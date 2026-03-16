from pydantic import BaseModel
from typing import Dict, Optional, Any

class GraphState(BaseModel):
    vitals_event_id: int
    device_id: Optional[str] = None
    effective_time: Optional[str] = None
    readings: Dict[str, Any] = {}
    patient_id: Optional[str] = None
    recommendation: Dict | None = None

