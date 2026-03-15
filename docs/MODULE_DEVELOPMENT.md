# Eminence HealthOS -- Module Development Guide

This guide walks through creating a new module for the HealthOS platform end-to-end, from backend directory layout through frontend integration and database migrations. All examples reference real patterns from existing modules (telehealth, operations, etc.) so you can follow the established conventions.

---

## Table of Contents

1. [Module Directory Structure](#1-module-directory-structure)
2. [Creating a New Module from Scratch](#2-creating-a-new-module-from-scratch)
3. [Router Setup](#3-router-setup)
4. [Mounting in main.py](#4-mounting-in-mainpy)
5. [Schema Definitions](#5-schema-definitions)
6. [Service Layer Patterns](#6-service-layer-patterns)
7. [Event Publishing](#7-event-publishing)
8. [Adding Frontend API Functions](#8-adding-frontend-api-functions)
9. [Creating the Frontend Page](#9-creating-the-frontend-page)
10. [Adding to Sidebar Navigation](#10-adding-to-sidebar-navigation)
11. [Database Migrations](#11-database-migrations)
12. [Testing Checklist](#12-testing-checklist)

---

## 1. Module Directory Structure

Every module lives under `modules/<module_name>/` and follows this standard layout:

```
modules/
  your_module/
    __init__.py            # Package marker (can be empty)
    routes.py              # FastAPI APIRouter with all HTTP endpoints
    events.py              # Event publisher for Kafka event bus
    agents/                # AI agent implementations
      __init__.py
      agent_one.py
      agent_two.py
    schemas/               # Pydantic request/response models
      __init__.py
      models.py
    services/              # Business logic and external integrations
      __init__.py
      core_service.py
```

This mirrors what the telehealth module uses:

```
modules/telehealth/
    __init__.py
    routes.py
    events.py
    agents/
        __init__.py
        session_manager.py
        symptom_checker.py
        visit_preparation.py
        clinical_note.py
        follow_up_plan.py
        medication_review.py
        scheduling.py
        ...
    schemas/
        __init__.py
        session.py
    services/
        __init__.py
        session_service.py
        video_service.py
```

---

## 2. Creating a New Module from Scratch

Follow these steps to scaffold a new module. We will use a hypothetical `care_coordination` module as the running example.

### Step 1: Create the directory tree

```bash
mkdir -p modules/care_coordination/{agents,schemas,services}
touch modules/care_coordination/__init__.py
touch modules/care_coordination/routes.py
touch modules/care_coordination/events.py
touch modules/care_coordination/agents/__init__.py
touch modules/care_coordination/schemas/__init__.py
touch modules/care_coordination/services/__init__.py
```

### Step 2: Build out each file

Work through the sections below in order: schemas first, then services, events, routes, and finally mount in main.py.

---

## 3. Router Setup

The router is the entry point for all HTTP traffic into your module. Create an `APIRouter` with a prefix that matches your module name, and a tags list for Swagger grouping.

**File: `modules/care_coordination/routes.py`**

```python
"""
Eminence HealthOS -- Care Coordination API Routes
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.agents.types import AgentInput
from healthos_platform.api.middleware.tenant import TenantContext, get_current_user
from healthos_platform.config.database import get_db as get_shared_db
from healthos_platform.security.rbac import Permission

from modules.care_coordination.schemas.referral import (
    ReferralCreate,
    ReferralResponse,
)
from modules.care_coordination.events import CareCoordinationEventPublisher

logger = logging.getLogger("healthos.care_coordination.routes")

router = APIRouter(prefix="/care-coordination", tags=["care-coordination"])

_event_publisher = CareCoordinationEventPublisher()


@router.post("/referrals", response_model=ReferralResponse)
async def create_referral(
    body: ReferralCreate,
    ctx: TenantContext = Depends(get_current_user),
):
    """Create a new care coordination referral."""
    from modules.care_coordination.agents.referral_agent import ReferralAgent

    ctx.require_permission(Permission.CARE_PLANS_WRITE)

    agent = ReferralAgent()
    agent_input = AgentInput(
        org_id=ctx.org_id,
        patient_id=body.patient_id,
        trigger="care_coordination.referral.create",
        context={
            "action": "create",
            "referral_type": body.referral_type,
            "reason": body.reason,
            "priority": body.priority,
        },
    )

    output = await agent.run(agent_input)
    result = output.result

    await _event_publisher.referral_created(
        referral_id=result.get("referral_id", ""),
        patient_id=str(body.patient_id),
        tenant_id=ctx.org_id or "default",
        data={"referral_type": body.referral_type},
    )

    return ReferralResponse(**result)
```

Key conventions to note:

- **Prefix**: The `APIRouter(prefix="/care-coordination", ...)` sets the URL namespace. Combined with the `/api/v1` prefix added in `main.py`, the full path becomes `/api/v1/care-coordination/referrals`.
- **Lazy agent imports**: Agents are imported inside route functions (not at module level) to avoid circular imports and keep startup fast. This is the pattern used throughout the telehealth and operations modules.
- **Permission checks**: Call `ctx.require_permission(Permission.SOME_PERMISSION)` before executing business logic.
- **Event publishing**: Emit a domain event after successful state changes.

### Authentication patterns

The codebase uses two authentication styles depending on the module:

**Style A** -- `TenantContext` (used by telehealth):

```python
from healthos_platform.api.middleware.tenant import TenantContext, get_current_user

@router.post("/endpoint")
async def my_endpoint(
    body: MySchema,
    ctx: TenantContext = Depends(get_current_user),
):
    ctx.require_permission(Permission.ENCOUNTERS_WRITE)
    # ctx.org_id, ctx.user_id available
```

**Style B** -- `require_auth` / `require_role` (used by operations):

```python
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

@router.post("/endpoint")
async def my_endpoint(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    ...

# For admin-only endpoints:
@router.post("/admin-endpoint")
async def admin_endpoint(
    body: dict[str, Any],
    user: CurrentUser = Depends(require_role("admin")),
):
    ...
```

Choose whichever style is consistent with the module group you are extending. Style A is preferred for new modules.

---

## 4. Mounting in main.py

Once your router is ready, register it in `services/api/main.py` inside the `create_app()` function.

Open `services/api/main.py` and add your import and `include_router` call in the `Module Routes` section:

```python
# In the "Module Routes" section of create_app():

from modules.care_coordination.routes import router as care_coordination_router

app.include_router(care_coordination_router, prefix="/api/v1", tags=["Care Coordination"])
```

This is exactly how every existing module is mounted. For reference, here is how the telehealth and operations modules are registered:

```python
from modules.telehealth.routes import router as telehealth_router
from modules.operations.routes import router as operations_router

app.include_router(telehealth_router, prefix="/api/v1", tags=["Telehealth"])
app.include_router(operations_router, prefix="/api/v1", tags=["Operations"])
```

The `prefix="/api/v1"` is combined with the router's own prefix. So if your router has `prefix="/care-coordination"`, the final URL path is `/api/v1/care-coordination/...`.

---

## 5. Schema Definitions

Schemas are Pydantic `BaseModel` classes that define request and response shapes. Place them in `modules/<module>/schemas/`.

**File: `modules/care_coordination/schemas/referral.py`**

```python
"""Care coordination referral schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReferralCreate(BaseModel):
    patient_id: UUID
    referral_type: str = Field(
        "specialist",
        description="specialist, diagnostic, therapy, social_services",
    )
    reason: str
    priority: str = Field("routine", description="routine, urgent, emergent")
    referring_provider_id: Optional[UUID] = None
    notes: Optional[str] = None


class ReferralResponse(BaseModel):
    referral_id: str
    patient_id: str
    referral_type: str
    status: str
    priority: str
    created_at: str
```

For reference, here is the actual session schema from the telehealth module (`modules/telehealth/schemas/session.py`):

```python
class SessionCreate(BaseModel):
    patient_id: UUID
    visit_type: str = Field("follow_up", description="follow_up, new_patient, urgent, wellness")
    urgency: str = Field("routine", description="routine, same_day, urgent, emergency")
    chief_complaint: Optional[str] = None
    symptoms: list[str] = []


class SessionResponse(BaseModel):
    session_id: str
    patient_id: str
    visit_type: str
    urgency: str
    status: str
    estimated_wait_minutes: int
    created_at: str
```

Guidelines:

- Use `UUID` for ID fields on request models (Pydantic handles serialization).
- Use `str` for ID fields on response models (avoids JSON serialization issues).
- Use `Field(default, description=...)` to document allowed values.
- Group related schemas in a single file (e.g., all referral-related models in `referral.py`).

---

## 6. Service Layer Patterns

Services encapsulate business logic, database access, caching, and external integrations. They live in `modules/<module>/services/`.

**File: `modules/care_coordination/services/referral_service.py`**

```python
"""Care coordination referral service layer."""

import json
import logging
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.care_coordination.events import CareCoordinationEventPublisher

logger = logging.getLogger("healthos.care_coordination.referral_service")


class ReferralService:
    """Business logic for care coordination referrals."""

    def __init__(
        self,
        redis=None,
        db: Optional[AsyncSession] = None,
        event_publisher: Optional[CareCoordinationEventPublisher] = None,
    ):
        self._redis = redis
        self._db = db
        self._events = event_publisher or CareCoordinationEventPublisher()

    async def create_referral(self, data: dict) -> dict:
        """Create and persist a new referral."""
        if self._db:
            # DB persistence
            ...
        elif self._redis:
            # Redis cache
            await self._redis.set(
                f"care_coord:referral:{data['referral_id']}",
                json.dumps(data, default=str),
                ex=7200,
            )
        return data

    async def get_referral(self, referral_id: str) -> Optional[dict]:
        """Retrieve a referral (Redis -> DB fallback)."""
        if self._redis:
            cached = await self._redis.get(f"care_coord:referral:{referral_id}")
            if cached:
                return json.loads(cached)
        if self._db:
            # Query DB
            ...
        return None
```

This follows the same three-tier pattern used by `TelehealthSessionService`:

1. **DB persistence** -- primary storage via SQLAlchemy async sessions.
2. **Redis cache** -- warm cache for frequently accessed data with TTL expiry.
3. **In-memory fallback** -- a `dict` for development/testing when neither DB nor Redis is available.

Services are instantiated by routes or agents as needed. They accept optional `db`, `redis`, and `event_publisher` dependencies to remain testable.

---

## 7. Event Publishing

Every module should publish domain events to the Kafka event bus for cross-module communication and audit trails. Events use the `HealthOSEvent` envelope from `shared/events/bus.py`.

**File: `modules/care_coordination/events.py`**

```python
"""Care coordination event publisher."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from shared.events.bus import EventProducer, HealthOSEvent

logger = logging.getLogger("healthos.care_coordination.events")

CARE_COORDINATION_TOPIC = "care_coordination.events"


class CareCoordinationEventType:
    REFERRAL_CREATED = "care_coordination.referral.created"
    REFERRAL_ACCEPTED = "care_coordination.referral.accepted"
    REFERRAL_COMPLETED = "care_coordination.referral.completed"
    TRANSITION_INITIATED = "care_coordination.transition.initiated"


class CareCoordinationEventPublisher:
    """Publishes care coordination events to the Kafka event bus."""

    def __init__(self, producer: Optional[EventProducer] = None) -> None:
        self._producer = producer

    def _build_event(
        self,
        event_type: str,
        *,
        referral_id: str = "",
        patient_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        tenant_id: str = "default",
        data: Optional[dict[str, Any]] = None,
    ) -> HealthOSEvent:
        return HealthOSEvent(
            event_type=event_type,
            payload={
                "referral_id": referral_id,
                "data": data or {},
            },
            event_id=str(uuid4()),
            tenant_id=tenant_id,
            patient_id=patient_id,
            source="care_coordination",
            timestamp=datetime.now(timezone.utc).isoformat(),
            trace_id=trace_id or str(uuid4()),
        )

    async def _publish(self, event: HealthOSEvent) -> None:
        """Publish with graceful fallback."""
        if self._producer is None:
            logger.warning(
                "Kafka producer not available -- logging event locally: [%s] %s",
                event.event_type,
                event.event_id,
            )
            return
        try:
            await self._producer.publish(CARE_COORDINATION_TOPIC, event)
        except Exception:
            logger.warning(
                "Failed to publish event %s (%s) -- continuing without Kafka",
                event.event_id,
                event.event_type,
                exc_info=True,
            )

    async def referral_created(
        self,
        referral_id: str,
        patient_id: str,
        *,
        tenant_id: str = "default",
        trace_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        event = self._build_event(
            CareCoordinationEventType.REFERRAL_CREATED,
            referral_id=referral_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            data=data,
        )
        await self._publish(event)
```

Key patterns from the telehealth module's `events.py`:

- **Graceful degradation**: When `_producer is None` or `publish` raises, the event is logged but never blocks the request.
- **Event type constants**: Define a class with string constants for each event type (e.g., `TelehealthEventType.SESSION_CREATED`).
- **Standard envelope**: Every event uses the `HealthOSEvent` dataclass which includes `event_type`, `payload`, `event_id`, `tenant_id`, `patient_id`, `source`, `timestamp`, and `trace_id`.
- **One topic per module**: Use a single topic like `"telehealth.events"` or `"care_coordination.events"`.
- **One public method per event type**: Each event has its own async method (e.g., `session_created()`, `note_generated()`).

---

## 8. Adding Frontend API Functions

All frontend API calls go through `frontend/src/lib/api.ts`, which provides a typed `request<T>()` helper that handles authentication, error handling, and base URL prefixing.

Add your module's API functions at the end of the file, grouped under a comment header:

```typescript
// -- Care Coordination -------------------------------------------------------

export async function createCareReferral(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/care-coordination/referrals", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchReferralStatus(referralId: string) {
  return request<Record<string, unknown>>(`/care-coordination/referrals/${referralId}`);
}

export async function listCareTransitions(patientId: string) {
  return request<Record<string, unknown>[]>(`/care-coordination/transitions/${patientId}`);
}
```

For modules with well-defined response shapes, define TypeScript interfaces like the telehealth module does:

```typescript
export interface CareReferral {
  referral_id: string;
  patient_id: string;
  referral_type: string;
  status: string;
  priority: string;
  created_at: string;
}

export async function createCareReferral(body: Record<string, unknown>) {
  return request<CareReferral>("/care-coordination/referrals", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
```

The `request<T>()` helper automatically:
- Prepends `/api/v1` to all paths
- Attaches the `Authorization: Bearer <token>` header from localStorage
- Redirects to `/login` on 401 responses
- Throws on non-OK responses

---

## 9. Creating the Frontend Page

Frontend pages use the Next.js App Router. Create a directory under `frontend/src/app/` matching your module's sidebar href.

**File: `frontend/src/app/care-coordination/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import { createCareReferral } from "@/lib/api";

export default function CareCoordinationPage() {
  const [creating, setCreating] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await createCareReferral({
        patient_id: "...",
        referral_type: "specialist",
        reason: "Cardiology consultation",
        priority: "routine",
      });
    } catch {
      // Handle error
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Care Coordination</h1>
        <button
          onClick={() => {/* open modal */}}
          className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700"
        >
          New Referral
        </button>
      </div>

      {/* Module-specific content */}
    </div>
  );
}
```

This follows the same pattern as `frontend/src/app/telehealth/page.tsx`:
- `"use client"` directive at the top (required for hooks and interactivity)
- Import API functions from `@/lib/api`
- Use `useState` for local UI state
- Follow the HealthOS Tailwind design system (`healthos-600`, `text-gray-900`, etc.)

For complex modules, extract sub-components into `frontend/src/components/<module>/`:

```
frontend/src/components/care-coordination/
    ReferralList.tsx
    ReferralDetail.tsx
    TransitionTimeline.tsx
```

---

## 10. Adding to Sidebar Navigation

The sidebar is defined in `frontend/src/components/layout/Sidebar.tsx`. Add your module to the appropriate section in the `NAV_SECTIONS` array.

Find the section that fits your module (Overview, Clinical, Operations, or Advanced) and add an entry:

```typescript
const NAV_SECTIONS = [
  // ...existing sections...
  {
    label: "Operations",
    items: [
      { href: "/operations", label: "Operations", icon: "clipboard" },
      { href: "/rcm", label: "Revenue Cycle", icon: "dollar" },
      { href: "/analytics", label: "Analytics", icon: "chart" },
      { href: "/compliance", label: "Compliance", icon: "shield" },
      // Add your new module:
      { href: "/care-coordination", label: "Care Coord", icon: "handshake" },
    ],
  },
  // ...
];
```

Available icon keys are defined in the `NavIcon` component in the same file: `grid`, `users`, `bell`, `video`, `clipboard`, `chart`, `mic`, `dollar`, `twin`, `shield`, `heart`, `pill`, `flask`, `scan`, `handshake`, `dna`, `activity`, `portal`, `cpu`, `storefront`.

If you need a custom icon, add a new SVG entry to the `icons` record inside the `NavIcon` component.

---

## 11. Database Migrations

HealthOS uses Alembic with async SQLAlchemy for database migrations. Migration files live in `migrations/versions/`.

### Step 1: Create a new migration file

Follow the sequential numbering convention (`001_`, `002_`, etc.):

**File: `migrations/versions/008_care_coordination_models.py`**

```python
"""Add care_coordination_referrals and care_transitions tables.

Revision ID: 008_care_coordination_models
Revises: 007_analytics_models
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "008_care_coordination_models"
down_revision = "007_analytics_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "care_coordination_referrals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("referral_id", sa.String(100), nullable=False, unique=True),
        sa.Column("patient_id", UUID(as_uuid=True),
                  sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("referring_provider_id", UUID(as_uuid=True),
                  sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("referral_type", sa.String(30), server_default="specialist"),
        sa.Column("priority", sa.String(20), server_default="routine"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )
    op.create_index("ix_care_referrals_referral_id",
                    "care_coordination_referrals", ["referral_id"], unique=True)
    op.create_index("ix_care_referrals_tenant_status",
                    "care_coordination_referrals", ["tenant_id", "status"])
    op.create_index("ix_care_referrals_patient",
                    "care_coordination_referrals", ["patient_id"])


def downgrade() -> None:
    op.drop_table("care_coordination_referrals")
```

### Step 2: Register models in env.py

If your module defines SQLAlchemy ORM models, import them in `migrations/env.py` so Alembic can detect them for autogenerate:

```python
# In migrations/env.py, add to the imports:
from shared.models import (
    tenant, patient, provider, encounter, observation,
    condition, medication, agent, alert, audit, consent, care_plan,
)
# Add your model:
from shared.models import care_coordination  # noqa: F401
```

### Step 3: Run the migration

```bash
alembic upgrade head
```

Migration conventions (from the existing `004_telehealth_models.py`):

- Always include `tenant_id` as `sa.String(100), nullable=False` for multi-tenancy.
- Use `UUID(as_uuid=True)` with `server_default=sa.text("gen_random_uuid()")` for primary keys.
- Use `sa.DateTime(timezone=True)` with `server_default=sa.func.now()` for timestamps.
- Use `JSONB` for flexible structured data (symptoms, metadata, action items, etc.).
- Create indexes on foreign keys, status fields, and any columns used for filtering.
- Always implement both `upgrade()` and `downgrade()`.
- Set `down_revision` to the previous migration's revision ID.

---

## 12. Testing Checklist

Before submitting your module, verify every layer:

### Backend

- [ ] **Routes load without import errors**: `python -c "from modules.your_module.routes import router"`
- [ ] **Router is mounted**: Verify your module appears in `/docs` (Swagger UI) at the correct prefix
- [ ] **Schema validation**: POST invalid data and confirm Pydantic returns 422 with clear error messages
- [ ] **Authentication enforced**: Confirm 401 is returned when no token is provided
- [ ] **Permission checks**: Confirm 403 when the user lacks the required permission
- [ ] **Agent invocation**: Confirm routes correctly instantiate and call the agent with proper `AgentInput`
- [ ] **Event publishing**: Verify events are published (check logs for "logging event locally" in dev mode)
- [ ] **Error handling**: Confirm `HTTPException(404)` is raised for missing resources
- [ ] **Database operations**: If using DB, confirm CRUD operations work with `get_shared_db`

### Frontend

- [ ] **API functions**: Confirm API functions in `api.ts` match backend route paths
- [ ] **Page renders**: Navigate to your module's page and confirm it loads without errors
- [ ] **Sidebar link**: Confirm the sidebar entry is present and highlights when active
- [ ] **API integration**: Confirm the page successfully calls backend endpoints

### Database

- [ ] **Migration runs forward**: `alembic upgrade head` succeeds
- [ ] **Migration rolls back**: `alembic downgrade -1` succeeds
- [ ] **Indexes created**: Confirm indexes exist on frequently queried columns
- [ ] **Multi-tenancy**: Confirm `tenant_id` column exists on all new tables

### Events

- [ ] **Event envelope**: Events include `event_type`, `event_id`, `tenant_id`, `source`, `timestamp`
- [ ] **Graceful fallback**: Module works when Kafka is unavailable (events are logged, not lost)
- [ ] **Event naming**: Event types follow the `module.entity.action` convention (e.g., `care_coordination.referral.created`)

### Integration

- [ ] **No circular imports**: The module starts cleanly with lazy agent imports in routes
- [ ] **Logging**: Module logger is namespaced under `healthos.<module>` (e.g., `healthos.care_coordination.routes`)
- [ ] **Consistent style**: Code follows existing patterns from telehealth/operations modules
