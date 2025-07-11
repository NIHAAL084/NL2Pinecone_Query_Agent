"""
Script to populate Pinecone database with data from CSV file.
The script scrapes content from URLs in the CSV and creates embeddings using Ollama.
"""
import os
import csv
import time
import json
import requests
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urlparse
from pinecone import Pinecone
from dotenv import load_dotenv
import re
from bs4 import BeautifulSoup


def is_running_in_docker() -> bool:
    """Check if the application is running inside a Docker container"""
    return os.path.exists('/.dockerenv')


def get_ollama_url() -> str:
    """Get the appropriate Ollama URL based on the environment"""
    base_url = os.getenv("OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings")
    
    if is_running_in_docker():
        # Replace localhost with host.docker.internal for Docker environment
        base_url = base_url.replace("localhost", "host.docker.internal")
    
    return base_url


def clean_text(text: str) -> str:
    """Clean and format scraped text content"""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize line breaks
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove common web artifacts
    text = re.sub(r'Share this:|Follow us:|Subscribe to:|Cookie Policy|Privacy Policy', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Advertisement|Sponsored Content|Related Articles?:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(By|Author):\s*[^\n]+', '', text, flags=re.IGNORECASE)
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    # Remove excessive punctuation
    text = re.sub(r'[.]{3,}', '...', text)
    text = re.sub(r'[-]{3,}', '---', text)
    
    # Final cleanup
    text = re.sub(r'\s+', ' ', text.strip())
    
    return text


def scrape_content_from_url(url: str) -> str:
    """
    Scrape content from a given URL using Beautiful Soup for better HTML parsing.
    Returns cleaned text content suitable for embedding.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parse HTML with Beautiful Soup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
            element.decompose()
        
        # Remove common web artifacts by class/id (be more specific to avoid removing content)
        for element in soup.find_all(attrs={'class': re.compile(r'(advertisement|sidebar|social-share|comment-section|related-links)', re.I)}):
            element.decompose()
        
        for element in soup.find_all(attrs={'id': re.compile(r'(advertisement|sidebar|social-share|comment-section|related-links)', re.I)}):
            element.decompose()
        
        # Try to find main content area (common patterns)
        main_content = None
        
        # Try different selectors for main content
        content_selectors = [
            'article',
            '[role="main"]',
            'main',
            '.content',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.story-body',
            '#content',
            '#main-content',
            '.main-content'
        ]
        
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                # Test if this content area actually has substantial text
                test_text = main_content.get_text(separator=' ', strip=True)
                if len(test_text) > 100:  # Only use if it has substantial content
                    break
                else:
                    main_content = None  # Reset and try next selector
        
        # If no main content found, use the body
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Extract text from the main content area
        # Get text from paragraphs, headings, and list items primarily
        text_elements = main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'div'])
        
        # Collect text from relevant elements
        content_parts = []
        for element in text_elements:
            text = element.get_text(strip=True)
            if text and len(text) > 20:  # Only include substantial text chunks
                content_parts.append(text)
        
        # If we didn't get enough content from structured elements, fall back to all text
        if len(' '.join(content_parts)) < 200:
            content_parts = [main_content.get_text(separator=' ', strip=True)]
        
        # Join all content parts
        raw_content = ' '.join(content_parts)
        
        # Clean the extracted text
        cleaned_content = clean_text(raw_content)
        
        print(f"✅ Scraped {len(cleaned_content)} characters from {url}")
        return cleaned_content
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to scrape {url}: {e}")
        return ""
    except Exception as e:
        print(f"❌ Error processing content from {url}: {e}")
        return ""


def generate_embedding(text: str) -> List[float]:
    """Generate embedding for text using Ollama"""
    if not text.strip():
        raise ValueError("Cannot generate embedding for empty text")
    
    try:
        ollama_url = get_ollama_url()
        response = requests.post(
            ollama_url,
            json={"model": "nomic-embed-text", "prompt": text},
            timeout=30
        )
        response.raise_for_status()
        emb_json = response.json()
        vector = emb_json.get("embedding")
        
        if not vector or not isinstance(vector, list):
            raise ValueError(f"Ollama returned invalid embedding: {emb_json}")
        
        print(f"✅ Generated embedding with dimension: {len(vector)}")
        return vector
        
    except Exception as e:
        raise Exception(f"Error generating embedding: {str(e)}")


def parse_tags(tags_str: str) -> List[str]:
    """Parse tags from various formats in CSV and normalize them"""
    if not tags_str:
        return []
    
    # Handle JSON array format like ["tag1", "tag2"]
    if tags_str.startswith('[') and tags_str.endswith(']'):
        try:
            parsed_tags = json.loads(tags_str)
            if isinstance(parsed_tags, list):
                # Clean up hashtags and quotes
                cleaned_tags = []
                for tag in parsed_tags:
                    if isinstance(tag, str):
                        tag = tag.strip().replace('#', '').replace('"', '')
                        if tag:
                            cleaned_tags.extend(normalize_tag(tag))
                return cleaned_tags
        except json.JSONDecodeError:
            pass
    
    # Handle comma-separated format
    tags = [tag.strip().replace('#', '').replace('"', '') for tag in tags_str.split(',')]
    normalized_tags = []
    for tag in tags:
        if tag:
            normalized_tags.extend(normalize_tag(tag))
    return normalized_tags


def normalize_tag(tag: str) -> List[str]:
    """
    Normalize tags according to specific rules:
    - Keep event names with years intact (e.g., IPL2025 -> IPL 2025)
    - Separate combined words (e.g., RohitSharma -> Rohit Sharma)
    - Handle special cases like IPLInjuries -> ["IPL", "injuries"]
    - Keep abbreviations and specific terms intact
    """
    if not tag:
        return []
    
    # Special case mappings for compound tags
    special_cases = {
        'IPLInjuries': ['IPL', 'injuries'],
        'IPLRecords': ['IPL', 'records'],
        'CricketForm': ['cricket', 'form'],
        'CricketHealth': ['cricket', 'health'],
        'SportsPolitics': ['sports', 'politics'],
        'IndiaSports': ['India', 'sports'],
        'CelebrityNews': ['celebrity', 'news'],
        'BangladeshCricket': ['Bangladesh', 'cricket'],
        'IPLHistory': ['IPL', 'history'],
        'RRvsMI': ['RR', 'MI']  # Team vs team should split to separate teams
    }
    
    # Terms that should NOT be split (abbreviations, brand names, etc.)
    no_split_terms = {
        'BallonDor', 'RCB', 'DRS', 'IPL', 'CSK', 'MI', 'RR', 'SRH', 'KKR', 
        'GT', 'LSG', 'DC', 'PBKS', 'Barcelona', 'Pickleball', 'Chattogram'
    }
    
    # Check special cases first
    if tag in special_cases:
        return special_cases[tag]
    
    # Check if it's just a standalone year (skip these)
    if re.match(r'^20\d{2}$', tag):
        return []
    
    # Handle event names with years (e.g., IPL2025 -> IPL 2025)
    # Look for pattern: word followed directly by year
    year_pattern = r'([A-Za-z]+)(20\d{2})$'
    year_match = re.match(year_pattern, tag)
    if year_match:
        event_name = year_match.group(1)
        year = year_match.group(2)
        # If the event name is in no-split terms, keep it with the year
        if event_name in no_split_terms:
            return [f"{event_name} {year}"]
        # Otherwise, apply normal processing to the event name and add year
        processed_event = normalize_tag(event_name)
        if processed_event:
            return [f"{processed_event[0]} {year}"]
        return [f"{event_name} {year}"]
    
    # If it's in no-split list, return as-is
    if tag in no_split_terms:
        return [tag]
    
    # Handle camelCase/PascalCase splitting for names and compound words
    # Only split when we have a lowercase letter followed by uppercase letter
    # This preserves abbreviations like "RRvsMI" while splitting "RohitSharma"
    spaced_tag = re.sub(r'([a-z])([A-Z])', r'\1 \2', tag)
    
    # Clean up and return
    result = spaced_tag.strip()
    if result:
        return [result]
    return []


def parse_date(date_str: str) -> Dict[str, int]:
    """Parse date string and return year, month, day components"""
    try:
        # Handle ISO format with timezone
        if 'T' in date_str:
            date_str = date_str.split('T')[0]
        
        # Parse YYYY-MM-DD format
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return {
            'published_year': date_obj.year,
            'published_month': date_obj.month,
            'published_day': date_obj.day
        }
    except ValueError as e:
        print(f"⚠️  Could not parse date '{date_str}': {e}")
        # Return current date as fallback
        now = datetime.now()
        return {
            'published_year': now.year,
            'published_month': now.month,
            'published_day': now.day
        }


def truncate_for_embedding(text: str, max_length: int = 8000) -> str:
    """
    Truncate content specifically for embedding generation.
    Tries to cut at sentence boundaries when possible.
    """
    if len(text) <= max_length:
        return text
    
    # Try to cut at a sentence boundary
    sentences = text[:max_length].split('. ')
    if len(sentences) > 1:
        return '. '.join(sentences[:-1]) + '.'
    else:
        return text[:max_length]


def process_csv_row(row: Dict[str, str], row_index: int) -> Dict[str, Any]:
    """Process a single CSV row and return a Pinecone vector"""
    
    page_url = row.get('pageURL', '').strip()
    title = row.get('title', '').strip()
    published_date = row.get('publishedDate', '').strip()
    author = row.get('author', '').strip()
    tags_str = row.get('tags', '').strip()
    
    print(f"\n📄 Processing row {row_index + 1}: {title[:50]}...")
    
    # Scrape content from URL
    if not page_url:
        raise ValueError("pageURL is required")
    
    content = scrape_content_from_url(page_url)
    if not content:
        raise ValueError(f"Could not scrape content from {page_url}")
    
    # Parse date components
    date_components = parse_date(published_date)
    
    # Parse tags
    tags = parse_tags(tags_str)
    
    # Generate embedding from scraped content
    # Truncate content for embedding to avoid exceeding length limits (8000 chars ~ 2048 tokens)
    truncated_content = truncate_for_embedding(content, max_length=8000)
    vector = generate_embedding(truncated_content)
    
    # Create metadata (including fields not used for querying)
    # Store the FULL untruncated content in metadata
    metadata = {
        'author': author,
        'tags': tags,
        **date_components,  # published_year, published_month, published_day
        'title': title,     # Not used for querying but stored for reference
        'pageURL': page_url,  # Not used for querying but stored for reference
        'content': content  # Store full untruncated content
    }
    
    return {
        'id': f"csv-{row_index + 1}",
        'values': vector,
        'metadata': metadata
    }


def main():
    # Load environment variables
    load_dotenv(override=True)
    
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX = os.getenv("PINECONE_INDEX")
    
    assert PINECONE_API_KEY, "PINECONE_API_KEY not set"
    assert PINECONE_INDEX, "PINECONE_INDEX not set"
    
    # Configure Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(PINECONE_INDEX)
    
    # Get CSV file path from command line or use default
    import sys
    csv_file_path = sys.argv[1] if len(sys.argv) > 1 else "sample_data.csv"
    
    if not os.path.exists(csv_file_path):
        print(f"❌ CSV file not found: {csv_file_path}")
        return
    
    print(f"🚀 Starting CSV-based Pinecone population from: {csv_file_path}")
    print(f"📊 Target Pinecone index: {PINECONE_INDEX}")
    
    # Read and process CSV
    processed_rows = []
    failed_rows = []
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        total_rows = sum(1 for _ in reader)
        csvfile.seek(0)  # Reset file pointer
        reader = csv.DictReader(csvfile)  # Recreate reader
        
        print(f"📋 Found {total_rows} rows to process")
        
        for row_index, row in enumerate(reader):
            try:
                vector_data = process_csv_row(row, row_index)
                processed_rows.append((
                    vector_data['id'],
                    vector_data['values'],
                    vector_data['metadata']
                ))
                
                print(f"✅ Processed row {row_index + 1}/{total_rows}: {vector_data['id']}")
                
                # Add a small delay to be respectful to websites
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Failed to process row {row_index + 1}: {e}")
                failed_rows.append(row_index + 1)
                continue
    
    # Upsert to Pinecone in batches
    if processed_rows:
        batch_size = 50  # Pinecone batch limit
        total_batches = (len(processed_rows) + batch_size - 1) // batch_size
        
        print(f"\n🔄 Upserting {len(processed_rows)} vectors to Pinecone in {total_batches} batches...")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(processed_rows))
            batch = processed_rows[start_idx:end_idx]
            
            try:
                index.upsert(vectors=batch)
                print(f"✅ Upserted batch {batch_num + 1}/{total_batches} ({len(batch)} vectors)")
            except Exception as e:
                print(f"❌ Failed to upsert batch {batch_num + 1}: {e}")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"✅ Successfully processed: {len(processed_rows)} rows")
    print(f"❌ Failed to process: {len(failed_rows)} rows")
    if failed_rows:
        print(f"💥 Failed row numbers: {failed_rows}")
    
    print(f"\n🎉 CSV-based population complete!")
    print(f"💾 Database '{PINECONE_INDEX}' now contains {len(processed_rows)} new vectors from CSV data")


if __name__ == "__main__":
    main()
