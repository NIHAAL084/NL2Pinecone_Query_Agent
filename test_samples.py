"""
Test samples for NL2Pinecone Query Agent

Contains sample queries from project requirements and README,
along with expected outputs for validation.
"""

# Primary test cases from project requirements
PRIMARY_SAMPLES = [
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

# Additional test cases from README
ADDITIONAL_SAMPLES = [
    {
        "query": "Find articles tagged with 'AI' and 'deep learning' from March 2023.",
        "expected_filter": {
            "tags": {"$in": ["AI", "deep learning"]},
            "published_year": {"$eq": 2023},
            "published_month": {"$eq": 3}
        }
    },
    {
        "query": "Show me posts by Emma Johnson published on 2024-07-15.",
        "expected_filter": {
            "author": "Emma Johnson",
            "published_year": {"$eq": 2024},
            "published_month": {"$eq": 7},
            "published_day": {"$eq": 15}
        }
    },
    {
        "query": "Articles about 'knowledge graphs' from 2022.",
        "expected_filter": {
            "tags": {"$in": ["knowledge graphs"]},
            "published_year": {"$eq": 2022}
        }
    },
    {
        "query": "Papers by Priya Patel on transformers.",
        "expected_filter": {
            "author": "Priya Patel",
            "tags": {"$in": ["transformers"]}
        }
    },
    {
        "query": "Any retrieval or NLP articles by David Kim from December 2023?",
        "expected_filter": {
            "author": "David Kim",
            "tags": {"$in": ["retrieval", "NLP"]},
            "published_year": {"$eq": 2023},
            "published_month": {"$eq": 12}
        }
    },
    {
        "query": "Show me all posts tagged with 'search' and 'vector search' from 2025-01-10.",
        "expected_filter": {
            "tags": {"$in": ["search", "vector search"]},
            "published_year": {"$eq": 2025},
            "published_month": {"$eq": 1},
            "published_day": {"$eq": 10}
        }
    },
    {
        "query": "Articles by Olivia Lee about LLMs from this year.",
        "expected_filter": {
            "author": "Olivia Lee",
            "tags": {"$in": ["LLMs"]},
            "published_year": {"$eq": 2025}
        }
    }
]

# Edge cases and variations
EDGE_CASE_SAMPLES = [
    {
        "query": "articles by john doe",
        "expected_filter": {
            "author": "john doe"
        }
    },
    {
        "query": "posts about AI last month",
        "expected_filter": {
            "tags": {"$in": ["AI"]},
            "published_year": {"$eq": 2025},
            "published_month": {"$eq": 6}
        }
    },
    {
        "query": "research on neural networks from 2020",
        "expected_filter": {
            "tags": {"$in": ["neural networks"]},
            "published_year": {"$eq": 2020}
        }
    },
    {
        "query": "anything tagged with machine learning",
        "expected_filter": {
            "tags": {"$in": ["machine learning"]}
        }
    },
    {
        "query": "posts from January 2024",
        "expected_filter": {
            "published_year": {"$eq": 2024},
            "published_month": {"$eq": 1}
        }
    }
]

# All samples combined
ALL_SAMPLES = PRIMARY_SAMPLES + ADDITIONAL_SAMPLES + EDGE_CASE_SAMPLES

# Just the queries for batch processing
ALL_QUERIES = [sample["query"] for sample in ALL_SAMPLES]
PRIMARY_QUERIES = [sample["query"] for sample in PRIMARY_SAMPLES]
ADDITIONAL_QUERIES = [sample["query"] for sample in ADDITIONAL_SAMPLES]
EDGE_CASE_QUERIES = [sample["query"] for sample in EDGE_CASE_SAMPLES]

if __name__ == "__main__":
    print(f"Total samples: {len(ALL_SAMPLES)}")
    print(f"Primary samples: {len(PRIMARY_SAMPLES)}")
    print(f"Additional samples: {len(ADDITIONAL_SAMPLES)}")
    print(f"Edge case samples: {len(EDGE_CASE_SAMPLES)}")
    
    print("\nAll queries:")
    for i, query in enumerate(ALL_QUERIES, 1):
        print(f"{i}. {query}")
