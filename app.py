"""
FastAPI application for Natural Language to Pinecone Query Agent
"""

from dotenv import load_dotenv
load_dotenv(override=True)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import requests
from nl2pinecone_agent import NL2PineconeAgent
from pinecone import Pinecone
import json

app = FastAPI(
    title="NL2Pinecone Query Agent",
    description="Convert natural language queries to Pinecone metadata filters",
    version="1.0.0"
)

# Initialize the agent
agent = NL2PineconeAgent()

# Initialize Pinecone client
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings")

pinecone_client = None
pinecone_index = None

if PINECONE_API_KEY and PINECONE_INDEX:
    try:
        pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
        pinecone_index = pinecone_client.Index(PINECONE_INDEX)
    except Exception as e:
        print(f"Warning: Could not initialize Pinecone client: {e}")


class QueryRequest(BaseModel):
    """Request model for natural language queries"""
    query: str


class SearchRequest(BaseModel):
    """Request model for search queries with results"""
    query: str
    top_k: Optional[int] = 10
    include_metadata: Optional[bool] = True


class BatchSearchRequest(BaseModel):
    """Request model for batch search queries with results"""
    queries: List[str]
    top_k: Optional[int] = 10
    include_metadata: Optional[bool] = True


class SearchResult(BaseModel):
    """Individual search result"""
    id: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Response model for search results"""
    original_query: str
    pinecone_filter: Dict[str, Any]
    results: List[SearchResult]
    total_results: int
    timestamp: str


class QueryResponse(BaseModel):
    """Response model for processed queries"""
    original_query: str
    pinecone_filter: Dict[str, Any]
    is_valid: bool
    timestamp: str


def generate_embedding(text: str) -> List[float]:
    """Generate embedding for text using Ollama"""
    try:
        response = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": "nomic-embed-text", "prompt": text}
        )
        response.raise_for_status()
        emb_json = response.json()
        vector = emb_json.get("embedding")
        if not vector or not isinstance(vector, list):
            raise ValueError(f"Ollama returned invalid embedding: {emb_json}")
        return vector
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embedding: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Natural Language to Pinecone Query Agent API",
        "version": "1.0.0",
        "endpoints": {
            "/query": "POST - Convert natural language to Pinecone filter",
            "/results": "POST - Search Pinecone with natural language query",
            "/batch-query": "POST - Process multiple queries in batch",
            "/batch-results": "POST - Search Pinecone with multiple natural language queries",
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


@app.post("/results", response_model=SearchResponse)
async def search_with_query(request: SearchRequest):
    """
    Search Pinecone database using natural language query with vector similarity and metadata filtering
    
    Args:
        request: SearchRequest containing the natural language query and search parameters
        
    Returns:
        SearchResponse with actual search results from Pinecone database
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if not pinecone_index:
            raise HTTPException(status_code=503, detail="Pinecone client not available. Check PINECONE_API_KEY and PINECONE_INDEX environment variables.")
        
        query = request.query.strip()
        
        # Generate metadata filter using the agent
        pinecone_filter = agent.generate_pinecone_filter(query)
        
        # Generate embedding for the query
        query_vector = generate_embedding(query)
        
        # Search Pinecone with vector similarity and metadata filtering
        search_kwargs = {
            "vector": query_vector,
            "top_k": request.top_k,
            "include_metadata": request.include_metadata
        }
        
        # Add metadata filter if it's not empty
        if pinecone_filter:
            search_kwargs["filter"] = pinecone_filter
        
        search_results = pinecone_index.query(**search_kwargs)
        
        # Process results
        results = []
        for match in search_results.get('matches', []):
            result = SearchResult(
                id=match.get('id', ''),
                score=match.get('score', 0.0),
                metadata=match.get('metadata') if request.include_metadata else None
            )
            results.append(result)
        
        return SearchResponse(
            original_query=query,
            pinecone_filter=pinecone_filter,
            results=results,
            total_results=len(results),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing search: {str(e)}")


@app.post("/batch-results")
async def search_with_batch_queries(request: BatchSearchRequest):
    """
    Search Pinecone database using multiple natural language queries with vector similarity and metadata filtering
    
    Args:
        request: BatchSearchRequest containing the natural language queries and search parameters
        
    Returns:
        List of SearchResponse with actual search results from Pinecone database for each query
    """
    try:
        if not request.queries:
            raise HTTPException(status_code=400, detail="Queries list cannot be empty")
        
        if not pinecone_index:
            raise HTTPException(status_code=503, detail="Pinecone client not available. Check PINECONE_API_KEY and PINECONE_INDEX environment variables.")
        
        batch_results = []
        
        for query in request.queries:
            if not query or not query.strip():
                continue
                
            query = query.strip()
            
            try:
                # Generate metadata filter using the agent
                pinecone_filter = agent.generate_pinecone_filter(query)
                
                # Generate embedding for the query
                query_vector = generate_embedding(query)
                
                # Search Pinecone with vector similarity and metadata filtering
                search_kwargs = {
                    "vector": query_vector,
                    "top_k": request.top_k,
                    "include_metadata": request.include_metadata
                }
                
                # Add metadata filter if it's not empty
                if pinecone_filter:
                    search_kwargs["filter"] = pinecone_filter
                
                search_results = pinecone_index.query(**search_kwargs)
                
                # Process results
                results = []
                for match in search_results.get('matches', []):
                    result = SearchResult(
                        id=match.get('id', ''),
                        score=match.get('score', 0.0),
                        metadata=match.get('metadata') if request.include_metadata else None
                    )
                    results.append(result)
                
                search_response = SearchResponse(
                    original_query=query,
                    pinecone_filter=pinecone_filter,
                    results=results,
                    total_results=len(results),
                    timestamp=datetime.now().isoformat()
                )
                
                batch_results.append(search_response)
                
            except Exception as e:
                # If one query fails, add error info but continue with others
                batch_results.append({
                    "original_query": query,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        return {
            "results": batch_results,
            "total_processed": len(batch_results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing batch search: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
