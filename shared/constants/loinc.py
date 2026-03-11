"""LOINC code constants used across the platform."""

# Vital Signs
SYSTOLIC_BP = "8480-6"
DIASTOLIC_BP = "8462-4"
HEART_RATE = "8867-4"
RESPIRATORY_RATE = "9279-1"
BODY_TEMPERATURE = "8310-5"
SPO2 = "2708-6"
BMI = "39156-5"
BODY_WEIGHT = "29463-7"
BODY_HEIGHT = "8302-2"
BP_PANEL = "55284-4"

# Common Labs
GLUCOSE = "2345-7"
CREATININE = "2160-0"
BUN = "3094-0"
SODIUM = "2951-2"
POTASSIUM = "2823-3"
HBA1C = "4548-4"
HEMOGLOBIN = "718-7"
MCV = "787-2"
WBC = "6690-2"
PLATELETS = "777-3"
TOTAL_CHOLESTEROL = "2093-3"
LDL = "13457-7"
HDL = "2085-9"
TRIGLYCERIDES = "2571-8"
ALT = "1742-6"
AST = "1920-8"
TSH = "3016-3"
EGFR = "33914-3"

# Categories
VITAL_SIGNS_CODES = [
    SYSTOLIC_BP, DIASTOLIC_BP, HEART_RATE, RESPIRATORY_RATE,
    BODY_TEMPERATURE, SPO2, BMI, BODY_WEIGHT, BODY_HEIGHT,
]

LAB_CODES = [
    GLUCOSE, CREATININE, BUN, SODIUM, POTASSIUM, HBA1C,
    HEMOGLOBIN, MCV, WBC, PLATELETS, TOTAL_CHOLESTEROL,
    LDL, HDL, TRIGLYCERIDES, ALT, AST, TSH, EGFR,
]

DISPLAY_NAMES = {
    SYSTOLIC_BP: "Systolic Blood Pressure",
    DIASTOLIC_BP: "Diastolic Blood Pressure",
    HEART_RATE: "Heart Rate",
    RESPIRATORY_RATE: "Respiratory Rate",
    BODY_TEMPERATURE: "Body Temperature",
    SPO2: "Oxygen Saturation",
    BMI: "BMI",
    BODY_WEIGHT: "Body Weight",
    BODY_HEIGHT: "Body Height",
    GLUCOSE: "Glucose",
    CREATININE: "Creatinine",
    BUN: "Blood Urea Nitrogen",
    SODIUM: "Sodium",
    POTASSIUM: "Potassium",
    HBA1C: "Hemoglobin A1c",
    HEMOGLOBIN: "Hemoglobin",
    WBC: "White Blood Cell Count",
    PLATELETS: "Platelet Count",
    TOTAL_CHOLESTEROL: "Total Cholesterol",
    LDL: "LDL Cholesterol",
    HDL: "HDL Cholesterol",
}
