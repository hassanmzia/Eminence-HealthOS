"""
Eminence HealthOS — Neo4j Knowledge Graph Service
Models clinical relationships: Patient→Condition, Patient→Medication,
Condition→Medication interactions, Care pathways, Provider networks.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from healthos_platform.config import get_settings

logger = structlog.get_logger()

_driver = None


async def get_driver():
    """Get or create the Neo4j async driver."""
    global _driver
    if _driver is None:
        from neo4j import AsyncGraphDatabase

        settings = get_settings()
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_pool_size=20,
        )
        logger.info("neo4j.connected", uri=settings.neo4j_uri)
    return _driver


async def close_driver():
    """Close the Neo4j driver."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
        logger.info("neo4j.closed")


class KnowledgeGraph:
    """
    Clinical knowledge graph operations.

    Node types: Patient, Condition, Medication, Provider, Procedure, LabTest
    Edge types: HAS_CONDITION, TAKES_MEDICATION, TREATS, INTERACTS_WITH,
                ORDERED_BY, CARE_TEAM_MEMBER, REFERRED_TO
    """

    # ── Patient Graph ─────────────────────────────────────────────────────

    async def upsert_patient(self, patient_id: str, org_id: str, demographics: dict[str, Any]) -> None:
        """Create or update a Patient node with its relationships."""
        driver = await get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (p:Patient {id: $patient_id})
                SET p.org_id = $org_id,
                    p.name = $name,
                    p.dob = $dob,
                    p.gender = $gender,
                    p.updated_at = datetime()
                """,
                patient_id=patient_id,
                org_id=org_id,
                name=demographics.get("name", ""),
                dob=demographics.get("dob", ""),
                gender=demographics.get("gender", ""),
            )
        logger.info("kg.patient.upserted", patient_id=patient_id)

    async def add_condition(self, patient_id: str, condition_code: str, display: str, onset: str = "") -> None:
        """Add a condition to a patient."""
        driver = await get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (c:Condition {code: $code})
                SET c.display = $display
                WITH c
                MATCH (p:Patient {id: $patient_id})
                MERGE (p)-[r:HAS_CONDITION]->(c)
                SET r.onset = $onset, r.active = true
                """,
                patient_id=patient_id,
                code=condition_code,
                display=display,
                onset=onset,
            )

    async def add_medication(self, patient_id: str, medication_name: str, dose: str = "", frequency: str = "") -> None:
        """Add a medication to a patient."""
        driver = await get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (m:Medication {name: $name})
                WITH m
                MATCH (p:Patient {id: $patient_id})
                MERGE (p)-[r:TAKES_MEDICATION]->(m)
                SET r.dose = $dose, r.frequency = $frequency, r.active = true
                """,
                patient_id=patient_id,
                name=medication_name,
                dose=dose,
                frequency=frequency,
            )

    async def add_care_team_member(self, patient_id: str, provider_id: str, role: str) -> None:
        """Link a provider to a patient's care team."""
        driver = await get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (pr:Provider {id: $provider_id})
                WITH pr
                MATCH (p:Patient {id: $patient_id})
                MERGE (p)-[r:CARE_TEAM_MEMBER]->(pr)
                SET r.role = $role
                """,
                patient_id=patient_id,
                provider_id=provider_id,
                role=role,
            )

    # ── Clinical Relationships ────────────────────────────────────────────

    async def add_drug_interaction(
        self, drug_a: str, drug_b: str, severity: str, description: str
    ) -> None:
        """Record a drug-drug interaction in the knowledge graph."""
        driver = await get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (a:Medication {name: $drug_a})
                MERGE (b:Medication {name: $drug_b})
                MERGE (a)-[r:INTERACTS_WITH]->(b)
                SET r.severity = $severity, r.description = $description
                """,
                drug_a=drug_a,
                drug_b=drug_b,
                severity=severity,
                description=description,
            )

    async def add_treatment_relationship(
        self, condition_code: str, medication_name: str, evidence_level: str = "standard"
    ) -> None:
        """Record that a medication treats a condition."""
        driver = await get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (c:Condition {code: $code})
                MERGE (m:Medication {name: $medication})
                MERGE (m)-[r:TREATS]->(c)
                SET r.evidence_level = $evidence
                """,
                code=condition_code,
                medication=medication_name,
                evidence=evidence_level,
            )

    # ── Queries ───────────────────────────────────────────────────────────

    async def get_patient_graph(self, patient_id: str) -> dict[str, Any]:
        """Get the full knowledge graph for a patient."""
        driver = await get_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (p:Patient {id: $patient_id})
                OPTIONAL MATCH (p)-[hc:HAS_CONDITION]->(c:Condition)
                OPTIONAL MATCH (p)-[tm:TAKES_MEDICATION]->(m:Medication)
                OPTIONAL MATCH (p)-[ct:CARE_TEAM_MEMBER]->(pr:Provider)
                RETURN p,
                    collect(DISTINCT {code: c.code, display: c.display, onset: hc.onset}) AS conditions,
                    collect(DISTINCT {name: m.name, dose: tm.dose, frequency: tm.frequency}) AS medications,
                    collect(DISTINCT {id: pr.id, role: ct.role}) AS care_team
                """,
                patient_id=patient_id,
            )
            record = await result.single()
            if not record:
                return {}

            return {
                "patient_id": patient_id,
                "conditions": [c for c in record["conditions"] if c.get("code")],
                "medications": [m for m in record["medications"] if m.get("name")],
                "care_team": [ct for ct in record["care_team"] if ct.get("id")],
            }

    async def find_drug_interactions(self, medication_names: list[str]) -> list[dict[str, Any]]:
        """Find interactions between a set of medications."""
        driver = await get_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                UNWIND $meds AS med_name
                MATCH (a:Medication {name: med_name})-[r:INTERACTS_WITH]-(b:Medication)
                WHERE b.name IN $meds AND a.name < b.name
                RETURN a.name AS drug_a, b.name AS drug_b,
                       r.severity AS severity, r.description AS description
                """,
                meds=medication_names,
            )
            return [dict(record) async for record in result]

    async def find_related_patients(self, patient_id: str, max_hops: int = 2) -> list[dict[str, Any]]:
        """Find patients with similar conditions (for cohort analysis)."""
        driver = await get_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(c:Condition)
                    <-[:HAS_CONDITION]-(other:Patient)
                WHERE other.id <> $patient_id
                WITH other, collect(c.display) AS shared_conditions, count(c) AS overlap
                ORDER BY overlap DESC
                LIMIT 20
                RETURN other.id AS patient_id, shared_conditions, overlap
                """,
                patient_id=patient_id,
            )
            return [dict(record) async for record in result]

    async def get_care_pathway(self, condition_code: str) -> dict[str, Any]:
        """Get the standard care pathway for a condition."""
        driver = await get_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Condition {code: $code})
                OPTIONAL MATCH (m:Medication)-[t:TREATS]->(c)
                OPTIONAL MATCH (l:LabTest)-[:MONITORS]->(c)
                RETURN c.display AS condition,
                    collect(DISTINCT {name: m.name, evidence: t.evidence_level}) AS treatments,
                    collect(DISTINCT {name: l.name, frequency: l.frequency}) AS monitoring
                """,
                code=condition_code,
            )
            record = await result.single()
            if not record:
                return {"condition_code": condition_code, "treatments": [], "monitoring": []}
            return {
                "condition_code": condition_code,
                "condition_name": record["condition"],
                "treatments": [t for t in record["treatments"] if t.get("name")],
                "monitoring": [m for m in record["monitoring"] if m.get("name")],
            }

    # ── Bulk Operations ───────────────────────────────────────────────────

    async def sync_patient_from_db(self, patient_id: str, patient_data: dict[str, Any]) -> None:
        """Sync a full patient record from the relational DB into the knowledge graph."""
        await self.upsert_patient(
            patient_id=patient_id,
            org_id=patient_data.get("org_id", ""),
            demographics=patient_data.get("demographics", {}),
        )

        for condition in patient_data.get("conditions", []):
            await self.add_condition(
                patient_id=patient_id,
                condition_code=condition.get("code", ""),
                display=condition.get("display", ""),
                onset=condition.get("onset", ""),
            )

        for medication in patient_data.get("medications", []):
            await self.add_medication(
                patient_id=patient_id,
                medication_name=medication.get("name", ""),
                dose=medication.get("dose", ""),
                frequency=medication.get("frequency", ""),
            )

        logger.info("kg.patient.synced", patient_id=patient_id)


# Module-level instance
knowledge_graph = KnowledgeGraph()
