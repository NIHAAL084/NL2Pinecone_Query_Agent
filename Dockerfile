# Multi-stage build for NL2Pinecone Query Agent
# Builder stage for dependencies
FROM python:3.11-slim AS builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Install system dependencies required for building
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock* README.md ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv --python 3.11
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies (excluding dev dependencies for production)
RUN uv sync --no-dev --frozen

# Production runtime stage
FROM python:3.11-slim AS runtime

# Install uv for runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check with improved configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Environment variables for production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000

# Add labels for metadata
LABEL org.opencontainers.image.title="NL2Pinecone Query Agent"
LABEL org.opencontainers.image.description="AI agent for converting natural language to Pinecone queries"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="nihaal.a084@gmail.com"

# Run the application with proper signal handling using uv run
CMD ["uv", "run", "app.py"]
