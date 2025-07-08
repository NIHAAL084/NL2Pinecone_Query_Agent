"""
Natural Language to Pinecone Query Agent using Google Gemini
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, Any

import google.generativeai as genai
from dotenv import load_dotenv

# Load .env before anything else
load_dotenv(override=True)

# Load environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
PINECONE_HOST = os.getenv("PINECONE_HOST")




class NL2PineconeAgent:
    """
    Agent to convert natural language queries into Pinecone metadata filters using Google Gemini (no fallback).
    """
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY must be set in the environment.")
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-001')
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.current_day = datetime.now().day

    def _create_system_prompt(self) -> str:
        # Use string concatenation instead of .format() to avoid curly brace issues
        return f"""
You are an expert at converting natural language queries into Pinecone metadata filters.

Today's date: {self.current_year}-{self.current_month:02d}-{self.current_day:02d}

METADATA SCHEMA:
  - author: string (e.g., "John Doe")
  - tags: list of strings (e.g., ["AI", "NLP"])
  - published_year: integer (e.g., 2024)
  - published_month: integer (1-12)
  - published_day: integer (1-31)

QUERY OPERATORS:
  - $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin

RULES:
  1. Use published_year, published_month, published_day for all date filters.
  2. Always return valid, minified JSON (no comments, no extra text).
  3. Handle relative dates (e.g., "last year", "this month", "past 3 years").
  4. Extract author names and tags accurately.
  5. If no time period is mentioned, do not add date filters.
  6. If no author or tags are mentioned, omit those fields.

EXAMPLES:
  Query: articles by John Doe last year about AI
  Output: {{"author": "John Doe", "tags": {{"$in": ["AI"]}}, "published_year": {{"$eq": 2024}}}}

  Query: posts tagged with 'NLP' in March 2023
  Output: {{"tags": {{"$in": ["NLP"]}}, "published_year": {{"$eq": 2023}}, "published_month": {{"$eq": 3}}}}

  Query: anything by Alice
  Output: {{"author": "Alice"}}

Convert the following natural language query to a Pinecone metadata filter. Return ONLY the JSON object, no additional text, no explanation, no markdown.
"""


    def generate_pinecone_filter(self, natural_language_query: str) -> Dict[str, Any]:
        prompt = self._create_system_prompt() + f"\n\nQuery: {natural_language_query}"
        response = self.model.generate_content(prompt)
        response_text = response.text.strip()
        # Use a raw string for the regex to avoid escape sequence issues
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        raise ValueError("Gemini did not return a valid JSON filter.")


