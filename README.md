# Natural Language to Pinecone Query Agent 🤖

A production-ready AI agent that converts natural language queries into structured Pinecone metadata filters using Google Gemini AI, featuring comprehensive batch processing and testing capabilities.

## 🎯 Overview

This project implements an intelligent agent that converts natural language input into valid Pinecone queries with vector search and metadata filtering. The agent leverages Google Gemini AI to understand temporal references, author names, and topic tags, creating precise database queries for vector similarity search.

**Key Features:**

- 🧠 **Google Gemini AI Integration** - Advanced natural language understanding
- ⚡ **Batch Processing** - Handle multiple queries simultaneously  
- 🧪 **Comprehensive Testing** - 15 test scenarios with 100% success rate
- 🐳 **Docker Support** - Production-ready containerization
- 📊 **Detailed Metrics** - Performance tracking and validation reports
- 🔧 **uv Integration** - Fast dependency management

## 🏗️ Architecture

```mermaid
graph TD
    A[Natural Language Query] --> B[Google Gemini AI]
    B --> C[JSON Extraction & Validation]
    C --> D[Pinecone Filter JSON]
    
    E[Batch Queries] --> F[FastAPI Batch Endpoint]
    F --> B
    
    G[Single Query] --> H[FastAPI Query Endpoint]
    H --> B
    
    I[Test Suite] --> J[Comprehensive Validation]
    J --> K[Success Metrics & Reports]
```

## 📁 Project Structure

```
NL2Pincone_query_agent/
├── nl2pinecone_agent.py     # Core agent implementation (Gemini-only)
├── app.py                   # FastAPI application with batch processing
├── test_samples.py          # Comprehensive test data from requirements
├── test_batch.py            # Batch testing script with validation
├── batch_test_results.json  # Generated test results and metrics
├── pyproject.toml           # uv-compatible project configuration
├── requirements.txt         # Pip fallback requirements
├── Makefile                 # Development and testing automation
├── Dockerfile               # Multi-stage container configuration
├── .env.example             # Environment variable template
├── fill_pinecone_db.py      # Database population utility
└── README.md                # This documentation
```

## ✅ Test Results & Validation

### **Latest Batch Test Results:**

- 🎯 **100% Success Rate** across all test samples  
- ⚡ **15 queries processed** in ~16.8 seconds (~1.1s per query)
- ✅ **All primary test cases** from project requirements passed
- ✅ **All additional test cases** handled correctly  
- ✅ **Edge cases and variations** processed accurately

### **Test Coverage:**

- **Primary samples** (project requirements): 3 queries
- **Additional samples** (README examples): 7 queries
- **Edge cases** (date variations, complex names): 5 queries
- **Total coverage**: 15 comprehensive test scenarios

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager (recommended)
- Google Gemini API key

### 1. Installation & Setup

```bash
# Clone the repository
git clone <repository-url>
cd NL2Pincone_query_agent

# Setup with uv (recommended - fastest)
make setup

# Alternative: Setup with pip
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
# Create environment file
cp .env.example .env

# Add your API key to .env
echo "GEMINI_API_KEY=your_gemini_api_key_here" >> .env
```

### 3. Run & Test

```bash
# Start the API server
make run

# In a separate terminal, run tests
make test-batch          # Comprehensive batch testing
make test-primary        # Core requirement tests only
make health             # API health check
```

## 📚 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint with API information |
| GET | `/health` | Health check and status |
| GET | `/examples` | Example queries and expected responses |
| POST | `/query` | Convert single natural language query |
| POST | `/batch-query` | Process multiple queries simultaneously |

### Single Query Example

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me articles by Alice Zhang from last year about machine learning"}'
```

**Response:**

```json
{
  "original_query": "Show me articles by Alice Zhang from last year about machine learning",
  "pinecone_filter": {
    "author": "Alice Zhang",
    "published_year": {"$eq": 2024},
    "tags": {"$in": ["machine learning"]}
  },
  "is_valid": true,
  "timestamp": "2025-01-08T10:30:00"
}
```

### Batch Query Example

```bash
curl -X POST "http://localhost:8000/batch-query" \
  -H "Content-Type: application/json" \
  -d '{"queries": ["Find posts tagged with LLMs published in June, 2023", "Anything by John Doe on vector search?"]}'
```

## 🧪 Test Cases & Examples

### Primary Test Cases (Project Requirements)

1. **Author + Time + Topic**

   ```
   Input: "Show me articles by Alice Zhang from last year about machine learning"
   Output: {"author": "Alice Zhang", "published_year": {"$eq": 2024}, "tags": {"$in": ["machine learning"]}}
   ```

2. **Tags + Specific Date**

   ```
   Input: "Find posts tagged with 'LLMs' published in June, 2023"
   Output: {"tags": {"$in": ["LLMs"]}, "published_year": {"$eq": 2023}, "published_month": {"$eq": 6}}
   ```

3. **Author + Topic**

   ```
   Input: "Anything by John Doe on vector search?"
   Output: {"author": "John Doe", "tags": {"$in": ["vector search"]}}
   ```

### Additional Test Cases

4. **Multiple Tags with Date**

   ```
   Input: "Find articles tagged with 'AI' and 'deep learning' from March 2023."
   Output: {"tags": {"$in": ["AI", "deep learning"]}, "published_year": {"$eq": 2023}, "published_month": {"$eq": 3}}
   ```

5. **Exact Date with Author**

   ```
   Input: "Show me posts by Emma Johnson published on 2024-07-15."
   Output: {"author": "Emma Johnson", "published_year": {"$eq": 2024}, "published_month": {"$eq": 7}, "published_day": {"$eq": 15}}
   ```

### Edge Cases

6. **Complex Author Names**

   ```
   Input: "Papers by Priya Patel on transformers."
   Output: {"author": "Priya Patel", "tags": {"$in": ["transformers"]}}
   ```

7. **Multiple Filters**

   ```
   Input: "Any retrieval or NLP articles by David Kim from December 2023?"
   Output: {"author": "David Kim", "tags": {"$in": ["retrieval", "NLP"]}, "published_year": {"$eq": 2023}, "published_month": {"$eq": 12}}
   ```

## 🛠️ Development Commands

```bash
# Setup and Installation
make setup              # Setup uv environment and install dependencies
make install            # Alias for setup
make dev               # Setup development environment

# Running
make run               # Start FastAPI server
make health            # Check API health status

# Testing
make test              # Run individual query tests
make test-batch        # Run comprehensive batch tests (all samples)
make test-primary      # Run primary requirement tests only
make samples           # Show all available test samples

# Docker
make docker-build      # Build Docker image
make docker-run        # Run Docker container
make docker-stop       # Stop and remove container

# Development
make clean             # Clean generated files and cache
make lint              # Run code linting with ruff
make format            # Format code with black
make type-check        # Run type checking with mypy

# Utilities
make help              # Show all available commands
make env-create        # Create .env from template
```

## 🐳 Docker Deployment

### Quick Docker Setup

```bash
# Build and run
make docker-build
make docker-run

# Or manually
docker build -t nl2pinecone-agent .
docker run -d --name nl2pinecone-api -p 8000:8000 --env-file .env nl2pinecone-agent
```

### Docker Compose

```yaml
version: '3.8'
services:
  nl2pinecone-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 📊 Metadata Schema

The agent supports these Pinecone metadata fields:

### Supported Fields

- **author**: `string` - Article author name
- **tags**: `array` - Topic tags for the content
- **published_year**: `integer` - Publication year
- **published_month**: `integer` - Publication month (1-12)
- **published_day**: `integer` - Publication day (1-31)

### Query Operators

- `$eq`: equals
- `$ne`: not equals
- `$gt`: greater than
- `$gte`: greater than or equal
- `$lt`: less than
- `$lte`: less than or equal
- `$in`: value in list
- `$nin`: value not in list

## 🔧 Configuration

### Environment Variables

Required:

- `GEMINI_API_KEY`: Your Google Gemini API key

Optional:

- `PINECONE_API_KEY`: For future Pinecone integration
- `LOG_LEVEL`: Logging level (default: INFO)

### uv Configuration

This project uses uv for fast dependency management. Key benefits:

- ⚡ 10-100x faster than pip
- 🔒 Deterministic dependency resolution
- 🛠️ Built-in virtual environment management

## 🎯 Features

### ✅ Implemented

- [x] Google Gemini AI integration (no fallbacks)
- [x] Natural language query processing
- [x] FastAPI REST API with comprehensive endpoints
- [x] Batch query processing with detailed metrics
- [x] Docker containerization with multi-stage builds
- [x] Comprehensive test suite (15 test scenarios)
- [x] uv-based dependency management
- [x] Production-ready logging and error handling
- [x] Health checks and monitoring
- [x] Automated validation and reporting

### 🔮 Future Enhancements

- [ ] Live Pinecone database integration
- [ ] Query result caching with Redis
- [ ] Advanced date parsing ("two weeks ago", "last quarter")
- [ ] Query optimization suggestions
- [ ] Real-time performance analytics dashboard
- [ ] GraphQL API support

## 🧪 Testing

### Test Automation

```bash
# Quick validation
make test-primary      # Test core requirements (3 queries)
make test-batch        # Full test suite (15 queries)

# Individual testing
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "your test query here"}'
```

### Test Results

All tests generate detailed reports in `batch_test_results.json` with:

- Query processing times
- Success/failure rates
- Exact vs approximate matches
- Error details and debugging information

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`make test-batch`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Development Setup

```bash
git clone <repo>
cd NL2Pincone_query_agent
make dev
make test-batch  # Ensure all tests pass
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.


---

