MEDICAL_TEST_MAP = {

    # 🧪 Cholesterol
    "total cholesterol": "cholesterol_total",
    "cholesterol total": "cholesterol_total",
    "ldl cholesterol": "cholesterol_ldl",
    "ldl": "cholesterol_ldl",
    "hdl cholesterol": "cholesterol_hdl",
    "hdl": "cholesterol_hdl",
    "triglycerides": "triglycerides",

    # 🍬 Glucose
    "fasting blood glucose": "glucose_fasting",
    "blood sugar fasting": "glucose_fasting",
    "fasting glucose": "glucose_fasting",
    "fbs": "glucose_fasting",
    "glucose fasting": "glucose_fasting",
    "glucose": "glucose_random",

    # 🩸 Diabetes
    "hba1c": "hba1c",
    "a1c": "hba1c",

    # 🧬 Blood
    "hemoglobin": "hemoglobin",
    "hb": "hemoglobin",
    "wbc": "wbc",
    "white blood cell": "wbc",
    "rbc": "rbc",
    "red blood cell": "rbc",
    "platelet": "platelets",

    # 🧪 Kidney
    "creatinine": "creatinine",
    "urea": "urea",
}

def normalize_test_name(name):
    name = name.lower().strip()

    for key in sorted(MEDICAL_TEST_MAP, key=len, reverse=True):
        if key in name:
            return MEDICAL_TEST_MAP[key]

        print(f"[SKIPPED] {name}")  # 🔥 ADD THIS
    return None


import re


MEDICAL_TEST_MAP = {
    **MEDICAL_TEST_MAP,
    "serum cholesterol": "cholesterol_total",
    "ldl-c": "cholesterol_ldl",
    "hdl-c": "cholesterol_hdl",
    "fasting plasma glucose": "glucose_fasting",
    "random glucose": "glucose_random",
    "hb a1c": "hba1c",
    "haemoglobin": "hemoglobin",
    "white blood cells": "wbc",
    "red blood cells": "rbc",
    "platelets": "platelets",
    "serum creatinine": "creatinine",
    "blood urea": "urea",
    "bun": "urea",
}


def _clean_name(name: str) -> str:
    cleaned = re.sub(r"[_:/]+", " ", name.lower())
    cleaned = re.sub(r"[^a-z0-9\s\-\+\(\)%\.]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -:")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "unknown_parameter"


def normalize_test_name(name):
    """
    Normalize a raw parameter name.

    Known tests map to canonical identifiers. Unknown tests are preserved
    as a safe slug instead of being dropped, which keeps the pipeline dynamic.
    """

    cleaned_name = _clean_name(name)

    if not cleaned_name:
        return "unknown_parameter"

    if cleaned_name in MEDICAL_TEST_MAP:
        return MEDICAL_TEST_MAP[cleaned_name]

    for key in sorted(MEDICAL_TEST_MAP, key=len, reverse=True):
        if key in cleaned_name:
            return MEDICAL_TEST_MAP[key]

    return _slugify(cleaned_name)
