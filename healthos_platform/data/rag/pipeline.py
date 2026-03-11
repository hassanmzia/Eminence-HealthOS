"""
Eminence HealthOS — RAG Pipeline for Clinical Knowledge Retrieval

Retrieval-Augmented Generation pipeline that:
1. Accepts clinical queries (symptoms, conditions, drug questions)
2. Retrieves relevant context from the vector store
3. Augments agent prompts with retrieved clinical knowledge
4. Returns structured context for downstream agents
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from healthos_platform.data.vector_store.store import VectorStore

logger = logging.getLogger("healthos.rag")


# Built-in clinical knowledge snippets (fallback when vector store is empty)
BUILTIN_KNOWLEDGE: list[dict[str, Any]] = [
    {
        "category": "vital_thresholds",
        "title": "Normal Vital Sign Ranges (Adults)",
        "text": (
            "Normal vital sign ranges for adults: "
            "Heart rate: 60-100 bpm. "
            "Systolic BP: 90-120 mmHg, Diastolic BP: 60-80 mmHg. "
            "Respiratory rate: 12-20 breaths/min. "
            "SpO2: 95-100%. "
            "Temperature: 97.8-99.1°F (36.5-37.3°C). "
            "Fasting glucose: 70-100 mg/dL."
        ),
    },
    {
        "category": "clinical_guidelines",
        "title": "Heart Failure Management — ACC/AHA",
        "text": (
            "Heart failure management guidelines (ACC/AHA): "
            "Daily weight monitoring — report >2lb gain in 24h or >5lb in a week. "
            "Fluid restriction 1.5-2L/day. Low sodium diet <2g/day. "
            "Target BP <130/80. Monitor for signs of decompensation: "
            "dyspnea, orthopnea, peripheral edema, fatigue."
        ),
    },
    {
        "category": "clinical_guidelines",
        "title": "Diabetes Management — ADA Standards",
        "text": (
            "Diabetes management (ADA Standards of Care): "
            "A1C target <7% for most adults. "
            "Fasting glucose target: 80-130 mg/dL. "
            "Post-prandial glucose: <180 mg/dL. "
            "Monitor for hypoglycemia: glucose <70 mg/dL. "
            "Annual eye exam, foot exam, kidney function tests."
        ),
    },
    {
        "category": "clinical_guidelines",
        "title": "Hypertension Management — JNC 8",
        "text": (
            "Hypertension management: "
            "Target BP <130/80 for most adults. "
            "First-line medications: ACE inhibitors, ARBs, calcium channel blockers, thiazide diuretics. "
            "Lifestyle: DASH diet, sodium <2.3g/day, regular exercise 150min/week, "
            "limit alcohol, weight management."
        ),
    },
    {
        "category": "clinical_guidelines",
        "title": "COPD Management — GOLD",
        "text": (
            "COPD management (GOLD guidelines): "
            "Smoking cessation is the most effective intervention. "
            "Bronchodilators (LABA/LAMA) as maintenance therapy. "
            "Inhaled corticosteroids for frequent exacerbations. "
            "Pulmonary rehabilitation. Annual influenza and pneumococcal vaccines. "
            "Monitor SpO2 — target >88%. Exacerbation action plan."
        ),
    },
    {
        "category": "drug_reference",
        "title": "Common Drug Interactions — High Risk",
        "text": (
            "High-risk drug interactions: "
            "Warfarin + NSAIDs: increased bleeding risk. "
            "ACE inhibitors + potassium-sparing diuretics: hyperkalemia. "
            "Statins + fibrates: rhabdomyolysis risk. "
            "SSRIs + MAOIs: serotonin syndrome. "
            "Metformin + contrast dye: lactic acidosis risk (hold 48h)."
        ),
    },
    {
        "category": "telehealth_protocols",
        "title": "Telehealth Encounter Workflow",
        "text": (
            "Telehealth encounter standard workflow: "
            "1. Pre-visit: symptom assessment, vital review, medication reconciliation. "
            "2. Provider review of pre-visit summary and AI agent findings. "
            "3. Virtual encounter with patient (video/audio). "
            "4. Clinical documentation (SOAP note generation). "
            "5. Care plan update and follow-up scheduling. "
            "6. After-visit summary delivery to patient."
        ),
    },
]


class RAGPipeline:
    """
    Clinical knowledge retrieval pipeline.

    Uses vector similarity search with fallback to built-in knowledge base.
    """

    def __init__(self, vector_store: VectorStore | None = None):
        self._store = vector_store

    async def retrieve(
        self,
        query: str,
        limit: int = 5,
        category: str | None = None,
        score_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant clinical knowledge for a query.

        Falls back to built-in knowledge if vector store is unavailable or
        returns insufficient results.
        """
        results: list[dict[str, Any]] = []

        # Try vector store first
        if self._store:
            filters = {"category": category} if category else None
            try:
                results = await self._store.search(
                    query=query,
                    limit=limit,
                    filters=filters,
                    score_threshold=score_threshold,
                )
            except Exception as e:
                logger.warning("rag.vector_search_failed: %s", e)

        # Fall back to built-in knowledge if insufficient results
        if len(results) < limit:
            builtin = self._search_builtin(query, category, limit - len(results))
            results.extend(builtin)

        return results[:limit]

    async def retrieve_for_conditions(
        self, conditions: list[str], limit: int = 3
    ) -> list[dict[str, Any]]:
        """Retrieve clinical guidelines relevant to patient conditions."""
        all_results: list[dict[str, Any]] = []
        for condition in conditions[:5]:  # Cap at 5 conditions
            results = await self.retrieve(
                query=f"{condition} management guidelines",
                limit=limit,
                category="clinical_guidelines",
            )
            all_results.extend(results)
        return all_results

    async def retrieve_drug_info(
        self, medications: list[str], limit: int = 3
    ) -> list[dict[str, Any]]:
        """Retrieve drug interaction and safety information."""
        query = f"drug interactions: {', '.join(medications[:5])}"
        return await self.retrieve(
            query=query,
            limit=limit,
            category="drug_reference",
        )

    async def seed_builtin_knowledge(self) -> int:
        """Seed the vector store with built-in clinical knowledge."""
        if not self._store:
            return 0

        documents = [
            {"text": item["text"], "metadata": {"category": item["category"], "title": item["title"], "source": "builtin"}}
            for item in BUILTIN_KNOWLEDGE
        ]

        return await self._store.ingest_documents(documents)

    def _search_builtin(
        self,
        query: str,
        category: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Simple keyword-based search over built-in knowledge."""
        query_lower = query.lower()
        scored: list[tuple[float, dict[str, Any]]] = []

        for item in BUILTIN_KNOWLEDGE:
            if category and item["category"] != category:
                continue

            # Simple relevance scoring based on keyword overlap
            text_lower = item["text"].lower()
            title_lower = item["title"].lower()
            query_words = set(query_lower.split())
            text_words = set(text_lower.split())

            overlap = len(query_words & text_words)
            title_bonus = 0.3 if any(w in title_lower for w in query_words) else 0.0
            score = (overlap / max(len(query_words), 1)) + title_bonus

            if score > 0.1:
                scored.append((
                    score,
                    {
                        "text": item["text"],
                        "score": round(min(score, 1.0), 3),
                        "source": "builtin",
                        "category": item["category"],
                        "title": item["title"],
                        "metadata": {"category": item["category"], "title": item["title"]},
                    },
                ))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in scored[:limit]]
