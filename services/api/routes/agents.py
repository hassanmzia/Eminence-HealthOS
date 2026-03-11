"""Agent observability endpoints — decisions, interactions, model cards."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.config.database import get_db
from services.api.middleware.auth import CurrentUser, require_auth
from services.api.middleware.tenant import get_tenant_id
from services.api.schemas.agent import (
    AgentDecisionResponse,
    AgentInteractionResponse,
    AgentStatusResponse,
)
from services.api.schemas.common import PaginatedResponse
from shared.models.agent import AgentDecision, AgentInteraction

logger = logging.getLogger("healthos.routes.agents")
router = APIRouter()


@router.get("/decisions", response_model=PaginatedResponse[AgentDecisionResponse])
async def list_decisions(
    agent_name: Optional[str] = Query(None),
    patient_id: Optional[UUID] = Query(None),
    trace_id: Optional[str] = Query(None),
    requires_hitl: Optional[bool] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    query = select(AgentDecision).where(AgentDecision.tenant_id == tenant_id)

    if agent_name:
        query = query.where(AgentDecision.agent_name == agent_name)
    if patient_id:
        query = query.where(AgentDecision.patient_id == str(patient_id))
    if trace_id:
        query = query.where(AgentDecision.trace_id == trace_id)
    if requires_hitl is not None:
        query = query.where(AgentDecision.requires_hitl == requires_hitl)

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    rows = await db.execute(
        query.order_by(AgentDecision.created_at.desc()).offset(offset).limit(limit)
    )
    decisions = rows.scalars().all()

    return PaginatedResponse(
        items=[AgentDecisionResponse.model_validate(d) for d in decisions],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/decisions/{decision_id}", response_model=AgentDecisionResponse)
async def get_decision(
    decision_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    result = await db.execute(
        select(AgentDecision).where(
            AgentDecision.id == str(decision_id),
            AgentDecision.tenant_id == tenant_id,
        )
    )
    decision = result.scalar_one_or_none()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return AgentDecisionResponse.model_validate(decision)


@router.get("/interactions", response_model=PaginatedResponse[AgentInteractionResponse])
async def list_interactions(
    trace_id: Optional[str] = Query(None),
    sender_agent: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    query = select(AgentInteraction).where(AgentInteraction.tenant_id == tenant_id)

    if trace_id:
        query = query.where(AgentInteraction.trace_id == trace_id)
    if sender_agent:
        query = query.where(AgentInteraction.sender_agent == sender_agent)

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    rows = await db.execute(
        query.order_by(AgentInteraction.created_at.desc()).offset(offset).limit(limit)
    )
    interactions = rows.scalars().all()

    return PaginatedResponse(
        items=[AgentInteractionResponse.model_validate(i) for i in interactions],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/status", response_model=list[AgentStatusResponse])
async def get_agent_statuses(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth),
):
    """Aggregate status for all agents that have produced decisions."""
    query = (
        select(
            AgentDecision.agent_name,
            AgentDecision.agent_tier,
            func.count().label("total_decisions"),
            func.avg(AgentDecision.confidence).label("avg_confidence"),
            func.avg(AgentDecision.duration_ms).label("avg_duration_ms"),
            func.max(AgentDecision.created_at).label("last_active"),
        )
        .where(AgentDecision.tenant_id == tenant_id)
        .group_by(AgentDecision.agent_name, AgentDecision.agent_tier)
        .order_by(AgentDecision.agent_tier, AgentDecision.agent_name)
    )

    rows = await db.execute(query)
    return [
        AgentStatusResponse(
            agent_name=row.agent_name,
            agent_tier=row.agent_tier,
            status="active",
            total_decisions=row.total_decisions,
            avg_confidence=round(float(row.avg_confidence or 0), 3),
            avg_duration_ms=round(float(row.avg_duration_ms or 0), 1),
            last_active=row.last_active,
        )
        for row in rows.all()
    ]


@router.get("/model-cards/{agent_name}")
async def get_model_card(
    agent_name: str,
    user: CurrentUser = Depends(require_auth),
):
    """Retrieve the model card for a specific agent."""
    try:
        from observability.model_cards.generator import ModelCardGenerator
        generator = ModelCardGenerator()
        card = generator.generate(agent_name)
        return card
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No model card for agent: {agent_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model card generation failed: {e}")
