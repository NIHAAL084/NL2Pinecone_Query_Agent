"""
Script to generate and upsert 100 sample documents into Pinecone using Gemini for content and metadata generation.
"""
import os
import random
import time
from datetime import datetime, timedelta
from typing import List
import google.generativeai as genai
from pinecone import Pinecone
from dotenv import load_dotenv


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


# Load environment variables
load_dotenv(override=True)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
PINECONE_HOST = os.getenv("PINECONE_HOST")

assert GEMINI_API_KEY, "GEMINI_API_KEY not set"
assert PINECONE_API_KEY, "PINECONE_API_KEY not set"
assert PINECONE_INDEX, "PINECONE_INDEX not set"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel('gemini-2.0-flash-001')

# Configure Pinecone (new SDK)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

# Sample authors and tags
authors = [
    "Alice Zhang", "John Doe", "Maria Garcia", "David Kim", "Priya Patel",
    "Liam Smith", "Emma Johnson", "Noah Brown", "Olivia Lee", "William Jones"
]
tags = [
    "machine learning", "LLMs", "vector search", "AI", "NLP", "retrieval",
    "deep learning", "transformers", "search", "knowledge graphs"
]

def random_date(start_year=2022, end_year=2025):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    d = start + timedelta(days=random_days)
    return d.year, d.month, d.day

def generate_sample(i: int):
    author = random.choice(authors)
    tag_sample = random.sample(tags, k=random.randint(1, 3))
    year, month, day = random_date()
    prompt = (
        f"Write a 3-5 sentence article summary about {', '.join(tag_sample)} "
        f"by {author} published on {year}-{month:02d}-{day:02d}. "
        f"Do not include any metadata, just the summary."
    )
    try:
        response = gemini.generate_content(prompt)
        content = response.text.strip()
        print(f"Generated content for sample {i}: {content[:50]}...")
    except Exception as e:
        print(f"Gemini API failed for sample {i}: {e}")
        content = f"Sample article about {', '.join(tag_sample)} by {author}."
    # Use Ollama embedding model to generate a real vector
    import requests
    ollama_url = get_ollama_url()
    emb_response = requests.post(
        ollama_url,
        json={"model": "nomic-embed-text", "prompt": content}
    )
    emb_response.raise_for_status()
    emb_json = emb_response.json()
    vector = emb_json.get("embedding")
    if not vector or not isinstance(vector, list):
        raise ValueError(f"Ollama returned invalid embedding: {emb_json}")
    print(f"Embedding dimension: {len(vector)}")
    
    # Store content in metadata as a separate field
    metadata = {
        "author": author,
        "tags": tag_sample,
        "published_year": year,
        "published_month": month,
        "published_day": day,
        "content": content  # Store the generated content in metadata
    }
    
    return {
        "id": f"sample-{i}",
        "values": vector,
        "metadata": metadata
    }

def main():
    total_samples = 100
    batch_size = 15  # Gemini rate limit: 15 requests per minute
    samples = []
    
    print(f"Generating {total_samples} samples in batches of {batch_size} (rate limit: 15/min)")
    
    for batch_start in range(0, total_samples, batch_size):
        batch_end = min(batch_start + batch_size, total_samples)
        batch_samples = []
        
        print(f"\n--- Processing batch {batch_start//batch_size + 1}: samples {batch_start+1}-{batch_end} ---")
        
        for i in range(batch_start, batch_end):
            sample = generate_sample(i)
            batch_samples.append((sample["id"], sample["values"], sample["metadata"]))
            samples.append((sample["id"], sample["values"], sample["metadata"]))
            print(f"Prepared sample {i+1}/{total_samples} (id: {sample['id']})")
        
        # Upsert this batch to Pinecone
        if batch_samples:
            index.upsert(vectors=batch_samples)
            print(f"Upserted batch of {len(batch_samples)} samples to Pinecone")
        
        # Wait 60 seconds before next batch (except for the last batch)
        if batch_end < total_samples:
            print(f"Waiting 60 seconds for rate limit reset...")
            time.sleep(60)
    
    print(f"\n✅ Successfully generated and upserted all {len(samples)} samples to Pinecone index '{PINECONE_INDEX}'")
    print(f"Database now contains fresh content generated by Gemini!")

if __name__ == "__main__":
    main()
