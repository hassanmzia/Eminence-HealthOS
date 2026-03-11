"""
Eminence HealthOS — Vector Store (Qdrant)
Manages vector embeddings for clinical knowledge retrieval (RAG).
Supports document ingestion, similarity search, and filtered queries.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

logger = logging.getLogger("healthos.vector_store")


class VectorStore:
    """
    Qdrant-backed vector store for clinical knowledge retrieval.

    Supports:
    - Ingesting clinical documents (guidelines, protocols, drug references)
    - Similarity search for RAG context
    - Filtered search by collection, source type, and metadata
    """

    DEFAULT_COLLECTION = "clinical_knowledge"

    def __init__(self, client: Any = None, embedding_fn: Any = None):
        """
        Args:
            client: Qdrant client instance (qdrant_client.QdrantClient)
            embedding_fn: Callable that takes text and returns embedding vector
        """
        self._client = client
        self._embed = embedding_fn
        self._dimension = 384  # Default for all-MiniLM-L6-v2

    async def ensure_collection(self, collection: str | None = None) -> None:
        """Create collection if it doesn't exist."""
        collection = collection or self.DEFAULT_COLLECTION
        if not self._client:
            logger.warning("Vector store client not configured")
            return

        try:
            from qdrant_client.models import Distance, VectorParams

            collections = self._client.get_collections().collections
            existing = {c.name for c in collections}

            if collection not in existing:
                self._client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(
                        size=self._dimension, distance=Distance.COSINE
                    ),
                )
                logger.info("vector_store.collection_created", collection=collection)
        except Exception as e:
            logger.warning("vector_store.ensure_collection_failed: %s", e)

    async def ingest_documents(
        self,
        documents: list[dict[str, Any]],
        collection: str | None = None,
    ) -> int:
        """
        Ingest documents into the vector store.

        Each document should have:
            - text: str — the document content
            - metadata: dict — source, category, title, etc.
        """
        collection = collection or self.DEFAULT_COLLECTION
        if not self._client or not self._embed:
            logger.warning("Vector store not fully configured — skipping ingest")
            return 0

        from qdrant_client.models import PointStruct

        points = []
        for doc in documents:
            text = doc.get("text", "")
            if not text:
                continue

            embedding = self._embed(text)
            point_id = str(uuid.uuid4())

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": text,
                        "source": doc.get("metadata", {}).get("source", "unknown"),
                        "category": doc.get("metadata", {}).get("category", "general"),
                        "title": doc.get("metadata", {}).get("title", ""),
                        **doc.get("metadata", {}),
                    },
                )
            )

        if points:
            self._client.upsert(collection_name=collection, points=points)
            logger.info("vector_store.ingested", count=len(points), collection=collection)

        return len(points)

    async def search(
        self,
        query: str,
        limit: int = 5,
        collection: str | None = None,
        filters: Optional[dict[str, Any]] = None,
        score_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Semantic search for relevant clinical knowledge.

        Returns list of results with text, score, and metadata.
        """
        collection = collection or self.DEFAULT_COLLECTION
        if not self._client or not self._embed:
            logger.warning("Vector store not configured — returning empty results")
            return []

        try:
            query_vector = self._embed(query)

            # Build filter conditions
            query_filter = None
            if filters:
                from qdrant_client.models import FieldCondition, Filter, MatchValue

                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
                query_filter = Filter(must=conditions)

            results = self._client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
                score_threshold=score_threshold,
            )

            return [
                {
                    "text": r.payload.get("text", ""),
                    "score": r.score,
                    "source": r.payload.get("source", ""),
                    "category": r.payload.get("category", ""),
                    "title": r.payload.get("title", ""),
                    "metadata": {k: v for k, v in r.payload.items() if k != "text"},
                }
                for r in results
            ]

        except Exception as e:
            logger.error("vector_store.search_failed: %s", e)
            return []

    async def delete_collection(self, collection: str) -> None:
        """Delete a collection."""
        if self._client:
            try:
                self._client.delete_collection(collection)
            except Exception as e:
                logger.warning("vector_store.delete_failed: %s", e)
