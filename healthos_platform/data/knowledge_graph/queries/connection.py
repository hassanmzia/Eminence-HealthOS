"""
Eminence HealthOS — Async Neo4j driver connection with retry logic and connection pooling.
Used for medical knowledge graph queries (drug interactions, disease relationships).

Replaces the synchronous Django-based connection from InHealth with a standalone
async neo4j driver compatible with HealthOS's asyncio architecture.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

# Neo4j async driver — lazy initialized
_driver = None
_driver_lock = asyncio.Lock()


async def get_driver():
    """Get or create the Neo4j async driver (singleton with retry)."""
    global _driver
    if _driver is None:
        async with _driver_lock:
            if _driver is None:  # Double-checked locking
                _driver = await _create_driver_with_retry()
    return _driver


async def _create_driver_with_retry(max_retries: int = 5, delay: float = 2.0):
    """Create Neo4j async driver with exponential backoff retry."""
    from neo4j import AsyncGraphDatabase

    from healthos_platform.config import get_settings

    settings = get_settings()
    uri = settings.neo4j_uri
    user = settings.neo4j_user
    password = settings.neo4j_password

    for attempt in range(max_retries):
        try:
            driver = AsyncGraphDatabase.driver(
                uri,
                auth=(user, password),
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                connection_acquisition_timeout=30,
            )
            # Verify connectivity
            await driver.verify_connectivity()
            logger.info("neo4j.connected", uri=uri)
            return driver
        except Exception as e:
            wait = delay * (2 ** attempt)
            logger.warning(
                "neo4j.connection_retry",
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e),
                retry_in_seconds=wait,
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(wait)
            else:
                logger.error("neo4j.connection_failed", attempts=max_retries)
                raise


@asynccontextmanager
async def get_session(database: str = "neo4j") -> AsyncGenerator:
    """Async context manager for Neo4j sessions."""
    driver = await get_driver()
    session = driver.session(database=database)
    try:
        yield session
    finally:
        await session.close()


async def run_query(
    cypher: str, parameters: Dict[str, Any] | None = None, database: str = "neo4j"
) -> List[Dict[str, Any]]:
    """Execute a read Cypher query and return results as a list of dicts."""
    async with get_session(database=database) as session:
        result = await session.run(cypher, parameters or {})
        records = [record.data() async for record in result]
        return records


async def run_write_query(
    cypher: str, parameters: Dict[str, Any] | None = None, database: str = "neo4j"
) -> List[Dict[str, Any]]:
    """Execute a write Cypher query within a transaction."""

    async def _tx_work(tx):
        result = await tx.run(cypher, parameters or {})
        return [record.data() async for record in result]

    async with get_session(database=database) as session:
        return await session.execute_write(_tx_work)


async def close_driver() -> None:
    """Close the Neo4j driver (call on application shutdown)."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
        logger.info("neo4j.driver_closed")


async def initialize_schema() -> None:
    """Create Neo4j indexes and constraints for the knowledge graph."""
    schema_queries = [
        # Drug nodes
        "CREATE CONSTRAINT drug_rxnorm IF NOT EXISTS FOR (d:Drug) REQUIRE d.rxnorm IS UNIQUE",
        "CREATE CONSTRAINT disease_icd10 IF NOT EXISTS FOR (d:Disease) REQUIRE d.icd10 IS UNIQUE",
        "CREATE CONSTRAINT symptom_id IF NOT EXISTS FOR (s:Symptom) REQUIRE s.id IS UNIQUE",
        "CREATE CONSTRAINT gene_id IF NOT EXISTS FOR (g:Gene) REQUIRE g.id IS UNIQUE",
        # Patient
        "CREATE CONSTRAINT patient_id IF NOT EXISTS FOR (p:Patient) REQUIRE p.id IS UNIQUE",
        # Indexes for performance
        "CREATE INDEX drug_name IF NOT EXISTS FOR (d:Drug) ON (d.name)",
        "CREATE INDEX disease_name IF NOT EXISTS FOR (d:Disease) ON (d.name)",
        "CREATE INDEX interaction_severity IF NOT EXISTS FOR ()-[r:INTERACTS_WITH]-() ON (r.severity)",
    ]

    try:
        async with get_session() as session:
            for query in schema_queries:
                try:
                    await session.run(query)
                except Exception as e:
                    logger.warning("neo4j.schema_warning", query=query[:60], error=str(e))
        logger.info("neo4j.schema_initialized")
    except Exception as e:
        logger.error("neo4j.schema_init_failed", error=str(e))
