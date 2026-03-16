FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (avoids pulling ~4GB of CUDA libraries)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install heavy ML deps in a separate layer to manage disk pressure
RUN pip install --no-cache-dir \
    sentence-transformers \
    scikit-learn \
    xgboost \
    numpy \
    pandas

# Install remaining deps before editable install
RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] pydantic pydantic-settings \
    "sqlalchemy[asyncio]" asyncpg alembic redis \
    langgraph langchain-core langchain-anthropic langchain-community \
    anthropic fhir.resources \
    aiokafka "celery[redis]" \
    "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt>=4.0.0,<4.1.0" pyotp cryptography \
    opentelemetry-api opentelemetry-sdk prometheus-client structlog \
    neo4j qdrant-client \
    httpx python-multipart python-dotenv tenacity orjson

COPY pyproject.toml .
COPY healthos_platform/ healthos_platform/
COPY modules/ modules/
COPY shared/ shared/
COPY clinical_decision_support/ clinical_decision_support/
COPY observability/ observability/
COPY scripts/ scripts/
COPY services/ services/

# Editable install (deps already satisfied, only links the project)
RUN pip install --no-cache-dir --no-deps -e .

# --- Runtime stage ---
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages and app from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

EXPOSE 8000

CMD ["uvicorn", "healthos_platform.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
