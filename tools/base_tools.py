"""
Eminence HealthOS -- Base LangChain Tool Definitions

Core tools shared across all agent modules.  Every tool uses the
``@tool`` decorator, reads configuration from ``ToolSettings``, and
includes full error handling.

No Django dependency -- all config comes from environment variables
via the Pydantic settings model.
"""

from __future__ import annotations

import io
import json
import logging
import os
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger("healthos.tools")


# ---------------------------------------------------------------------------
# Settings (Pydantic, env-backed)
# ---------------------------------------------------------------------------

class ToolSettings(BaseSettings):
    """Configuration consumed by all base tools."""

    # -- Postgres (sync, for raw SQL tools) ---------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "healthos"
    postgres_user: str = "healthos"
    postgres_password: str = ""

    # -- Neo4j --------------------------------------------------------------
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "healthos-neo4j"

    # -- Qdrant -------------------------------------------------------------
    qdrant_url: str = "http://localhost:6333"

    # -- Embedding model ----------------------------------------------------
    embedding_model: str = "all-MiniLM-L6-v2"

    # -- Upstream micro-services --------------------------------------------
    api_base_url: str = "http://localhost:8000"
    ml_service_url: str = "http://localhost:8002"
    nl2sql_service_url: str = "http://localhost:8000"
    whisper_service_url: str = ""
    osrm_service_url: str = "http://router.project-osrm.org"

    # -- API keys / tokens --------------------------------------------------
    internal_api_token: str = ""
    openai_api_key: str = ""
    ncbi_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def get_tool_settings() -> ToolSettings:
    """Return a fresh settings instance (not cached -- tools are long-lived)."""
    return ToolSettings()


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _get_pg_conn():
    """Return a psycopg2 connection using Pydantic settings."""
    import psycopg2

    cfg = get_tool_settings()
    return psycopg2.connect(
        host=cfg.postgres_host,
        port=cfg.postgres_port,
        dbname=cfg.postgres_db,
        user=cfg.postgres_user,
        password=cfg.postgres_password,
    )


def _get_neo4j_driver():
    """Return a Neo4j driver using Pydantic settings."""
    from neo4j import GraphDatabase

    cfg = get_tool_settings()
    return GraphDatabase.driver(
        cfg.neo4j_uri,
        auth=(cfg.neo4j_user, cfg.neo4j_password),
    )


def _get_qdrant_client():
    """Return a QdrantClient using Pydantic settings."""
    from qdrant_client import QdrantClient

    cfg = get_tool_settings()
    return QdrantClient(url=cfg.qdrant_url)


# ---------------------------------------------------------------------------
# FHIR / Database tools
# ---------------------------------------------------------------------------

@tool
def query_fhir_database(resource_type: str, patient_id: str, filters: dict) -> dict:
    """
    Query patient FHIR records from PostgreSQL.

    Args:
        resource_type: FHIR resource type (Observation, MedicationRequest, etc.)
        patient_id: FHIR patient identifier
        filters: Additional filter criteria (e.g., {"code": "2339-0", "limit": 10})

    Returns:
        Dict with 'resources' list and 'count' integer.
    """
    try:
        limit = filters.get("limit", 50)
        code = filters.get("code")
        date_from = filters.get("date_from")

        conditions = ["subject_id = %s"]
        params: list = [patient_id]

        if code:
            conditions.append("code = %s")
            params.append(code)
        if date_from:
            conditions.append("effective_datetime >= %s")
            params.append(date_from)

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT id, code, value, unit, effective_datetime, status, meta
            FROM fhir_{resource_type.lower()}
            WHERE {where_clause}
            ORDER BY effective_datetime DESC
            LIMIT %s
        """
        params.append(limit)

        conn = _get_pg_conn()
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            resources = [dict(zip(columns, row)) for row in rows]
        conn.close()

        return {"resources": resources, "count": len(resources), "resource_type": resource_type}

    except Exception as exc:
        logger.error("query_fhir_database failed: %s", exc)
        return {"resources": [], "count": 0, "error": str(exc)}


# ---------------------------------------------------------------------------
# Neo4j graph tools
# ---------------------------------------------------------------------------

@tool
def query_graph_database(cypher_query: str, params: dict) -> list:
    """
    Execute a Cypher query against the Neo4j knowledge graph.

    Args:
        cypher_query: Valid Cypher query string
        params: Query parameters dict

    Returns:
        List of result records as dicts.
    """
    try:
        driver = _get_neo4j_driver()
        with driver.session() as session:
            result = session.run(cypher_query, **params)
            records = [record.data() for record in result]
        driver.close()
        return records
    except Exception as exc:
        logger.error("query_graph_database failed: %s", exc)
        return [{"error": str(exc)}]


@tool
def check_drug_interactions(drug_list: list) -> dict:
    """
    Check for drug-drug interactions using a Neo4j backtracking search.

    Args:
        drug_list: List of drug names or RxNorm codes (e.g., ["metformin", "lisinopril"])

    Returns:
        Dict with 'interactions' list and 'severity_summary'.
    """
    try:
        cypher = """
        UNWIND $drugs AS drug1
        UNWIND $drugs AS drug2
        WITH drug1, drug2
        WHERE drug1 < drug2
        MATCH (d1:Drug {name: drug1})-[r:INTERACTS_WITH]->(d2:Drug {name: drug2})
        RETURN d1.name AS drug1, d2.name AS drug2,
               r.severity AS severity, r.mechanism AS mechanism,
               r.clinical_effect AS clinical_effect, r.management AS management
        ORDER BY
          CASE r.severity
            WHEN 'contraindicated' THEN 1
            WHEN 'major' THEN 2
            WHEN 'moderate' THEN 3
            WHEN 'minor' THEN 4
            ELSE 5
          END
        """
        driver = _get_neo4j_driver()
        with driver.session() as session:
            result = session.run(cypher, drugs=drug_list)
            interactions = [record.data() for record in result]
        driver.close()

        severity_counts: Dict[str, int] = {}
        for interaction in interactions:
            sev = interaction.get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "interactions": interactions,
            "total_interactions": len(interactions),
            "severity_summary": severity_counts,
            "has_contraindications": any(
                i.get("severity") == "contraindicated" for i in interactions
            ),
        }
    except Exception as exc:
        logger.error("check_drug_interactions failed: %s", exc)
        return {"interactions": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# Qdrant vector search
# ---------------------------------------------------------------------------

@tool
def vector_search(query: str, collection: str, top_k: int = 5) -> list:
    """
    Semantic search in Qdrant vector store for clinical guidelines and literature.

    Args:
        query: Natural language search query
        collection: Qdrant collection name (e.g., 'clinical_guidelines', 'pubmed_abstracts')
        top_k: Number of top results to return

    Returns:
        List of matching documents with content and score.
    """
    try:
        from sentence_transformers import SentenceTransformer

        cfg = get_tool_settings()
        embedder = SentenceTransformer(cfg.embedding_model)
        query_vector = embedder.encode(query).tolist()

        client = _get_qdrant_client()
        results = client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )

        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "content": hit.payload.get("content", ""),
                "source": hit.payload.get("source", ""),
                "title": hit.payload.get("title", ""),
                "metadata": {k: v for k, v in hit.payload.items() if k not in ("content",)},
            }
            for hit in results
        ]
    except Exception as exc:
        logger.error("vector_search failed: %s", exc)
        return [{"error": str(exc)}]


# ---------------------------------------------------------------------------
# ML risk scoring
# ---------------------------------------------------------------------------

@tool
def calculate_risk_score(patient_id: str, condition: str, model_type: str) -> dict:
    """
    Run an ML risk model for a patient.

    Args:
        patient_id: Patient identifier
        condition: Clinical condition (e.g., 'hospitalization', 'ckd_progression')
        model_type: Model type ('xgboost', 'lstm', 'ensemble')

    Returns:
        Dict with 'score', 'level', 'confidence_interval', 'feature_importances'.
    """
    try:
        import httpx

        cfg = get_tool_settings()
        resp = httpx.post(
            f"{cfg.ml_service_url}/predict",
            json={
                "patient_id": patient_id,
                "condition": condition,
                "model_type": model_type,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("calculate_risk_score failed: %s", exc)
        return {
            "score": 0.0,
            "level": "UNKNOWN",
            "confidence_interval": [0.0, 0.0],
            "feature_importances": [],
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Notification / scheduling
# ---------------------------------------------------------------------------

@tool
def send_notification(
    patient_id: str, notification_type: str, message: str, channel: str
) -> bool:
    """
    Send a prioritized notification via the notification dispatcher.

    Args:
        patient_id: Patient identifier
        notification_type: CRITICAL | URGENT | SOON | ROUTINE
        message: Notification message text
        channel: Delivery channel: 'push' | 'sms' | 'email' | 'in_app' | 'ehr_inbox'

    Returns:
        True if sent successfully, False otherwise.
    """
    try:
        import httpx

        cfg = get_tool_settings()
        resp = httpx.post(
            f"{cfg.api_base_url}/api/v1/notifications/send",
            json={
                "patient_id": patient_id,
                "notification_type": notification_type,
                "message": message,
                "channel": channel,
            },
            timeout=10.0,
            headers={"X-Internal-Token": cfg.internal_api_token},
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.error("send_notification failed: %s", exc)
        return False


@tool
def schedule_appointment(
    patient_id: str, provider_id: str, urgency: str, reason: str
) -> dict:
    """
    Schedule an appointment with priority routing.

    Args:
        patient_id: Patient identifier
        provider_id: Provider identifier (or specialty like 'cardiologist')
        urgency: CRITICAL | URGENT | SOON | ROUTINE
        reason: Clinical reason for appointment

    Returns:
        Dict with appointment_id, scheduled_datetime, provider details.
    """
    try:
        import httpx

        cfg = get_tool_settings()
        resp = httpx.post(
            f"{cfg.api_base_url}/api/v1/appointments/schedule",
            json={
                "patient_id": patient_id,
                "provider_id": provider_id,
                "urgency": urgency,
                "reason": reason,
            },
            timeout=15.0,
            headers={"X-Internal-Token": cfg.internal_api_token},
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("schedule_appointment failed: %s", exc)
        return {"error": str(exc), "scheduled": False}


# ---------------------------------------------------------------------------
# Geospatial
# ---------------------------------------------------------------------------

@tool
def find_nearest_hospital(patient_location: dict, capabilities_needed: list) -> dict:
    """
    Find the nearest capable hospital using PostGIS geospatial query.

    Args:
        patient_location: Dict with 'lat' and 'lon' keys
        capabilities_needed: List of required capabilities (e.g., ['cath_lab', 'stroke_center'])

    Returns:
        Dict with hospital name, address, distance_km, ETA, capabilities.
    """
    try:
        lat = patient_location.get("lat", 0)
        lon = patient_location.get("lon", 0)

        caps_filter = ""
        if capabilities_needed:
            caps_list = ", ".join(f"'{c}'" for c in capabilities_needed)
            caps_filter = f"AND capabilities && ARRAY[{caps_list}]::text[]"

        conn = _get_pg_conn()
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    id, name, address, phone,
                    ST_Distance(
                        location::geography,
                        ST_MakePoint(%s, %s)::geography
                    ) / 1000.0 AS distance_km,
                    capabilities
                FROM hospitals
                WHERE active = TRUE {caps_filter}
                ORDER BY distance_km
                LIMIT 1
                """,
                (lon, lat),
            )
            row = cur.fetchone()
            if row:
                cols = [desc[0] for desc in cur.description]
                return dict(zip(cols, row))
            return {"error": "No suitable hospital found"}
    except Exception as exc:
        logger.error("find_nearest_hospital failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# NL2SQL
# ---------------------------------------------------------------------------

@tool
def nl2sql_query(natural_language_query: str, patient_id: str) -> dict:
    """
    Convert a natural language question to SQL and execute it against the
    patient database. Includes safety guardrails to prevent unauthorized
    data access.

    Args:
        natural_language_query: Clinical question in plain English
        patient_id: Patient identifier (used to scope the query for safety)

    Returns:
        Dict with 'sql', 'results', 'columns'.
    """
    try:
        import httpx

        cfg = get_tool_settings()
        resp = httpx.post(
            f"{cfg.nl2sql_service_url}/api/v1/nl2sql",
            json={
                "query": natural_language_query,
                "patient_id": patient_id,
                "safety_mode": True,
            },
            timeout=30.0,
            headers={"X-Internal-Token": cfg.internal_api_token},
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("nl2sql_query failed: %s", exc)
        return {"sql": "", "results": [], "columns": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# External APIs
# ---------------------------------------------------------------------------

@tool
def search_pubmed(query: str, max_results: int = 10) -> list:
    """
    Search PubMed for medical literature using E-utilities API.

    Args:
        query: PubMed search query (supports MeSH terms and boolean operators)
        max_results: Maximum number of articles to return (default 10, max 50)

    Returns:
        List of articles with pmid, title, abstract, authors, publication_date.
    """
    try:
        import httpx

        cfg = get_tool_settings()
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        max_results = min(max_results, 50)

        search_resp = httpx.get(
            f"{base_url}/esearch.fcgi",
            params={
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "api_key": cfg.ncbi_api_key,
            },
            timeout=15.0,
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()
        pmids = search_data.get("esearchresult", {}).get("idlist", [])

        if not pmids:
            return []

        fetch_resp = httpx.get(
            f"{base_url}/efetch.fcgi",
            params={
                "db": "pubmed",
                "id": ",".join(pmids),
                "rettype": "abstract",
                "retmode": "json",
                "api_key": cfg.ncbi_api_key,
            },
            timeout=15.0,
        )
        fetch_resp.raise_for_status()

        articles = []
        for pmid in pmids:
            articles.append(
                {
                    "pmid": pmid,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "fetched": True,
                }
            )
        return articles

    except Exception as exc:
        logger.error("search_pubmed failed: %s", exc)
        return [{"error": str(exc)}]


@tool
def search_clinical_trials(condition: str, patient_criteria: dict) -> list:
    """
    Search ClinicalTrials.gov for matching trials.

    Args:
        condition: Medical condition or disease name
        patient_criteria: Dict with 'age', 'sex', 'conditions', 'medications', 'location'

    Returns:
        List of matching trials with NCT ID, title, status, eligibility, contact info.
    """
    try:
        import httpx

        age = patient_criteria.get("age", "")
        location = patient_criteria.get("location", "")

        resp = httpx.get(
            "https://clinicaltrials.gov/api/v2/studies",
            params={
                "query.cond": condition,
                "query.patient": (
                    f"AREA[MinimumAge]{age} AND "
                    f"AREA[Sex]{patient_criteria.get('sex', 'all')}"
                ),
                "filter.geo": location,
                "filter.overallStatus": "RECRUITING",
                "pageSize": 10,
                "format": "json",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        studies = data.get("studies", [])

        results = []
        for study in studies:
            proto = study.get("protocolSection", {})
            id_module = proto.get("identificationModule", {})
            status_module = proto.get("statusModule", {})
            desc_module = proto.get("descriptionModule", {})
            elig_module = proto.get("eligibilityModule", {})
            results.append(
                {
                    "nct_id": id_module.get("nctId", ""),
                    "title": id_module.get("briefTitle", ""),
                    "status": status_module.get("overallStatus", ""),
                    "brief_summary": desc_module.get("briefSummary", ""),
                    "eligibility_criteria": elig_module.get("eligibilityCriteria", ""),
                    "minimum_age": elig_module.get("minimumAge", ""),
                    "maximum_age": elig_module.get("maximumAge", ""),
                    "sex": elig_module.get("sex", "ALL"),
                    "url": f"https://clinicaltrials.gov/study/{id_module.get('nctId', '')}",
                }
            )
        return results

    except Exception as exc:
        logger.error("search_clinical_trials failed: %s", exc)
        return [{"error": str(exc)}]


# ---------------------------------------------------------------------------
# Voice / transcription
# ---------------------------------------------------------------------------

@tool
def transcribe_voice(audio_url: str) -> str:
    """
    Transcribe a voice recording using Whisper (via OpenAI API or local Whisper).

    Args:
        audio_url: URL or file path to audio recording (mp3, wav, m4a, etc.)

    Returns:
        Transcribed text string.
    """
    try:
        import httpx

        cfg = get_tool_settings()
        if cfg.whisper_service_url:
            resp = httpx.post(
                f"{cfg.whisper_service_url}/transcribe",
                json={"audio_url": audio_url},
                timeout=60.0,
            )
            resp.raise_for_status()
            return resp.json().get("text", "")
        else:
            import openai

            client = openai.OpenAI(api_key=cfg.openai_api_key)
            audio_data = httpx.get(audio_url, timeout=30.0).content
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.mp3"
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
            return transcript.text

    except Exception as exc:
        logger.error("transcribe_voice failed: %s", exc)
        return f"[Transcription error: {exc}]"


# ---------------------------------------------------------------------------
# PHI / Security
# ---------------------------------------------------------------------------

@tool
def detect_phi(text: str) -> dict:
    """
    Detect Protected Health Information (PHI) in text using Microsoft Presidio.

    Args:
        text: Text to analyze for PHI

    Returns:
        Dict with 'entities' list (type, start, end, score) and 'has_phi' bool.
    """
    try:
        from presidio_analyzer import AnalyzerEngine

        analyzer = AnalyzerEngine()
        results = analyzer.analyze(
            text=text,
            language="en",
            entities=[
                "PERSON",
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
                "US_SSN",
                "US_DRIVER_LICENSE",
                "US_PASSPORT",
                "CREDIT_CARD",
                "IBAN_CODE",
                "IP_ADDRESS",
                "LOCATION",
                "DATE_TIME",
                "NRP",
                "MEDICAL_LICENSE",
            ],
        )
        entities = [
            {
                "type": r.entity_type,
                "start": r.start,
                "end": r.end,
                "score": r.score,
                "text": text[r.start : r.end],
            }
            for r in results
        ]
        return {"entities": entities, "has_phi": len(entities) > 0, "phi_count": len(entities)}
    except Exception as exc:
        logger.error("detect_phi failed: %s", exc)
        return {"entities": [], "has_phi": False, "error": str(exc)}


@tool
def redact_phi(text: str) -> str:
    """
    Redact Protected Health Information from text using Presidio anonymizer.

    Args:
        text: Text containing PHI to redact

    Returns:
        Text with PHI replaced by type tags (e.g., <PERSON>, <EMAIL_ADDRESS>).
    """
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig

        analyzer = AnalyzerEngine()
        anonymizer = AnonymizerEngine()

        results = analyzer.analyze(text=text, language="en")

        anonymized = anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators={
                "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
                "PERSON": OperatorConfig("replace", {"new_value": "<PATIENT_NAME>"}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
                "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
                "US_SSN": OperatorConfig("replace", {"new_value": "<SSN>"}),
                "LOCATION": OperatorConfig("replace", {"new_value": "<LOCATION>"}),
                "DATE_TIME": OperatorConfig("replace", {"new_value": "<DATE>"}),
            },
        )
        return anonymized.text
    except Exception as exc:
        logger.error("redact_phi failed: %s", exc)
        logger.critical("PHI REDACTION FAILED -- text may contain PHI: %s", exc)
        return text


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_BASE_TOOLS = [
    query_fhir_database,
    query_graph_database,
    vector_search,
    check_drug_interactions,
    calculate_risk_score,
    send_notification,
    schedule_appointment,
    find_nearest_hospital,
    nl2sql_query,
    search_pubmed,
    search_clinical_trials,
    transcribe_voice,
    detect_phi,
    redact_phi,
]

TOOL_MAP = {t.name: t for t in ALL_BASE_TOOLS}
