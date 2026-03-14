"""
Eminence HealthOS — HL7v2 EHR Connector

Implements ``BaseEHRConnector`` for legacy EHR systems that communicate via
HL7 v2.x messages over TCP/MLLP (Minimal Lower Layer Protocol).

Supports:
- ADT (Admission/Discharge/Transfer) messages for encounter sync
- ORU messages for observation/result sync
- MDM messages for clinical document sync
- Async TCP/MLLP transport layer
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from shared.utils.hl7v2 import (
    build_ack,
    build_adt_a01,
    build_oru_r01,
    parse_hl7_message,
)
from healthos_platform.interop.ehr.base_connector import (
    BaseEHRConnector,
    audit_sync,
    ehr_retry,
)
from healthos_platform.interop.ehr.mappers import (
    clinical_note_to_hl7_mdm,
    encounter_to_hl7_adt,
    fhir_encounter_to_internal,
    vital_to_hl7_oru,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# MLLP framing constants
# ---------------------------------------------------------------------------
MLLP_START_BLOCK = b"\x0b"   # VT (vertical tab)
MLLP_END_BLOCK = b"\x1c"     # FS (file separator)
MLLP_CARRIAGE_RETURN = b"\x0d"  # CR


class MLLPTransport:
    """
    Async TCP transport implementing the MLLP (Minimal Lower Layer Protocol)
    framing used by HL7v2 systems.

    MLLP frame format:
        <VT> message <FS><CR>
    """

    def __init__(self, host: str, port: int, timeout: float = 30.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        """Open a TCP connection to the remote HL7v2 endpoint."""
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=self.timeout,
        )
        logger.info("mllp.connected", host=self.host, port=self.port)

    async def disconnect(self) -> None:
        """Close the TCP connection."""
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None
        logger.info("mllp.disconnected", host=self.host, port=self.port)

    @property
    def is_connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def send_message(self, hl7_message: str) -> str:
        """
        Send an HL7v2 message over MLLP and wait for the ACK response.

        Args:
            hl7_message: The complete HL7v2 message string.

        Returns:
            The raw ACK message string from the remote system.

        Raises:
            ConnectionError: If not connected.
            TimeoutError: If the remote system does not respond in time.
        """
        if not self.is_connected:
            raise ConnectionError("MLLP transport is not connected")

        assert self._writer is not None
        assert self._reader is not None

        # Frame with MLLP envelope
        frame = MLLP_START_BLOCK + hl7_message.encode("utf-8") + MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN
        self._writer.write(frame)
        await self._writer.drain()

        logger.debug("mllp.sent", size=len(frame))

        # Read response (also MLLP-framed)
        response = await asyncio.wait_for(
            self._read_mllp_frame(),
            timeout=self.timeout,
        )
        logger.debug("mllp.received", size=len(response))
        return response

    async def _read_mllp_frame(self) -> str:
        """Read a single MLLP-framed message from the stream."""
        assert self._reader is not None

        # Read until we see the start block
        while True:
            byte = await self._reader.read(1)
            if not byte:
                raise ConnectionError("Connection closed while waiting for MLLP start block")
            if byte == MLLP_START_BLOCK:
                break

        # Read message body until end block
        buffer = bytearray()
        while True:
            byte = await self._reader.read(1)
            if not byte:
                raise ConnectionError("Connection closed while reading MLLP message")
            if byte == MLLP_END_BLOCK:
                # Consume trailing CR
                await self._reader.read(1)
                break
            buffer.extend(byte)

        return buffer.decode("utf-8")


class HL7v2Connector(BaseEHRConnector):
    """
    HL7v2 connector for legacy EHR systems using TCP/MLLP transport.

    Parameters
    ----------
    host:
        The hostname or IP of the HL7v2 listener.
    port:
        The TCP port of the HL7v2 listener.
    timeout:
        Socket timeout in seconds (default 30).
    sending_app:
        MSH-3 sending application name.
    sending_facility:
        MSH-4 sending facility name.
    receiving_app:
        MSH-5 receiving application name.
    receiving_facility:
        MSH-6 receiving facility name.
    """

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 30.0,
        sending_app: str = "HealthOS",
        sending_facility: str = "HealthOS",
        receiving_app: str = "",
        receiving_facility: str = "",
        connector_name: str = "hl7v2",
    ) -> None:
        super().__init__(connector_name=connector_name)
        self.host = host
        self.port = port
        self.sending_app = sending_app
        self.sending_facility = sending_facility
        self.receiving_app = receiving_app
        self.receiving_facility = receiving_facility

        self._transport = MLLPTransport(host, port, timeout)

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        await self._transport.connect()

    async def disconnect(self) -> None:
        await self._transport.disconnect()

    async def is_connected(self) -> bool:
        return self._transport.is_connected

    # ------------------------------------------------------------------
    # Encounter sync (ADT)
    # ------------------------------------------------------------------

    @audit_sync("sync_encounter")
    @ehr_retry()
    async def sync_encounter(self, encounter: Any, patient: Any = None) -> dict:
        """
        Push an internal Encounter to the remote system as an ADT message.

        Returns a dict with the ACK status and message control ID.
        """
        adt_message = encounter_to_hl7_adt(encounter, patient=patient)
        ack_raw = await self._transport.send_message(adt_message)
        return self._parse_ack(ack_raw)

    @audit_sync("fetch_encounters")
    @ehr_retry()
    async def fetch_encounters(
        self,
        patient_id: str,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> list[dict]:
        """
        HL7v2 does not natively support query-response for encounters.

        This sends a QBP^Q11 (Query By Parameter) message if the remote
        system supports it. Returns parsed ADT responses or an empty list.
        """
        # Build a simple QBP^Q11 query for patient encounters
        qbp_message = self._build_query_message(patient_id, date_range)
        try:
            response_raw = await self._transport.send_message(qbp_message)
            parsed = parse_hl7_message(response_raw)
            # Wrap the PV1 data in a list if present
            pv1 = parsed.get("PV1")
            if pv1:
                return [pv1]
            return []
        except Exception as exc:
            logger.warning(
                "hl7v2.fetch_encounters_unsupported",
                error=str(exc),
                detail="Remote system may not support QBP queries",
            )
            return []

    # ------------------------------------------------------------------
    # Patient sync (ADT)
    # ------------------------------------------------------------------

    @audit_sync("sync_patient")
    @ehr_retry()
    async def sync_patient(self, patient: Any) -> dict:
        """
        Push a patient registration as an ADT^A04 (pre-admit) message.
        """
        patient_data = self._patient_to_hl7_dict(patient)
        adt_message = build_adt_a01(patient_data)
        ack_raw = await self._transport.send_message(adt_message)
        return self._parse_ack(ack_raw)

    @audit_sync("fetch_patient")
    @ehr_retry()
    async def fetch_patient(self, patient_id: str) -> dict:
        """
        Fetch patient demographics via a QBP^Q22 query.

        Returns parsed PID data or an empty dict if unsupported.
        """
        qbp_message = self._build_patient_query(patient_id)
        try:
            response_raw = await self._transport.send_message(qbp_message)
            parsed = parse_hl7_message(response_raw)
            return parsed.get("PID", {})
        except Exception as exc:
            logger.warning(
                "hl7v2.fetch_patient_unsupported",
                error=str(exc),
            )
            return {}

    # ------------------------------------------------------------------
    # Clinical data push
    # ------------------------------------------------------------------

    @audit_sync("push_clinical_note")
    @ehr_retry()
    async def push_clinical_note(self, note: Any, patient: Any = None) -> str:
        """
        Push a clinical note as an MDM^T02 message.

        Returns the message control ID from the ACK.
        """
        mdm_message = clinical_note_to_hl7_mdm(note, patient=patient)
        ack_raw = await self._transport.send_message(mdm_message)
        ack = self._parse_ack(ack_raw)
        return ack.get("message_control_id", "")

    @audit_sync("push_observation")
    @ehr_retry()
    async def push_observation(self, observation: Any, patient: Any = None) -> str:
        """
        Push an observation/vital as an ORU^R01 message.

        Returns the message control ID from the ACK.
        """
        oru_message = vital_to_hl7_oru(observation, patient=patient)
        ack_raw = await self._transport.send_message(oru_message)
        ack = self._parse_ack(ack_raw)
        return ack.get("message_control_id", "")

    # ------------------------------------------------------------------
    # Message building helpers
    # ------------------------------------------------------------------

    def _patient_to_hl7_dict(self, patient: Any) -> dict[str, Any]:
        """Build the patient_data dict expected by the hl7v2 builder."""
        demographics = getattr(patient, "demographics", None)

        if demographics and isinstance(demographics, dict):
            name_str = demographics.get("name", "")
            parts = name_str.split(" ", 1)
            first_name = parts[0] if parts else ""
            last_name = parts[1] if len(parts) > 1 else first_name
            gender = demographics.get("gender", "unknown")
            dob = demographics.get("dob", "")
            contact = demographics.get("contact", {})
            phone = contact.get("phone", "")
        else:
            first_name = getattr(patient, "first_name", "")
            last_name = getattr(patient, "last_name", "")
            gender = getattr(patient, "sex", "unknown")
            dob_val = getattr(patient, "date_of_birth", None)
            dob = dob_val.isoformat() if dob_val else ""
            phone = getattr(patient, "phone", "") or ""

        return {
            "patient_id": str(getattr(patient, "id", "")),
            "mrn": getattr(patient, "mrn", "") or str(getattr(patient, "id", "")),
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": dob,
            "sex": gender,
            "phone": phone,
            "sending_application": self.sending_app,
            "sending_facility": self.sending_facility,
            "receiving_application": self.receiving_app,
            "receiving_facility": self.receiving_facility,
            "patient_class": "O",
            "message_control_id": f"HEALTHOS-{uuid.uuid4().hex[:12]}",
        }

    def _build_query_message(
        self,
        patient_id: str,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> str:
        """Build a QBP^Q11 query message for encounter lookup."""
        from shared.utils.hl7v2 import (
            COMPONENT_SEP,
            SEGMENT_TERMINATOR,
            _build_msh,
            _build_segment,
            _hl7_timestamp,
        )

        now = datetime.now(timezone.utc)
        control_id = f"HEALTHOS-{uuid.uuid4().hex[:12]}"

        segments = [
            _build_msh(
                message_type=f"QBP{COMPONENT_SEP}Q11",
                message_control_id=control_id,
                sending_app=self.sending_app,
                sending_facility=self.sending_facility,
                receiving_app=self.receiving_app,
                receiving_facility=self.receiving_facility,
                timestamp=now,
            ),
        ]

        # QPD — Query Parameter Definition
        qpd_fields = [
            f"IHE PCD-01{COMPONENT_SEP}Query Encounters",
            control_id,
            patient_id,
        ]
        if date_range:
            start, end = date_range
            qpd_fields.append(f"{_hl7_timestamp(start)}-{_hl7_timestamp(end)}")
        segments.append(_build_segment("QPD", qpd_fields))

        # RCP — Response Control Parameters
        segments.append(_build_segment("RCP", ["I", "50"]))

        return SEGMENT_TERMINATOR.join(segments) + SEGMENT_TERMINATOR

    def _build_patient_query(self, patient_id: str) -> str:
        """Build a QBP^Q22 query for patient demographics."""
        from shared.utils.hl7v2 import (
            COMPONENT_SEP,
            SEGMENT_TERMINATOR,
            _build_msh,
            _build_segment,
        )

        now = datetime.now(timezone.utc)
        control_id = f"HEALTHOS-{uuid.uuid4().hex[:12]}"

        segments = [
            _build_msh(
                message_type=f"QBP{COMPONENT_SEP}Q22",
                message_control_id=control_id,
                sending_app=self.sending_app,
                sending_facility=self.sending_facility,
                receiving_app=self.receiving_app,
                receiving_facility=self.receiving_facility,
                timestamp=now,
            ),
            _build_segment("QPD", [
                f"IHE PDQ{COMPONENT_SEP}Query Patient",
                control_id,
                f"@PID.3.1{COMPONENT_SEP}{patient_id}",
            ]),
            _build_segment("RCP", ["I", "1"]),
        ]

        return SEGMENT_TERMINATOR.join(segments) + SEGMENT_TERMINATOR

    @staticmethod
    def _parse_ack(ack_raw: str) -> dict[str, Any]:
        """Parse an ACK message and return structured status info."""
        parsed = parse_hl7_message(ack_raw)
        msh = parsed.get("MSH", {})

        # Look for MSA segment
        msa: dict[str, str] = {}
        for seg_id, fields in parsed.get("segments", []):
            if seg_id == "MSA" and len(fields) > 2:
                msa = {
                    "ack_code": fields[1] if len(fields) > 1 else "",
                    "message_control_id": fields[2] if len(fields) > 2 else "",
                    "text_message": fields[3] if len(fields) > 3 else "",
                }
                break

        ack_code = msa.get("ack_code", "AE")
        return {
            "ack_code": ack_code,
            "accepted": ack_code == "AA",
            "message_control_id": msa.get("message_control_id", ""),
            "text_message": msa.get("text_message", ""),
            "raw": ack_raw,
        }
