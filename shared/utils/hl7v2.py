"""
HL7 v2.x message parser and builder utilities.

Supports parsing pipe-delimited HL7 v2 messages and building common message
types (ADT^A01, ORU^R01, ACK) for interoperability with legacy health systems.

Standard HL7 v2 delimiters:
    |  field separator
    ^  component separator
    ~  repetition separator
    \\  escape character
    &  sub-component separator
"""

from datetime import datetime
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FIELD_SEP = "|"
COMPONENT_SEP = "^"
REPEAT_SEP = "~"
ESCAPE_CHAR = "\\"
SUB_COMPONENT_SEP = "&"
ENCODING_CHARS = f"{COMPONENT_SEP}{REPEAT_SEP}{ESCAPE_CHAR}{SUB_COMPONENT_SEP}"

SEGMENT_TERMINATOR = "\r"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hl7_timestamp(dt: Optional[datetime] = None) -> str:
    """Format a datetime as an HL7 v2 timestamp (YYYYMMDDHHmmss)."""
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime("%Y%m%d%H%M%S")


def _hl7_date(value) -> str:
    """Format a date or datetime as YYYYMMDD."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y%m%d")
    if hasattr(value, "strftime"):
        return value.strftime("%Y%m%d")
    # Assume ISO string — strip dashes
    return str(value).replace("-", "")[:8]


def _split_components(field_value: str) -> list[str]:
    """Split a field value into components using ^."""
    return field_value.split(COMPONENT_SEP)


def _split_repeats(field_value: str) -> list[str]:
    """Split a field value into repetitions using ~."""
    return field_value.split(REPEAT_SEP)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_hl7_message(raw_message: str) -> dict:
    """
    Parse an HL7 v2 pipe-delimited message into a structured dict.

    Handles the following segments: MSH, PID, OBX, OBR, PV1, DG1.
    Segments that appear multiple times (OBX, OBR, DG1) are collected
    into lists.

    Returns a dict with:
        - "raw": original message string
        - "segments": ordered list of (segment_id, field_list)
        - Segment-specific parsed keys (see _parse_* helpers)
    """
    raw_message = raw_message.strip()
    # Normalise line endings — HL7 uses \r but files may have \n or \r\n
    lines = raw_message.replace("\r\n", "\r").replace("\n", "\r").split("\r")
    lines = [ln for ln in lines if ln.strip()]

    result: dict[str, Any] = {
        "raw": raw_message,
        "segments": [],
    }

    # Collect repeating segments
    obx_list: list[dict] = []
    obr_list: list[dict] = []
    dg1_list: list[dict] = []

    for line in lines:
        if not line:
            continue

        segment_id = line[:3]

        # MSH is special: field separator is the 4th character
        if segment_id == "MSH":
            fields = _parse_msh_fields(line)
        else:
            fields = line.split(FIELD_SEP)

        result["segments"].append((segment_id, fields))

        if segment_id == "MSH":
            result["MSH"] = _parse_msh(fields)
        elif segment_id == "PID":
            result["PID"] = _parse_pid(fields)
        elif segment_id == "PV1":
            result["PV1"] = _parse_pv1(fields)
        elif segment_id == "OBR":
            obr_list.append(_parse_obr(fields))
        elif segment_id == "OBX":
            obx_list.append(_parse_obx(fields))
        elif segment_id == "DG1":
            dg1_list.append(_parse_dg1(fields))

    if obx_list:
        result["OBX"] = obx_list
    if obr_list:
        result["OBR"] = obr_list
    if dg1_list:
        result["DG1"] = dg1_list

    return result


def _parse_msh_fields(line: str) -> list[str]:
    """
    Parse MSH segment fields.

    MSH is unique: MSH-1 is the field separator character itself (|),
    and MSH-2 is the encoding characters (^~\\&).
    We return a list where index 0 = "MSH", index 1 = "|", and so on.
    """
    # Field separator is char at index 3
    sep = line[3]
    rest = line[4:]  # everything after "MSH|"
    parts = rest.split(sep)
    # Reconstruct: MSH, |, <encoding chars>, ...
    return ["MSH", sep] + parts


def _safe_get(fields: list[str], index: int, default: str = "") -> str:
    """Safely get a field by index."""
    if index < len(fields):
        return fields[index]
    return default


def _parse_msh(fields: list[str]) -> dict:
    """Parse MSH segment into a dict."""
    return {
        "field_separator": _safe_get(fields, 1, "|"),
        "encoding_characters": _safe_get(fields, 2),
        "sending_application": _safe_get(fields, 3),
        "sending_facility": _safe_get(fields, 4),
        "receiving_application": _safe_get(fields, 5),
        "receiving_facility": _safe_get(fields, 6),
        "datetime": _safe_get(fields, 7),
        "security": _safe_get(fields, 8),
        "message_type": _safe_get(fields, 9),
        "message_control_id": _safe_get(fields, 10),
        "processing_id": _safe_get(fields, 11),
        "version_id": _safe_get(fields, 12),
    }


def _parse_pid(fields: list[str]) -> dict:
    """Parse PID (Patient Identification) segment."""
    # PID-3: Patient Identifier List
    patient_id = _safe_get(fields, 3)
    # PID-5: Patient Name (family^given^middle^suffix^prefix)
    name_field = _safe_get(fields, 5)
    name_components = _split_components(name_field)
    # PID-7: Date of Birth
    dob = _safe_get(fields, 7)
    # PID-8: Sex
    sex = _safe_get(fields, 8)
    # PID-11: Address
    address_field = _safe_get(fields, 11)
    addr_components = _split_components(address_field)
    # PID-13: Phone
    phone = _safe_get(fields, 13)

    return {
        "set_id": _safe_get(fields, 1),
        "patient_id": patient_id,
        "patient_id_external": _safe_get(fields, 2),
        "patient_name": {
            "family": name_components[0] if name_components else "",
            "given": name_components[1] if len(name_components) > 1 else "",
            "middle": name_components[2] if len(name_components) > 2 else "",
            "suffix": name_components[3] if len(name_components) > 3 else "",
            "prefix": name_components[4] if len(name_components) > 4 else "",
        },
        "date_of_birth": dob,
        "sex": sex,
        "race": _safe_get(fields, 10),
        "address": {
            "street": addr_components[0] if addr_components else "",
            "other": addr_components[1] if len(addr_components) > 1 else "",
            "city": addr_components[2] if len(addr_components) > 2 else "",
            "state": addr_components[3] if len(addr_components) > 3 else "",
            "zip": addr_components[4] if len(addr_components) > 4 else "",
            "country": addr_components[5] if len(addr_components) > 5 else "",
        },
        "phone": phone,
        "ssn": _safe_get(fields, 19),
    }


def _parse_pv1(fields: list[str]) -> dict:
    """Parse PV1 (Patient Visit) segment."""
    return {
        "set_id": _safe_get(fields, 1),
        "patient_class": _safe_get(fields, 2),
        "assigned_location": _safe_get(fields, 3),
        "admission_type": _safe_get(fields, 4),
        "attending_doctor": _safe_get(fields, 7),
        "referring_doctor": _safe_get(fields, 8),
        "hospital_service": _safe_get(fields, 10),
        "readmission_indicator": _safe_get(fields, 13),
        "discharge_disposition": _safe_get(fields, 36),
        "admit_datetime": _safe_get(fields, 44),
        "discharge_datetime": _safe_get(fields, 45),
        "visit_number": _safe_get(fields, 19),
    }


def _parse_obr(fields: list[str]) -> dict:
    """Parse OBR (Observation Request) segment."""
    # OBR-4: Universal Service Identifier
    service_id = _safe_get(fields, 4)
    service_components = _split_components(service_id)
    return {
        "set_id": _safe_get(fields, 1),
        "placer_order_number": _safe_get(fields, 2),
        "filler_order_number": _safe_get(fields, 3),
        "universal_service_id": {
            "code": service_components[0] if service_components else "",
            "display": service_components[1] if len(service_components) > 1 else "",
            "coding_system": service_components[2] if len(service_components) > 2 else "",
        },
        "observation_datetime": _safe_get(fields, 7),
        "result_status": _safe_get(fields, 25),
    }


def _parse_obx(fields: list[str]) -> dict:
    """Parse OBX (Observation/Result) segment."""
    # OBX-3: Observation Identifier
    obs_id = _safe_get(fields, 3)
    obs_components = _split_components(obs_id)
    # OBX-6: Units
    units_field = _safe_get(fields, 6)
    units_components = _split_components(units_field)

    return {
        "set_id": _safe_get(fields, 1),
        "value_type": _safe_get(fields, 2),
        "observation_id": {
            "code": obs_components[0] if obs_components else "",
            "display": obs_components[1] if len(obs_components) > 1 else "",
            "coding_system": obs_components[2] if len(obs_components) > 2 else "",
        },
        "observation_sub_id": _safe_get(fields, 4),
        "value": _safe_get(fields, 5),
        "units": {
            "code": units_components[0] if units_components else "",
            "display": units_components[1] if len(units_components) > 1 else "",
            "coding_system": units_components[2] if len(units_components) > 2 else "",
        },
        "reference_range": _safe_get(fields, 7),
        "abnormal_flags": _safe_get(fields, 8),
        "observation_result_status": _safe_get(fields, 11),
        "effective_datetime": _safe_get(fields, 14),
    }


def _parse_dg1(fields: list[str]) -> dict:
    """Parse DG1 (Diagnosis) segment."""
    # DG1-3: Diagnosis Code
    diag_code = _safe_get(fields, 3)
    diag_components = _split_components(diag_code)

    return {
        "set_id": _safe_get(fields, 1),
        "coding_method": _safe_get(fields, 2),
        "diagnosis_code": {
            "code": diag_components[0] if diag_components else "",
            "display": diag_components[1] if len(diag_components) > 1 else "",
            "coding_system": diag_components[2] if len(diag_components) > 2 else "",
        },
        "diagnosis_description": _safe_get(fields, 4),
        "diagnosis_datetime": _safe_get(fields, 5),
        "diagnosis_type": _safe_get(fields, 6),
    }


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _build_segment(segment_id: str, fields: list[str]) -> str:
    """Build a single HL7 segment from a list of field values."""
    return FIELD_SEP.join([segment_id] + fields)


def _build_msh(
    message_type: str,
    message_control_id: str,
    sending_app: str = "HealthOS",
    sending_facility: str = "HealthOS",
    receiving_app: str = "",
    receiving_facility: str = "",
    timestamp: Optional[datetime] = None,
    version: str = "2.5.1",
) -> str:
    """Build an MSH segment."""
    ts = _hl7_timestamp(timestamp)
    # MSH-1 is the field separator itself, embedded in the segment header
    # MSH|^~\\&|sending_app|sending_facility|receiving_app|receiving_facility|datetime||message_type|control_id|P|version
    return FIELD_SEP.join([
        "MSH",
        ENCODING_CHARS,      # MSH-2: Encoding characters
        sending_app,          # MSH-3
        sending_facility,     # MSH-4
        receiving_app,        # MSH-5
        receiving_facility,   # MSH-6
        ts,                   # MSH-7
        "",                   # MSH-8: Security
        message_type,         # MSH-9: Message Type
        message_control_id,   # MSH-10: Message Control ID
        "P",                  # MSH-11: Processing ID (P = Production)
        version,              # MSH-12: Version ID
    ])


def _build_evn(event_type: str, timestamp: Optional[datetime] = None) -> str:
    """Build an EVN (Event Type) segment."""
    ts = _hl7_timestamp(timestamp)
    return _build_segment("EVN", [
        event_type,  # EVN-1
        ts,          # EVN-2: Recorded datetime
    ])


def _build_pid(patient_data: dict) -> str:
    """Build a PID segment from patient data dict."""
    patient_id = patient_data.get("patient_id", "")
    mrn = patient_data.get("mrn", patient_id)
    last_name = patient_data.get("last_name", "")
    first_name = patient_data.get("first_name", "")
    middle_name = patient_data.get("middle_name", "")
    dob = _hl7_date(patient_data.get("date_of_birth"))
    sex = patient_data.get("sex", "U")
    # Map FHIR gender to HL7 v2 sex
    sex_map = {"male": "M", "female": "F", "other": "O", "unknown": "U"}
    sex = sex_map.get(sex.lower(), sex.upper()) if sex else "U"

    # Address
    street = patient_data.get("address_line1", "")
    city = patient_data.get("city", "")
    state = patient_data.get("state", "")
    postal_code = patient_data.get("postal_code", "")
    country = patient_data.get("country", "US")
    address = COMPONENT_SEP.join([street, "", city, state, postal_code, country])

    phone = patient_data.get("phone", "")
    ssn = patient_data.get("ssn", "")

    # Patient name: family^given^middle
    patient_name = COMPONENT_SEP.join([last_name, first_name, middle_name])

    return _build_segment("PID", [
        "1",               # PID-1: Set ID
        "",                # PID-2: External ID (deprecated)
        mrn,               # PID-3: Patient Identifier List
        "",                # PID-4: Alternate Patient ID
        patient_name,      # PID-5: Patient Name
        "",                # PID-6: Mother's Maiden Name
        dob,               # PID-7: Date/Time of Birth
        sex,               # PID-8: Administrative Sex
        "",                # PID-9: Patient Alias
        "",                # PID-10: Race
        address,           # PID-11: Patient Address
        "",                # PID-12: County Code
        phone,             # PID-13: Phone Number - Home
        "",                # PID-14: Phone Number - Business
        "",                # PID-15: Primary Language
        "",                # PID-16: Marital Status
        "",                # PID-17: Religion
        "",                # PID-18: Patient Account Number
        ssn,               # PID-19: SSN
    ])


def _build_pv1(
    patient_class: str = "I",
    attending_doctor: str = "",
    admit_datetime: Optional[datetime] = None,
    visit_number: str = "",
) -> str:
    """Build a PV1 (Patient Visit) segment."""
    fields = [""] * 45  # PV1 can have up to 52 fields; we fill what we need
    fields[0] = "1"                          # PV1-1: Set ID
    fields[1] = patient_class                # PV1-2: Patient Class (I=inpatient, O=outpatient, E=emergency)
    fields[6] = attending_doctor             # PV1-7: Attending Doctor
    fields[18] = visit_number                # PV1-19: Visit Number
    if admit_datetime:
        fields[43] = _hl7_timestamp(admit_datetime)  # PV1-44: Admit Date/Time
    return _build_segment("PV1", fields)


def build_adt_a01(patient_data: dict) -> str:
    """
    Build an ADT^A01 (Admit/Visit Notification) HL7 v2 message.

    Expected patient_data keys:
        - patient_id / mrn
        - first_name, last_name
        - date_of_birth
        - sex
        - address_line1, city, state, postal_code, country (optional)
        - phone (optional)
        - attending_doctor (optional)
        - admit_datetime (optional, defaults to now)
        - message_control_id (optional)
        - visit_number (optional)
    """
    control_id = patient_data.get(
        "message_control_id",
        f"HEALTHOS-{_hl7_timestamp()}",
    )
    now = datetime.utcnow()
    admit_dt = patient_data.get("admit_datetime", now)

    segments = [
        _build_msh(
            message_type=f"ADT{COMPONENT_SEP}A01",
            message_control_id=control_id,
            sending_app=patient_data.get("sending_application", "HealthOS"),
            sending_facility=patient_data.get("sending_facility", "HealthOS"),
            receiving_app=patient_data.get("receiving_application", ""),
            receiving_facility=patient_data.get("receiving_facility", ""),
            timestamp=now,
        ),
        _build_evn("A01", now),
        _build_pid(patient_data),
        _build_pv1(
            patient_class=patient_data.get("patient_class", "I"),
            attending_doctor=patient_data.get("attending_doctor", ""),
            admit_datetime=admit_dt if isinstance(admit_dt, datetime) else None,
            visit_number=patient_data.get("visit_number", ""),
        ),
    ]

    return SEGMENT_TERMINATOR.join(segments) + SEGMENT_TERMINATOR


def build_oru_r01(observation_data: dict) -> str:
    """
    Build an ORU^R01 (Observation Result) HL7 v2 message.

    Expected observation_data keys:
        - patient_id / mrn
        - first_name, last_name
        - date_of_birth, sex (optional)
        - observations: list of dicts, each with:
            - code (e.g., LOINC code)
            - display (e.g., "Systolic Blood Pressure")
            - coding_system (e.g., "LN" for LOINC; optional, defaults to "LN")
            - value
            - value_type (optional, defaults to "NM")
            - units (optional)
            - units_code (optional)
            - reference_range (optional, e.g., "60-100")
            - abnormal_flags (optional, e.g., "H", "L", "N")
            - status (optional, defaults to "F" for final)
            - effective_datetime (optional)
        - order_code, order_display (optional, for OBR)
        - message_control_id (optional)
    """
    control_id = observation_data.get(
        "message_control_id",
        f"HEALTHOS-{_hl7_timestamp()}",
    )
    now = datetime.utcnow()

    segments = [
        _build_msh(
            message_type=f"ORU{COMPONENT_SEP}R01",
            message_control_id=control_id,
            sending_app=observation_data.get("sending_application", "HealthOS"),
            sending_facility=observation_data.get("sending_facility", "HealthOS"),
            receiving_app=observation_data.get("receiving_application", ""),
            receiving_facility=observation_data.get("receiving_facility", ""),
            timestamp=now,
        ),
        _build_pid(observation_data),
    ]

    # OBR (Observation Request)
    order_code = observation_data.get("order_code", "")
    order_display = observation_data.get("order_display", "")
    order_system = observation_data.get("order_coding_system", "LN")
    obr_service = COMPONENT_SEP.join([order_code, order_display, order_system])
    obr_ts = _hl7_timestamp(now)
    obr_fields = [""] * 26
    obr_fields[0] = "1"           # OBR-1: Set ID
    obr_fields[3] = obr_service   # OBR-4: Universal Service ID
    obr_fields[6] = obr_ts        # OBR-7: Observation datetime
    obr_fields[24] = "F"          # OBR-25: Result Status
    segments.append(_build_segment("OBR", obr_fields))

    # OBX segments
    observations = observation_data.get("observations", [])
    for i, obs in enumerate(observations, start=1):
        code = obs.get("code", "")
        display = obs.get("display", "")
        coding_system = obs.get("coding_system", "LN")
        obs_id = COMPONENT_SEP.join([code, display, coding_system])

        value_type = obs.get("value_type", "NM")
        value = str(obs.get("value", ""))

        units_code = obs.get("units_code", obs.get("units", ""))
        units_display = obs.get("units", units_code)
        units_system = obs.get("units_coding_system", "UCUM")
        units = COMPONENT_SEP.join([units_code, units_display, units_system]) if units_code else ""

        ref_range = obs.get("reference_range", "")
        abnormal = obs.get("abnormal_flags", "")
        status = obs.get("status", "F")

        eff_dt = obs.get("effective_datetime")
        eff_ts = _hl7_timestamp(eff_dt) if isinstance(eff_dt, datetime) else (eff_dt or "")

        obx_fields = [""] * 15
        obx_fields[0] = str(i)       # OBX-1: Set ID
        obx_fields[1] = value_type   # OBX-2: Value Type
        obx_fields[2] = obs_id       # OBX-3: Observation Identifier
        obx_fields[3] = ""           # OBX-4: Sub-ID
        obx_fields[4] = value        # OBX-5: Observation Value
        obx_fields[5] = units        # OBX-6: Units
        obx_fields[6] = ref_range    # OBX-7: Reference Range
        obx_fields[7] = abnormal     # OBX-8: Abnormal Flags
        obx_fields[10] = status      # OBX-11: Result Status
        obx_fields[13] = eff_ts      # OBX-14: Date/Time of Observation
        segments.append(_build_segment("OBX", obx_fields))

    return SEGMENT_TERMINATOR.join(segments) + SEGMENT_TERMINATOR


def build_ack(original_message_id: str, ack_code: str = "AA") -> str:
    """
    Build an ACK (Acknowledgement) HL7 v2 message.

    Args:
        original_message_id: The MSH-10 (Message Control ID) of the message
            being acknowledged.
        ack_code: Acknowledgement code — one of:
            AA = Application Accept
            AE = Application Error
            AR = Application Reject

    Returns:
        A complete HL7 v2 ACK message string.
    """
    now = datetime.utcnow()
    control_id = f"ACK-{_hl7_timestamp(now)}"

    segments = [
        _build_msh(
            message_type=f"ACK{COMPONENT_SEP}",
            message_control_id=control_id,
            sending_app="HealthOS",
            sending_facility="HealthOS",
            timestamp=now,
        ),
        _build_segment("MSA", [
            ack_code,                # MSA-1: Acknowledgement Code
            original_message_id,     # MSA-2: Message Control ID (of original)
        ]),
    ]

    return SEGMENT_TERMINATOR.join(segments) + SEGMENT_TERMINATOR
