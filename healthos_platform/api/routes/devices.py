"""
Eminence HealthOS — IoT Device API Routes (Phase 3)
Complete device authentication, data ingestion, and management.
Imported from InhealthUSA IoT API.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.database import get_db
from healthos_platform.api.middleware.tenant import (
    TenantContext,
    get_current_user,
    require_admin,
    require_clinical_staff,
)
from healthos_platform.models import (
    Device,
    DeviceActivityLog,
    DeviceAlertRule,
    DeviceAPIKey,
    DeviceDataReading,
    Vital,
)

router = APIRouter(prefix="/device", tags=["iot-devices"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS — with medical-range validation (ported from InhealthUSA serializers)
# ═══════════════════════════════════════════════════════════════════════════════


class DeviceAuthRequest(BaseModel):
    api_key: str


class DeviceAuthResponse(BaseModel):
    device_id: str
    device_name: str
    patient_id: str
    permissions: dict[str, bool]


class DeviceInfoResponse(BaseModel):
    id: uuid.UUID
    device_unique_id: str
    device_name: str
    device_type: str
    manufacturer: str | None
    model_number: str | None
    firmware_version: str | None
    status: str
    battery_level: int | None
    last_sync: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


class DeviceStatusUpdate(BaseModel):
    status: str | None = None
    battery_level: int | None = Field(None, ge=0, le=100)
    firmware_version: str | None = None


class VitalSignsData(BaseModel):
    """Vital signs submission with medical range validation."""
    timestamp: datetime
    blood_pressure_systolic: int | None = Field(None, ge=50, le=300)
    blood_pressure_diastolic: int | None = Field(None, ge=30, le=200)
    heart_rate: int | None = Field(None, ge=20, le=300)
    temperature: float | None = Field(None, ge=90.0, le=110.0)
    temperature_unit: str = "F"
    respiratory_rate: int | None = Field(None, ge=5, le=60)
    oxygen_saturation: float | None = Field(None, ge=50.0, le=100.0)
    weight: float | None = None
    weight_unit: str = "lbs"
    height_inches: float | None = None
    bmi: float | None = None
    glucose: float | None = Field(None, ge=0, le=600)
    signal_quality: int | None = Field(None, ge=0, le=100)

    @field_validator("blood_pressure_diastolic")
    @classmethod
    def bp_both_required(cls, v, info):
        sys = info.data.get("blood_pressure_systolic")
        if (v is not None and sys is None) or (v is None and sys is not None):
            raise ValueError("Both systolic and diastolic must be provided together")
        return v


class BulkVitalSignsRequest(BaseModel):
    readings: list[VitalSignsData] = Field(..., max_length=100)

    @field_validator("readings")
    @classmethod
    def chronological_order(cls, v):
        for i in range(1, len(v)):
            if v[i].timestamp < v[i - 1].timestamp:
                raise ValueError("Readings must be in chronological order")
        return v


class GlucoseData(BaseModel):
    timestamp: datetime
    glucose_level: float = Field(..., ge=0, le=600)
    meal_context: str | None = None  # fasting, pre_meal, post_meal, bedtime
    notes: str | None = None


class DeviceRegisterRequest(BaseModel):
    patient_id: uuid.UUID
    device_unique_id: str
    device_name: str
    device_type: str
    manufacturer: str | None = None
    model_number: str | None = None
    serial_number: str | None = None
    firmware_version: str | None = None


class DeviceAlertRuleCreate(BaseModel):
    device_id: uuid.UUID | None = None
    patient_id: uuid.UUID | None = None
    rule_name: str
    metric_name: str
    condition: str  # gt, lt, eq, gte, lte
    threshold_value: float
    alert_level: str = "warning"
    alert_message: str
    notify_patient: bool = False
    notify_provider: bool = True


class DeviceAlertRuleResponse(BaseModel):
    id: uuid.UUID
    rule_name: str
    metric_name: str
    condition: str
    threshold_value: float
    alert_level: str
    alert_message: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE AUTHENTICATION (API Key based)
# ═══════════════════════════════════════════════════════════════════════════════


async def _authenticate_device(api_key: str, db: AsyncSession) -> tuple[DeviceAPIKey, Device]:
    """Authenticate a device by API key prefix lookup + verification."""
    prefix = api_key[:8]
    result = await db.execute(
        select(DeviceAPIKey).where(DeviceAPIKey.key_prefix == prefix, DeviceAPIKey.is_active.is_(True))
    )
    key_obj = result.scalar_one_or_none()
    if not key_obj:
        raise HTTPException(401, "Invalid API key")

    # Check expiration
    if key_obj.expires_at and datetime.now(timezone.utc) > key_obj.expires_at:
        raise HTTPException(401, "API key expired")

    # Verify key hash
    hashed = hashlib.sha256(api_key.encode()).hexdigest()
    if hashed != key_obj.hashed_key:
        raise HTTPException(401, "Invalid API key")

    # Get device
    dev_result = await db.execute(select(Device).where(Device.id == key_obj.device_id))
    device = dev_result.scalar_one_or_none()
    if not device:
        raise HTTPException(404, "Device not found")

    # Record usage
    key_obj.last_used = datetime.now(timezone.utc)
    key_obj.request_count_today += 1

    return key_obj, device


@router.post("/auth", response_model=DeviceAuthResponse)
async def device_auth(
    body: DeviceAuthRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate an IoT device with an API key."""
    key_obj, device = await _authenticate_device(body.api_key, db)

    # Log activity
    log = DeviceActivityLog(
        device_id=device.id,
        api_key_id=key_obj.id,
        action_type="auth",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        endpoint="/api/v1/device/auth",
        http_method="POST",
        status_code=200,
    )
    db.add(log)

    return DeviceAuthResponse(
        device_id=str(device.device_unique_id),
        device_name=device.device_name,
        patient_id=str(device.patient_id),
        permissions={
            "can_write_vitals": key_obj.can_write_vitals,
            "can_read_patient": key_obj.can_read_patient,
        },
    )


@router.get("/info")
async def device_info(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Get device information."""
    _, device = await _authenticate_device(x_api_key, db)
    return DeviceInfoResponse.model_validate(device)


@router.put("/status")
async def update_device_status(
    body: DeviceStatusUpdate,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Update device status (battery, firmware, etc.)."""
    _, device = await _authenticate_device(x_api_key, db)
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(device, k, v)
    device.last_sync = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "updated"}


# ═══════════════════════════════════════════════════════════════════════════════
# VITAL SIGNS INGESTION
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/vitals")
async def submit_vitals(
    body: VitalSignsData,
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Submit a single vital signs reading from an IoT device."""
    key_obj, device = await _authenticate_device(x_api_key, db)
    if not key_obj.can_write_vitals:
        raise HTTPException(403, "API key does not have write_vitals permission")

    reading = DeviceDataReading(
        device_id=device.id,
        patient_id=device.patient_id,
        reading_type="vital_signs",
        timestamp=body.timestamp,
        data=body.model_dump(exclude_none=True, exclude={"timestamp", "signal_quality"}),
        signal_quality=body.signal_quality,
        battery_level=device.battery_level,
        device_firmware=device.firmware_version,
    )
    db.add(reading)

    # Also create a normalized Vital record
    vital_data = {}
    if body.blood_pressure_systolic is not None:
        vital_data["systolic"] = body.blood_pressure_systolic
        vital_data["diastolic"] = body.blood_pressure_diastolic
    if body.heart_rate is not None:
        vital_data["heart_rate"] = body.heart_rate
    if body.temperature is not None:
        vital_data["temperature"] = body.temperature
        vital_data["temperature_unit"] = body.temperature_unit
    if body.oxygen_saturation is not None:
        vital_data["oxygen_saturation"] = body.oxygen_saturation
    if body.respiratory_rate is not None:
        vital_data["respiratory_rate"] = body.respiratory_rate
    if body.glucose is not None:
        vital_data["glucose"] = body.glucose

    if vital_data:
        vital = Vital(
            patient_id=device.patient_id,
            org_id=device.org_id,
            device_id=device.device_unique_id,
            vital_type="composite",
            value=vital_data,
            unit="mixed",
            recorded_at=body.timestamp,
            source="iot_device",
            quality_score=body.signal_quality / 100.0 if body.signal_quality else None,
        )
        db.add(vital)

    # Log
    db.add(DeviceActivityLog(
        device_id=device.id,
        api_key_id=key_obj.id,
        action_type="data_post",
        ip_address=request.client.host if request.client else None,
        endpoint="/api/v1/device/vitals",
        http_method="POST",
        status_code=201,
    ))

    await db.flush()
    return {"status": "accepted", "reading_id": str(reading.id)}


@router.post("/vitals/bulk")
async def submit_vitals_bulk(
    body: BulkVitalSignsRequest,
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Bulk submit vital signs (up to 100 readings, chronological order)."""
    key_obj, device = await _authenticate_device(x_api_key, db)
    if not key_obj.can_write_vitals:
        raise HTTPException(403, "API key does not have write_vitals permission")

    reading_ids = []
    for reading_data in body.readings:
        reading = DeviceDataReading(
            device_id=device.id,
            patient_id=device.patient_id,
            reading_type="vital_signs",
            timestamp=reading_data.timestamp,
            data=reading_data.model_dump(exclude_none=True, exclude={"timestamp", "signal_quality"}),
            signal_quality=reading_data.signal_quality,
            battery_level=device.battery_level,
        )
        db.add(reading)
        await db.flush()
        reading_ids.append(str(reading.id))

    db.add(DeviceActivityLog(
        device_id=device.id,
        api_key_id=key_obj.id,
        action_type="data_post",
        ip_address=request.client.host if request.client else None,
        endpoint="/api/v1/device/vitals/bulk",
        http_method="POST",
        status_code=201,
        details={"count": len(body.readings)},
    ))

    return {"status": "accepted", "count": len(reading_ids), "reading_ids": reading_ids}


@router.post("/glucose")
async def submit_glucose(
    body: GlucoseData,
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Submit blood glucose reading."""
    key_obj, device = await _authenticate_device(x_api_key, db)
    if not key_obj.can_write_vitals:
        raise HTTPException(403, "API key does not have write_vitals permission")

    reading = DeviceDataReading(
        device_id=device.id,
        patient_id=device.patient_id,
        reading_type="glucose",
        timestamp=body.timestamp,
        data=body.model_dump(exclude_none=True, exclude={"timestamp"}),
    )
    db.add(reading)
    await db.flush()
    return {"status": "accepted", "reading_id": str(reading.id)}


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE MANAGEMENT (authenticated user endpoints)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/manage/list", response_model=list[DeviceInfoResponse])
async def list_devices(
    ctx: TenantContext = Depends(require_clinical_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all devices in the organization."""
    result = await db.execute(
        select(Device).where(Device.org_id == ctx.org_id).order_by(Device.created_at.desc())
    )
    return result.scalars().all()


@router.post("/manage/register", response_model=DeviceInfoResponse, status_code=201)
async def register_device(
    body: DeviceRegisterRequest,
    ctx: TenantContext = Depends(require_clinical_staff),
    db: AsyncSession = Depends(get_db),
):
    """Register a new IoT device."""
    device = Device(org_id=ctx.org_id, **body.model_dump())
    db.add(device)
    await db.flush()
    return device


@router.post("/manage/{device_id}/api-key")
async def create_device_api_key(
    device_id: uuid.UUID,
    key_name: str = "default",
    ctx: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new API key for a device. Returns the raw key ONCE."""
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.org_id == ctx.org_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(404, "Device not found")

    raw_key = secrets.token_urlsafe(32)
    prefix = raw_key[:8]
    hashed = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = DeviceAPIKey(
        device_id=device.id,
        key_name=key_name,
        key_prefix=prefix,
        hashed_key=hashed,
    )
    db.add(api_key)
    await db.flush()

    return {
        "api_key": raw_key,
        "key_prefix": prefix,
        "key_name": key_name,
        "message": "Save this key — it cannot be retrieved again.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ALERT RULES
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/alert-rules", response_model=list[DeviceAlertRuleResponse])
async def list_alert_rules(
    ctx: TenantContext = Depends(require_clinical_staff),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DeviceAlertRule).where(
            DeviceAlertRule.org_id == ctx.org_id, DeviceAlertRule.is_active.is_(True)
        )
    )
    return result.scalars().all()


@router.post("/alert-rules", response_model=DeviceAlertRuleResponse, status_code=201)
async def create_alert_rule(
    body: DeviceAlertRuleCreate,
    ctx: TenantContext = Depends(require_clinical_staff),
    db: AsyncSession = Depends(get_db),
):
    rule = DeviceAlertRule(org_id=ctx.org_id, **body.model_dump())
    db.add(rule)
    await db.flush()
    return rule
