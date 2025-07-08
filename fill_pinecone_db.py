"""
Script to generate and upsert 100 sample documents into Pinecone using Gemini for content and metadata generation.
"""
import os
import random
from datetime import datetime, timedelta
from typing import List
import google.generativeai as genai
from pinecone import Pinecone

# Load environment variables
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
gemini = genai.GenerativeModel('gemini-1.5-pro')

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
        f"Write a 1-2 sentence article summary about {', '.join(tag_sample)} "
        f"by {author} published on {year}-{month:02d}-{day:02d}. "
        f"Do not include any metadata, just the summary."
    )
    try:
        response = gemini.generate_content(prompt)
        content = response.text.strip()
    except Exception:
        content = f"Sample article about {', '.join(tag_sample)} by {author}."
    # Use Ollama embedding model to generate a real vector
    import requests
    ollama_url = os.getenv("OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings")
    emb_response = requests.post(
        ollama_url,
        json={"model": "nomic-embed-text", "prompt": content}
    )
    emb_response.raise_for_status()
    emb_json = emb_response.json()
    print("Ollama embedding API response:", emb_json)
    vector = emb_json.get("embedding")
    if not vector or not isinstance(vector, list):
        raise ValueError(f"Ollama returned invalid embedding: {emb_json}")
    print(f"Embedding dimension: {len(vector)}")
    metadata = {
        "author": author,
        "tags": tag_sample,
        "published_year": year,
        "published_month": month,
        "published_day": day,
        "summary": content
    }
    return {
        "id": f"sample-{i}",
        "values": vector,
        "metadata": metadata
    }

def main():
    samples = []
    for i in range(100):
        sample = generate_sample(i)
        samples.append((sample["id"], sample["values"], sample["metadata"]))
        print(f"Prepared sample {i+1}/100 (id: {sample['id']})")
    index.upsert(vectors=samples)
    print(f"Upserted {len(samples)} samples to Pinecone index '{PINECONE_INDEX}'")

if __name__ == "__main__":
    main()
