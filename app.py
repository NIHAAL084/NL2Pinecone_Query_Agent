"""
FastAPI application for Natural Language to Pinecone Query Agent
"""

from dotenv import load_dotenv
load_dotenv(override=True)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
import os
from nl2pinecone_agent import NL2PineconeAgent
import json

app = FastAPI(
    title="NL2Pinecone Query Agent",
    description="Convert natural language queries to Pinecone metadata filters",
    version="1.0.0"
)

# Initialize the agent
agent = NL2PineconeAgent()


class QueryRequest(BaseModel):
    """Request model for natural language queries"""
    query: str


class QueryResponse(BaseModel):
    """Response model for processed queries"""
    original_query: str
    pinecone_filter: Dict[str, Any]
    is_valid: bool
    timestamp: str


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Natural Language to Pinecone Query Agent API",
        "version": "1.0.0",
        "endpoints": {
            "/query": "POST - Convert natural language to Pinecone filter",
            "/health": "GET - Health check",
            "/examples": "GET - Example queries and responses"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "nl2pinecone-agent"}


@app.get("/examples")
async def get_examples():
    """Get example queries and their expected responses"""
    examples = [
        {
            "query": "Show me articles by Alice Zhang from last year about machine learning.",
            "expected_filter": {
                "author": "Alice Zhang",
                "published_year": {"$eq": 2024},
                "tags": {"$in": ["machine learning"]}
            }
        },
        {
            "query": "Find posts tagged with 'LLMs' published in June, 2023.",
            "expected_filter": {
                "tags": {"$in": ["LLMs"]},
                "published_year": {"$eq": 2023},
                "published_month": {"$eq": 6}
            }
        },
        {
            "query": "Anything by John Doe on vector search?",
            "expected_filter": {
                "author": "John Doe",
                "tags": {"$in": ["vector search"]}
            }
        }
    ]
    return {"examples": examples}


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a natural language query and return Pinecone metadata filter
    
    Args:
        request: QueryRequest containing the natural language query
        
    Returns:
        QueryResponse with the generated filter and metadata
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        

        query = request.query.strip()
        pinecone_filter = agent.generate_pinecone_filter(query)
        return QueryResponse(
            original_query=query,
            pinecone_filter=pinecone_filter,
            is_valid=True,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.post("/batch-query")
async def process_batch_queries(queries: list[str]):
    """
    Process multiple natural language queries in batch
    
    Args:
        queries: List of natural language query strings
        
    Returns:
        List of processed query results
    """
    try:
        if not queries:
            raise HTTPException(status_code=400, detail="Queries list cannot be empty")
        

        results = []
        for query in queries:
            if query and query.strip():
                pinecone_filter = agent.generate_pinecone_filter(query.strip())
                results.append({
                    "original_query": query.strip(),
                    "pinecone_filter": pinecone_filter,
                    "is_valid": True,
                    "timestamp": datetime.now().isoformat()
                })
        return {"results": results, "total_processed": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing batch queries: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
