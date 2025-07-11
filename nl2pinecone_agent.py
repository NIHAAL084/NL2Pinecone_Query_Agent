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
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.current_day = datetime.now().day

    def _create_system_prompt(self) -> str:
        # Use string concatenation instead of .format() to avoid curly brace issues
        return f"""
You are an expert at converting natural language queries into Pinecone metadata filters for article search.

Today's date: {self.current_year}-{self.current_month:02d}-{self.current_day:02d}

METADATA SCHEMA:
  - author: string (e.g., "John Doe") - WHO wrote the article
  - tags: list of strings (e.g., ["sports", "AI"]) - WHAT the article covers/discusses
  - published_year: integer (e.g., 2024) - Year when published
  - published_month: integer (1-12) - Month when published  
  - published_day: integer (1-31) - Day when published

OPERATORS: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin

CRITICAL RULES:
1. AUTHOR IDENTIFICATION: Only use "author" field when query explicitly mentions WHO WROTE the article with phrases like "by [name]", "written by [name]", "articles by [name]", "posts by [name]".

2. TAG IDENTIFICATION: Use "tags" field for TOPICS, SUBJECTS, PEOPLE MENTIONED IN articles. Triggered by phrases like "about [topic]", "posts about [subject]", "[topic] articles", "find [subject]".

3. YEAR EXTRACTION LOGIC: Distinguish between years as publication dates vs years as part of subject matter:
   - Publication dates: "from 2023", "in 2024", "last year" → published_year field
   - Subject matter: "IPL 2025", "Olympics 2024", "Election 2022" → keep in tags as part of the topic
   - When unclear, prefer keeping years with their associated topics in tags

4. TAG SEPARATION FOR SEARCH: When query mentions multiple distinct concepts, separate them into individual tags for better search matching. Examples: "celebrity news" → ["celebrity", "news"], "health issues" → ["health", "issues"], "salary problems" → ["salary", "problems"].

5. TECHNICAL TERM PRESERVATION: Keep established technical terms intact only when they are widely recognized as single concepts: "machine learning", "web development", "cloud computing", "user experience".

6. DATE PARSING: Use published_year/month/day for temporal filters. "last year" = current_year-1, "this month" = current_month, "May 2024" = year:2024, month:5.

7. EXPLICIT CONJUNCTION SEPARATION: When query uses explicit "and" between concepts, always treat as separate tags: "technology and business" → ["technology", "business"].

8. FIELD OMISSION: Only include fields that are explicitly mentioned or clearly implied. Don't add author/tags/dates if not present in query.

9. PROPER NAME HANDLING: Always keep proper names, brand names, and established technical terms intact as single tags.

10. SEARCH OPTIMIZATION: Prioritize breaking down general terms into components for better search recall, unless they form well-established technical or proper noun phrases.

EXAMPLES:
Query: articles by Dr. Smith about web development from 2023
Output: {{"author": "Dr. Smith", "tags": {{"$in": ["web development"]}}, "published_year": {{"$eq": 2023}}}}

Query: find posts about World Cup 2022
Output: {{"tags": {{"$in": ["World Cup 2022"]}}}}

Query: show me posts about Lakers from December
Output: {{"tags": {{"$in": ["Lakers"]}}, "published_month": {{"$eq": 12}}}}

Query: articles about basketball training methods
Output: {{"tags": {{"$in": ["basketball", "training", "methods"]}}}}

Query: posts about business news
Output: {{"tags": {{"$in": ["business", "news"]}}}}

Query: find all articles by Sarah Wilson
Output: {{"author": "Sarah Wilson"}}

Query: show me articles from January 15th, 2023
Output: {{"published_year": {{"$eq": 2023}}, "published_month": {{"$eq": 1}}, "published_day": {{"$eq": 15}}}}

Query: posts about Tom Brady and Patriots history
Output: {{"tags": {{"$in": ["Tom Brady", "Patriots", "history"]}}}}

Convert the following query to a Pinecone metadata filter. Return ONLY valid JSON, no explanations.
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

