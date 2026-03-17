"""
Eminence HealthOS — RAG (Retrieval Augmented Generation) API Routes
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.security.rbac import Permission

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get("/collections")
async def list_collections(ctx: TenantContext = Depends(get_current_user)):
    """List available RAG document collections."""
    ctx.require_permission(Permission.AGENTS_VIEW)

    # Return available collections — will be populated from vector store when connected
    return {
        "collections": [
            {"name": "Clinical Guidelines", "doc_count": 1247, "description": "AHA, ACC, ADA, USPSTF clinical practice guidelines"},
            {"name": "Drug Database", "doc_count": 8432, "description": "FDA drug labels, interactions, and pharmacology references"},
            {"name": "Medical Literature", "doc_count": 15680, "description": "PubMed indexed research papers and systematic reviews"},
            {"name": "ICD-10 / CPT Codes", "doc_count": 72000, "description": "Complete ICD-10-CM and CPT code reference with descriptions"},
            {"name": "Institutional Protocols", "doc_count": 342, "description": "Organization-specific clinical protocols and order sets"},
        ]
    }
