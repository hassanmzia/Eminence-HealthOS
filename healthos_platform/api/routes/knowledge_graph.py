"""
Eminence HealthOS — Knowledge Graph API Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.security.rbac import Permission

router = APIRouter(prefix="/knowledge-graph", tags=["Knowledge Graph"])


@router.get("/stats")
async def get_stats(ctx: TenantContext = Depends(get_current_user)):
    """Get knowledge graph statistics."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    # Return graph stats — will be populated from Neo4j when connected
    return {
        "total_nodes": 12847,
        "total_edges": 48329,
        "node_types": {
            "Disease": 2841,
            "Drug": 4126,
            "Symptom": 3012,
            "Patient": 1956,
            "Gene": 912,
        },
        "edge_types": {
            "TREATED_BY": 12400,
            "HAS_SYMPTOM": 9800,
            "DIAGNOSED_WITH": 8700,
            "INTERACTS_WITH": 6200,
            "ASSOCIATED_GENE": 4100,
            "CONTRAINDICATED": 3200,
            "SIDE_EFFECT_OF": 3929,
        },
    }
