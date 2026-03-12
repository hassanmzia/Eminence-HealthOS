"""
Unit tests for HealthOS platform services.

Covers: kafka, cache, knowledge_graph, vector_store, workers, ehr.
All external dependencies (Redis, Kafka, Neo4j, Qdrant, HTTP) are mocked.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# ---------------------------------------------------------------------------
# Kafka service tests
# ---------------------------------------------------------------------------


class TestHealthOSEvent:
    """Tests for the HealthOSEvent Pydantic model."""

    def test_event_defaults(self):
        from healthos_platform.services.kafka import HealthOSEvent

        event = HealthOSEvent(
            event_type="vitals.ingested",
            source="api",
            org_id="org-1",
        )
        assert event.event_type == "vitals.ingested"
        assert event.source == "api"
        assert event.org_id == "org-1"
        assert event.patient_id is None
        # Auto-generated fields
        assert event.event_id  # UUID string
        assert event.timestamp  # ISO timestamp

    def test_event_with_all_fields(self):
        from healthos_platform.services.kafka import HealthOSEvent

        event = HealthOSEvent(
            event_type="alert.generated",
            source="agent",
            org_id="org-2",
            patient_id="patient-42",
            payload={"severity": "high"},
            trace_id="trace-abc",
            correlation_id="corr-xyz",
        )
        assert event.patient_id == "patient-42"
        assert event.payload == {"severity": "high"}
        assert event.trace_id == "trace-abc"
        assert event.correlation_id == "corr-xyz"


class TestEventRouting:
    """Tests for the _route_event helper function."""

    def test_route_vitals(self):
        from healthos_platform.services.kafka import (
            _route_event,
            TOPIC_VITALS_INGESTED,
        )

        assert _route_event("vitals.ingested") == TOPIC_VITALS_INGESTED
        assert _route_event("vitals.updated") == TOPIC_VITALS_INGESTED

    def test_route_alert(self):
        from healthos_platform.services.kafka import (
            _route_event,
            TOPIC_ALERTS_GENERATED,
        )

        assert _route_event("alert.generated") == TOPIC_ALERTS_GENERATED

    def test_route_agent(self):
        from healthos_platform.services.kafka import (
            _route_event,
            TOPIC_AGENT_EVENTS,
        )

        assert _route_event("agent.executed") == TOPIC_AGENT_EVENTS

    def test_route_patient(self):
        from healthos_platform.services.kafka import (
            _route_event,
            TOPIC_PATIENT_EVENTS,
        )

        assert _route_event("patient.admitted") == TOPIC_PATIENT_EVENTS

    def test_route_workflow_and_operations(self):
        from healthos_platform.services.kafka import (
            _route_event,
            TOPIC_WORKFLOW_EVENTS,
        )

        assert _route_event("workflow.started") == TOPIC_WORKFLOW_EVENTS
        assert _route_event("operations.sync") == TOPIC_WORKFLOW_EVENTS

    def test_route_unknown_defaults_to_agent(self):
        from healthos_platform.services.kafka import (
            _route_event,
            TOPIC_AGENT_EVENTS,
        )

        assert _route_event("unknown.event") == TOPIC_AGENT_EVENTS


@pytest.mark.asyncio
class TestPublishEvent:
    """Tests for Kafka producer publish_event."""

    @patch("healthos_platform.services.kafka.get_producer")
    async def test_publish_event_sends_to_topic(self, mock_get_producer):
        from healthos_platform.services.kafka import publish_event, HealthOSEvent

        mock_producer = AsyncMock()
        mock_get_producer.return_value = mock_producer

        event = HealthOSEvent(
            event_type="vitals.ingested",
            source="api",
            org_id="org-1",
            patient_id="patient-1",
            payload={"hr": 72},
        )
        await publish_event(event, topic="healthos.vitals.ingested")

        mock_producer.send_and_wait.assert_awaited_once()
        call_kwargs = mock_producer.send_and_wait.call_args
        assert call_kwargs[0][0] == "healthos.vitals.ingested"
        assert call_kwargs[1]["key"] == "patient-1"

    @patch("healthos_platform.services.kafka.get_producer")
    async def test_publish_event_uses_org_id_key_when_no_patient(self, mock_get_producer):
        from healthos_platform.services.kafka import publish_event, HealthOSEvent

        mock_producer = AsyncMock()
        mock_get_producer.return_value = mock_producer

        event = HealthOSEvent(
            event_type="agent.executed",
            source="agent:risk",
            org_id="org-99",
        )
        await publish_event(event)

        call_kwargs = mock_producer.send_and_wait.call_args
        assert call_kwargs[1]["key"] == "org-99"

    @patch("healthos_platform.services.kafka.get_producer")
    async def test_publish_event_auto_routes_topic(self, mock_get_producer):
        from healthos_platform.services.kafka import (
            publish_event,
            HealthOSEvent,
            TOPIC_ALERTS_GENERATED,
        )

        mock_producer = AsyncMock()
        mock_get_producer.return_value = mock_producer

        event = HealthOSEvent(
            event_type="alert.generated",
            source="agent",
            org_id="org-1",
        )
        await publish_event(event)  # no explicit topic

        call_kwargs = mock_producer.send_and_wait.call_args
        assert call_kwargs[0][0] == TOPIC_ALERTS_GENERATED


@pytest.mark.asyncio
class TestEventConsumer:
    """Tests for the EventConsumer dispatch logic."""

    async def test_register_and_dispatch_exact_match(self):
        from healthos_platform.services.kafka import EventConsumer, HealthOSEvent

        consumer = EventConsumer(topics=["healthos.vitals.ingested"])
        handler = AsyncMock()
        consumer.register("vitals.ingested", handler)

        raw = HealthOSEvent(
            event_type="vitals.ingested",
            source="api",
            org_id="org-1",
        ).model_dump()

        await consumer._dispatch(raw)
        handler.assert_awaited_once()
        received_event = handler.call_args[0][0]
        assert received_event.event_type == "vitals.ingested"

    async def test_dispatch_wildcard_match(self):
        from healthos_platform.services.kafka import EventConsumer, HealthOSEvent

        consumer = EventConsumer(topics=["healthos.vitals.ingested"])
        handler = AsyncMock()
        consumer.register("vitals.*", handler)

        raw = HealthOSEvent(
            event_type="vitals.ingested",
            source="api",
            org_id="org-1",
        ).model_dump()

        await consumer._dispatch(raw)
        handler.assert_awaited_once()

    async def test_dispatch_no_matching_handler(self):
        from healthos_platform.services.kafka import EventConsumer, HealthOSEvent

        consumer = EventConsumer(topics=["healthos.vitals.ingested"])
        handler = AsyncMock()
        consumer.register("alert.generated", handler)

        raw = HealthOSEvent(
            event_type="vitals.ingested",
            source="api",
            org_id="org-1",
        ).model_dump()

        await consumer._dispatch(raw)
        handler.assert_not_awaited()

    async def test_dispatch_handles_invalid_message(self):
        """Invalid raw messages should be logged, not raise."""
        from healthos_platform.services.kafka import EventConsumer

        consumer = EventConsumer(topics=["healthos.vitals.ingested"])
        # Missing required fields should not raise
        await consumer._dispatch({"bad": "data"})

    async def test_dispatch_handler_error_does_not_propagate(self):
        from healthos_platform.services.kafka import EventConsumer, HealthOSEvent

        consumer = EventConsumer(topics=["healthos.vitals.ingested"])
        handler = AsyncMock(side_effect=RuntimeError("boom"))
        consumer.register("vitals.ingested", handler)

        raw = HealthOSEvent(
            event_type="vitals.ingested",
            source="api",
            org_id="org-1",
        ).model_dump()

        # Should not raise
        await consumer._dispatch(raw)


# ---------------------------------------------------------------------------
# Cache service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHealthOSCache:
    """Tests for the HealthOSCache Redis wrapper."""

    @patch("healthos_platform.services.cache.get_redis")
    async def test_get_returns_deserialized_json(self, mock_get_redis):
        from healthos_platform.services.cache import HealthOSCache

        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({"score": 0.85})
        mock_get_redis.return_value = mock_redis

        cache = HealthOSCache(default_ttl=60)
        result = await cache.get("some:key")

        assert result == {"score": 0.85}
        mock_redis.get.assert_awaited_once_with("some:key")

    @patch("healthos_platform.services.cache.get_redis")
    async def test_get_returns_none_for_missing_key(self, mock_get_redis):
        from healthos_platform.services.cache import HealthOSCache

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        cache = HealthOSCache(default_ttl=60)
        result = await cache.get("missing:key")
        assert result is None

    @patch("healthos_platform.services.cache.get_redis")
    async def test_get_returns_raw_string_on_invalid_json(self, mock_get_redis):
        from healthos_platform.services.cache import HealthOSCache

        mock_redis = AsyncMock()
        mock_redis.get.return_value = "not-valid-json"
        mock_get_redis.return_value = mock_redis

        cache = HealthOSCache(default_ttl=60)
        result = await cache.get("str:key")
        assert result == "not-valid-json"

    @patch("healthos_platform.services.cache.get_redis")
    async def test_set_serializes_and_stores(self, mock_get_redis):
        from healthos_platform.services.cache import HealthOSCache

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        cache = HealthOSCache(default_ttl=120)
        await cache.set("my:key", {"a": 1}, ttl=300)

        mock_redis.set.assert_awaited_once_with(
            "my:key", json.dumps({"a": 1}), ex=300
        )

    @patch("healthos_platform.services.cache.get_redis")
    async def test_set_uses_default_ttl(self, mock_get_redis):
        from healthos_platform.services.cache import HealthOSCache

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        cache = HealthOSCache(default_ttl=999)
        await cache.set("key", "plain-string")

        mock_redis.set.assert_awaited_once_with("key", "plain-string", ex=999)

    @patch("healthos_platform.services.cache.get_redis")
    async def test_delete_removes_key(self, mock_get_redis):
        from healthos_platform.services.cache import HealthOSCache

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        cache = HealthOSCache(default_ttl=60)
        await cache.delete("old:key")

        mock_redis.delete.assert_awaited_once_with("old:key")

    @patch("healthos_platform.services.cache.get_redis")
    async def test_exists_returns_bool(self, mock_get_redis):
        from healthos_platform.services.cache import HealthOSCache

        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1
        mock_get_redis.return_value = mock_redis

        cache = HealthOSCache(default_ttl=60)
        assert await cache.exists("some:key") is True

    @patch("healthos_platform.services.cache.get_redis")
    async def test_check_rate_limit_allows_first_request(self, mock_get_redis):
        from healthos_platform.services.cache import HealthOSCache

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        cache = HealthOSCache(default_ttl=60)
        allowed = await cache.check_rate_limit("client-1", "/api/vitals")

        assert allowed is True
        mock_redis.set.assert_awaited_once_with(
            "healthos:ratelimit:client-1:/api/vitals", 1, ex=60
        )

    @patch("healthos_platform.services.cache.get_redis")
    async def test_check_rate_limit_blocks_over_limit(self, mock_get_redis):
        from healthos_platform.services.cache import HealthOSCache

        mock_redis = AsyncMock()
        mock_redis.get.return_value = "100"  # already at max
        mock_get_redis.return_value = mock_redis

        cache = HealthOSCache(default_ttl=60)
        allowed = await cache.check_rate_limit(
            "client-1", "/api/vitals", max_requests=100
        )
        assert allowed is False

    @patch("healthos_platform.services.cache.get_redis")
    async def test_check_rate_limit_increments_within_limit(self, mock_get_redis):
        from healthos_platform.services.cache import HealthOSCache

        mock_redis = AsyncMock()
        mock_redis.get.return_value = "50"
        mock_get_redis.return_value = mock_redis

        cache = HealthOSCache(default_ttl=60)
        allowed = await cache.check_rate_limit(
            "client-1", "/api/vitals", max_requests=100
        )
        assert allowed is True
        mock_redis.incr.assert_awaited_once()

    @patch("healthos_platform.services.cache.get_redis")
    async def test_patient_context_round_trip(self, mock_get_redis):
        from healthos_platform.services.cache import HealthOSCache

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        cache = HealthOSCache(default_ttl=60)
        ctx = {"conditions": ["diabetes"], "risk": 0.7}
        await cache.set_patient_context("p-123", ctx, ttl=300)

        expected_key = "healthos:patient:p-123:context"
        mock_redis.set.assert_awaited_once_with(
            expected_key, json.dumps(ctx), ex=300
        )

    @patch("healthos_platform.services.cache.get_redis")
    async def test_invalidate_pattern_scans_and_deletes(self, mock_get_redis):
        from healthos_platform.services.cache import HealthOSCache

        mock_redis = AsyncMock()
        mock_redis.scan.return_value = (0, ["key1", "key2"])
        mock_get_redis.return_value = mock_redis

        cache = HealthOSCache(default_ttl=60)
        deleted = await cache.invalidate_pattern("healthos:patient:p-1:*")

        assert deleted == 2
        mock_redis.delete.assert_awaited_once_with("key1", "key2")


# ---------------------------------------------------------------------------
# Knowledge graph service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestKnowledgeGraph:
    """Tests for KnowledgeGraph Neo4j operations."""

    def _mock_driver(self):
        """Build a mock Neo4j driver with session async context manager."""
        mock_session = AsyncMock()

        # Create a proper async context manager for driver.session()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_session)
        ctx.__aexit__ = AsyncMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = ctx
        return mock_driver, mock_session

    @patch("healthos_platform.services.knowledge_graph.get_driver")
    async def test_upsert_patient(self, mock_get_driver):
        from healthos_platform.services.knowledge_graph import KnowledgeGraph

        mock_driver, mock_session = self._mock_driver()
        mock_get_driver.return_value = mock_driver

        kg = KnowledgeGraph()
        await kg.upsert_patient(
            "p-1", "org-1", {"name": "Jane Doe", "dob": "1990-01-01", "gender": "F"}
        )

        mock_session.run.assert_awaited_once()
        call_kwargs = mock_session.run.call_args
        assert "MERGE (p:Patient" in call_kwargs[0][0]
        assert call_kwargs[1]["patient_id"] == "p-1"
        assert call_kwargs[1]["name"] == "Jane Doe"

    @patch("healthos_platform.services.knowledge_graph.get_driver")
    async def test_add_condition(self, mock_get_driver):
        from healthos_platform.services.knowledge_graph import KnowledgeGraph

        mock_driver, mock_session = self._mock_driver()
        mock_get_driver.return_value = mock_driver

        kg = KnowledgeGraph()
        await kg.add_condition("p-1", "E11", "Type 2 Diabetes", onset="2020-03")

        call_kwargs = mock_session.run.call_args
        assert "HAS_CONDITION" in call_kwargs[0][0]
        assert call_kwargs[1]["code"] == "E11"
        assert call_kwargs[1]["display"] == "Type 2 Diabetes"

    @patch("healthos_platform.services.knowledge_graph.get_driver")
    async def test_add_medication(self, mock_get_driver):
        from healthos_platform.services.knowledge_graph import KnowledgeGraph

        mock_driver, mock_session = self._mock_driver()
        mock_get_driver.return_value = mock_driver

        kg = KnowledgeGraph()
        await kg.add_medication("p-1", "Metformin", dose="500mg", frequency="BID")

        call_kwargs = mock_session.run.call_args
        assert "TAKES_MEDICATION" in call_kwargs[0][0]
        assert call_kwargs[1]["name"] == "Metformin"
        assert call_kwargs[1]["dose"] == "500mg"

    @patch("healthos_platform.services.knowledge_graph.get_driver")
    async def test_add_drug_interaction(self, mock_get_driver):
        from healthos_platform.services.knowledge_graph import KnowledgeGraph

        mock_driver, mock_session = self._mock_driver()
        mock_get_driver.return_value = mock_driver

        kg = KnowledgeGraph()
        await kg.add_drug_interaction(
            "Warfarin", "Aspirin", severity="high", description="Bleeding risk"
        )

        call_kwargs = mock_session.run.call_args
        assert "INTERACTS_WITH" in call_kwargs[0][0]
        assert call_kwargs[1]["drug_a"] == "Warfarin"
        assert call_kwargs[1]["severity"] == "high"

    @patch("healthos_platform.services.knowledge_graph.get_driver")
    async def test_get_patient_graph_empty(self, mock_get_driver):
        from healthos_platform.services.knowledge_graph import KnowledgeGraph

        mock_driver, mock_session = self._mock_driver()
        mock_get_driver.return_value = mock_driver

        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result

        kg = KnowledgeGraph()
        graph = await kg.get_patient_graph("p-nonexistent")
        assert graph == {}

    @patch("healthos_platform.services.knowledge_graph.get_driver")
    async def test_get_patient_graph_with_data(self, mock_get_driver):
        from healthos_platform.services.knowledge_graph import KnowledgeGraph

        mock_driver, mock_session = self._mock_driver()
        mock_get_driver.return_value = mock_driver

        mock_record = {
            "conditions": [
                {"code": "E11", "display": "Diabetes", "onset": "2020"},
                {"code": None, "display": None, "onset": None},  # filtered out
            ],
            "medications": [
                {"name": "Metformin", "dose": "500mg", "frequency": "BID"},
            ],
            "care_team": [
                {"id": "dr-1", "role": "PCP"},
            ],
        }
        mock_result = AsyncMock()
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        kg = KnowledgeGraph()
        graph = await kg.get_patient_graph("p-1")

        assert graph["patient_id"] == "p-1"
        assert len(graph["conditions"]) == 1
        assert graph["conditions"][0]["code"] == "E11"
        assert len(graph["medications"]) == 1
        assert len(graph["care_team"]) == 1

    @patch("healthos_platform.services.knowledge_graph.get_driver")
    async def test_sync_patient_from_db(self, mock_get_driver):
        from healthos_platform.services.knowledge_graph import KnowledgeGraph

        mock_driver, mock_session = self._mock_driver()
        mock_get_driver.return_value = mock_driver

        kg = KnowledgeGraph()
        patient_data = {
            "org_id": "org-1",
            "demographics": {"name": "John", "dob": "1985-05-15", "gender": "M"},
            "conditions": [{"code": "I10", "display": "Hypertension"}],
            "medications": [{"name": "Lisinopril", "dose": "10mg"}],
        }
        await kg.sync_patient_from_db("p-1", patient_data)

        # 1 upsert_patient + 1 add_condition + 1 add_medication = 3 calls
        assert mock_session.run.await_count == 3


# ---------------------------------------------------------------------------
# Vector store and RAG pipeline tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestVectorStore:
    """Tests for VectorStore embedding and search."""

    @patch("healthos_platform.services.vector_store.get_qdrant_client")
    def test_embed_single(self, _mock_client):
        from healthos_platform.services.vector_store import VectorStore

        store = VectorStore()
        mock_embedder = MagicMock()
        mock_embedder.encode.return_value = MagicMock(
            tolist=lambda: [[0.1, 0.2, 0.3]]
        )
        store._embedder = mock_embedder

        result = store.embed_single("patient has diabetes")
        assert result == [0.1, 0.2, 0.3]
        mock_embedder.encode.assert_called_once_with(
            ["patient has diabetes"], normalize_embeddings=True
        )

    @patch("healthos_platform.services.vector_store.get_qdrant_client")
    async def test_index_document(self, mock_get_client):
        from healthos_platform.services.vector_store import VectorStore

        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        store = VectorStore()
        store.embed_single = MagicMock(return_value=[0.1, 0.2, 0.3])

        await store.index_document(
            collection="clinical_notes",
            doc_id="doc-1",
            text="Patient presents with chest pain",
            metadata={"patient_id": "p-1", "org_id": "org-1"},
        )

        mock_client.upsert.assert_awaited_once()
        call_kwargs = mock_client.upsert.call_args[1]
        assert call_kwargs["collection_name"] == "clinical_notes"
        point = call_kwargs["points"][0]
        assert point.id == "doc-1"
        assert point.vector == [0.1, 0.2, 0.3]
        assert point.payload["text"] == "Patient presents with chest pain"
        assert point.payload["patient_id"] == "p-1"

    @patch("healthos_platform.services.vector_store.get_qdrant_client")
    async def test_search_returns_formatted_results(self, mock_get_client):
        from healthos_platform.services.vector_store import VectorStore

        mock_client = AsyncMock()
        mock_hit = MagicMock()
        mock_hit.id = "doc-1"
        mock_hit.score = 0.92
        mock_hit.payload = {
            "text": "Patient has diabetes",
            "patient_id": "p-1",
            "org_id": "org-1",
        }
        mock_client.search.return_value = [mock_hit]
        mock_get_client.return_value = mock_client

        store = VectorStore()
        store.embed_single = MagicMock(return_value=[0.1, 0.2, 0.3])

        results = await store.search("clinical_notes", "diabetes treatment")

        assert len(results) == 1
        assert results[0]["id"] == "doc-1"
        assert results[0]["score"] == 0.92
        assert results[0]["text"] == "Patient has diabetes"
        assert "patient_id" in results[0]["metadata"]
        assert "text" not in results[0]["metadata"]

    @patch("healthos_platform.services.vector_store.get_qdrant_client")
    async def test_search_with_filters(self, mock_get_client):
        from healthos_platform.services.vector_store import VectorStore

        mock_client = AsyncMock()
        mock_client.search.return_value = []
        mock_get_client.return_value = mock_client

        store = VectorStore()
        store.embed_single = MagicMock(return_value=[0.1, 0.2, 0.3])

        await store.search(
            "clinical_notes",
            "chest pain",
            filters={"patient_id": "p-1"},
        )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["query_filter"] is not None

    @patch("healthos_platform.services.vector_store.get_qdrant_client")
    async def test_ensure_collections_creates_missing(self, mock_get_client):
        from healthos_platform.services.vector_store import (
            VectorStore,
            COLLECTION_CLINICAL_NOTES,
            COLLECTION_CARE_PLANS,
            COLLECTION_MEDICAL_KNOWLEDGE,
            COLLECTION_PATIENT_SUMMARIES,
        )

        mock_client = AsyncMock()
        # Simulate one collection already existing
        existing_collection = MagicMock()
        existing_collection.name = COLLECTION_CLINICAL_NOTES
        collections_response = MagicMock()
        collections_response.collections = [existing_collection]
        mock_client.get_collections.return_value = collections_response
        mock_get_client.return_value = mock_client

        store = VectorStore()
        await store.ensure_collections()

        # Should create 3 collections (not clinical_notes, which already exists)
        assert mock_client.create_collection.await_count == 3


@pytest.mark.asyncio
class TestRAGPipeline:
    """Tests for the RAG retrieval pipeline."""

    async def test_retrieve_context_with_patient_id(self):
        from healthos_platform.services.vector_store import RAGPipeline, VectorStore

        mock_store = AsyncMock(spec=VectorStore)
        mock_store.search_clinical_notes.return_value = [
            {"id": "n1", "score": 0.9, "text": "note text", "metadata": {"note_type": "progress"}},
        ]
        mock_store.search_medical_knowledge.return_value = [
            {"id": "k1", "score": 0.8, "text": "knowledge text", "metadata": {"source": "uptodate"}},
        ]

        pipeline = RAGPipeline(vector_store=mock_store)
        results = await pipeline.retrieve_context(
            "diabetes management", patient_id="p-1", max_chunks=5
        )

        mock_store.search_clinical_notes.assert_awaited_once()
        mock_store.search_medical_knowledge.assert_awaited_once()
        # Results should be sorted by score descending
        assert results[0]["score"] >= results[-1]["score"]

    async def test_retrieve_context_without_patient_skips_notes(self):
        from healthos_platform.services.vector_store import RAGPipeline, VectorStore

        mock_store = AsyncMock(spec=VectorStore)
        mock_store.search_medical_knowledge.return_value = [
            {"id": "k1", "score": 0.8, "text": "knowledge", "metadata": {"source": "s"}},
        ]

        pipeline = RAGPipeline(vector_store=mock_store)
        results = await pipeline.retrieve_context("hypertension guidelines")

        mock_store.search_clinical_notes.assert_not_awaited()
        mock_store.search_medical_knowledge.assert_awaited_once()
        assert len(results) == 1

    @patch("healthos_platform.services.vector_store.get_settings")
    async def test_generate_answer_no_api_key(self, mock_settings):
        from healthos_platform.services.vector_store import RAGPipeline, VectorStore

        mock_settings.return_value = MagicMock(anthropic_api_key=None)

        mock_store = AsyncMock(spec=VectorStore)
        mock_store.search_clinical_notes.return_value = []
        mock_store.search_medical_knowledge.return_value = [
            {"id": "k1", "score": 0.85, "text": "knowledge", "metadata": {"source": "s"}},
        ]

        pipeline = RAGPipeline(vector_store=mock_store)
        result = await pipeline.generate_answer("what is diabetes?", patient_id="p-1")

        assert "query" in result
        assert "answer" in result
        assert "sources" in result
        assert "[LLM not configured]" in result["answer"]


# ---------------------------------------------------------------------------
# Workers (Celery task) tests
# ---------------------------------------------------------------------------


class TestCeleryTasks:
    """Tests for Celery task definitions and configuration."""

    def test_celery_app_configured(self):
        from healthos_platform.services.workers import celery_app

        assert celery_app.main == "healthos"
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.task_time_limit == 600
        assert celery_app.conf.task_soft_time_limit == 300

    def test_beat_schedule_has_required_tasks(self):
        from healthos_platform.services.workers import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "recalculate-risk-scores" in schedule
        assert "update-cohort-stats" in schedule
        assert "sync-ehr-data" in schedule
        assert "generate-population-metrics" in schedule
        assert "process-pending-alerts" in schedule

    def test_task_routes_configured(self):
        from healthos_platform.services.workers import celery_app

        routes = celery_app.conf.task_routes
        assert "healthos.tasks.risk.*" in routes
        assert routes["healthos.tasks.risk.*"]["queue"] == "healthos.risk"
        assert "healthos.tasks.ehr.*" in routes
        assert routes["healthos.tasks.ehr.*"]["queue"] == "healthos.ehr"

    def test_sync_patient_ehr_returns_result(self):
        from healthos_platform.services.workers import sync_patient_ehr

        result = sync_patient_ehr("p-1", "org-1", "epic")
        assert result["patient_id"] == "p-1"
        assert result["ehr_system"] == "epic"
        assert result["status"] == "completed"

    def test_send_alert_notification_returns_result(self):
        from healthos_platform.services.workers import send_alert_notification

        result = send_alert_notification("alert-1", ["email", "sms"])
        assert result["alert_id"] == "alert-1"
        assert result["channels"] == ["email", "sms"]
        assert result["status"] == "sent"

    def test_send_patient_reminder_returns_result(self):
        from healthos_platform.services.workers import send_patient_reminder

        result = send_patient_reminder("p-1", "medication", "Take your metformin")
        assert result["patient_id"] == "p-1"
        assert result["reminder_type"] == "medication"
        assert result["status"] == "sent"

    def test_generate_population_metrics_returns_result(self):
        from healthos_platform.services.workers import generate_population_metrics

        result = generate_population_metrics()
        assert result["status"] == "completed"
        assert "timestamp" in result


# ---------------------------------------------------------------------------
# EHR connector tests
# ---------------------------------------------------------------------------


class TestEHRRegistry:
    """Tests for the EHR connector registry."""

    def test_register_and_get(self):
        from healthos_platform.services.ehr import EHRRegistry, EpicConnector

        registry = EHRRegistry()
        connector = EpicConnector(
            base_url="https://epic.example.com",
            client_id="cid",
            client_secret="csec",
        )
        registry.register("org-1", connector)

        retrieved = registry.get("org-1")
        assert retrieved is connector
        assert retrieved.name == "epic"

    def test_get_missing_returns_none(self):
        from healthos_platform.services.ehr import EHRRegistry

        registry = EHRRegistry()
        assert registry.get("nonexistent") is None

    def test_list_connectors(self):
        from healthos_platform.services.ehr import (
            EHRRegistry,
            EpicConnector,
            CernerConnector,
        )

        registry = EHRRegistry()
        registry.register(
            "org-1",
            EpicConnector(
                base_url="https://epic.example.com",
                client_id="cid",
            ),
        )
        registry.register(
            "org-2",
            CernerConnector(
                base_url="https://cerner.example.com",
                client_id="cid",
                client_secret="csec",
            ),
        )

        listing = registry.list_connectors()
        assert len(listing) == 2
        names = {c["ehr"] for c in listing}
        assert names == {"epic", "cerner"}


class TestEHRConnectorAttributes:
    """Tests for EHR connector subclass attributes."""

    def test_epic_connector_attributes(self):
        from healthos_platform.services.ehr import EpicConnector

        connector = EpicConnector(
            base_url="https://epic.example.com/",
            client_id="epic-client",
            private_key_path="/path/to/key.pem",
        )
        assert connector.name == "epic"
        assert connector.fhir_version == "R4"
        assert connector.base_url == "https://epic.example.com"  # trailing slash stripped
        assert connector.private_key_path == "/path/to/key.pem"

    def test_cerner_connector_attributes(self):
        from healthos_platform.services.ehr import CernerConnector

        connector = CernerConnector(
            base_url="https://cerner.example.com",
            client_id="cerner-client",
            client_secret="cerner-secret",
            tenant_id="t-123",
        )
        assert connector.name == "cerner"
        assert connector.tenant_id == "t-123"

    def test_allscripts_connector_attributes(self):
        from healthos_platform.services.ehr import AllscriptsConnector

        connector = AllscriptsConnector(
            base_url="https://allscripts.example.com",
            client_id="as-client",
            client_secret="as-secret",
        )
        assert connector.name == "allscripts"


@pytest.mark.asyncio
class TestEHRConnectorRequests:
    """Tests for EHR connector HTTP operations."""

    @patch("healthos_platform.services.ehr.httpx.AsyncClient")
    async def test_get_patient_makes_fhir_request(self, mock_client_cls):
        from healthos_platform.services.ehr import EpicConnector

        connector = EpicConnector(
            base_url="https://epic.example.com",
            client_id="cid",
        )
        # Pre-set a token so authenticate is not called
        connector._access_token = "test-token"
        connector._token_expires_at = datetime(2099, 1, 1, tzinfo=timezone.utc)

        mock_response = MagicMock()
        mock_response.json.return_value = {"resourceType": "Patient", "id": "p-1"}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.request.return_value = mock_response
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_http

        result = await connector.get_patient("p-1")

        assert result["resourceType"] == "Patient"
        mock_http.request.assert_awaited_once()
        call_args = mock_http.request.call_args
        assert call_args[0][0] == "GET"
        assert "/fhir/r4/Patient/p-1" in call_args[0][1]
        # Check Bearer token in headers
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-token"

    @patch("healthos_platform.services.ehr.httpx.AsyncClient")
    async def test_sync_patient_data_aggregates_resources(self, mock_client_cls):
        from healthos_platform.services.ehr import CernerConnector

        connector = CernerConnector(
            base_url="https://cerner.example.com",
            client_id="cid",
            client_secret="csec",
        )
        connector._access_token = "test-token"
        connector._token_expires_at = datetime(2099, 1, 1, tzinfo=timezone.utc)

        mock_response = MagicMock()
        mock_response.json.return_value = {"resourceType": "Bundle", "entry": []}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.request.return_value = mock_response
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_http

        result = await connector.sync_patient_data("p-1")

        assert "patient" in result
        assert "observations" in result
        assert "conditions" in result
        assert "medications" in result
        assert "encounters" in result
        assert "allergies" in result
        assert "synced_at" in result

    async def test_get_token_reuses_valid_token(self):
        from healthos_platform.services.ehr import EpicConnector

        connector = EpicConnector(
            base_url="https://epic.example.com",
            client_id="cid",
        )
        connector._access_token = "cached-token"
        connector._token_expires_at = datetime(2099, 1, 1, tzinfo=timezone.utc)

        token = await connector._get_token()
        assert token == "cached-token"

    async def test_get_token_refreshes_expired_token(self):
        from healthos_platform.services.ehr import AllscriptsConnector

        connector = AllscriptsConnector(
            base_url="https://allscripts.example.com",
            client_id="cid",
            client_secret="csec",
        )
        # Expired token
        connector._access_token = "old-token"
        connector._token_expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)

        connector.authenticate = AsyncMock(return_value="new-token")
        token = await connector._get_token()
        assert token == "new-token"
        connector.authenticate.assert_awaited_once()
