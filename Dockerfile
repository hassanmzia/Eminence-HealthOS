FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Layer 1: LangChain / Agent framework (heavy transitive deps)
RUN pip install --no-cache-dir \
    langgraph langchain-core langchain-anthropic langchain-community

# Layer 2: Core API + database + security + observability
RUN pip install --no-cache-dir \
    fastapi "uvicorn[standard]" pydantic pydantic-settings \
    "sqlalchemy[asyncio]" asyncpg alembic redis \
    anthropic fhir.resources \
    aiokafka "celery[redis]" \
    "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt>=4.0.0,<4.1.0" pyotp cryptography \
    opentelemetry-api opentelemetry-sdk prometheus-client structlog \
    neo4j qdrant-client \
    httpx python-multipart python-dotenv tenacity orjson

# NOTE: scikit-learn, xgboost, numpy, pandas, torch, sentence-transformers
# are all lazy-loaded in healthos_platform/ml/ and NOT needed at API startup.
# Install them in a dedicated ML worker image via: pip install -e ".[ml]"

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
