MEDICAL_RULES = {
    "cholesterol_total": {
        "normal": "< 200",
        "borderline": "200 - 239",
        "high": ">= 240",
        "risk": "Increases risk of heart disease"
    },
    "cholesterol_ldl": {
        "normal": "< 100",
        "high": ">= 160",
        "risk": "High LDL contributes to artery blockage"
    },
    "cholesterol_hdl": {
        "low": "< 40",
        "risk": "Low HDL reduces protection against heart disease"
    },
    "triglycerides": {
        "normal": "< 150",
        "high": ">= 200",
        "risk": "High triglycerides increase cardiovascular risk"
    },
    "glucose_fasting": {
        "normal": "70 - 100",
        "prediabetes": "100 - 125",
        "diabetes": ">= 126",
        "risk": "High blood sugar can indicate diabetes risk"
    },
    "hba1c": {
        "normal": "< 5.7",
        "prediabetes": "5.7 - 6.4",
        "diabetes": ">= 6.5",
        "risk": "Indicates long-term blood sugar control"
    },
    "hemoglobin": {
        "low": "< 13",
        "risk": "Low hemoglobin may indicate anemia"
    }
}



def apply_medical_rules(records):
    """
    Applies medical rules to extracted lab records
    and classifies them as normal / abnormal with risk context.
    """
    results = []

    for record in records:
        rule = MEDICAL_RULES.get(record.test_name)

        if not rule:
            continue

        status = "unknown"

        value = record.value

        # Rule evaluation (simple numeric thresholds)
        if "normal" in rule and "<" in rule["normal"]:
            threshold = float(rule["normal"].replace("<", "").strip())
            if value < threshold:
                status = "normal"

        if "borderline" in rule:
            low, high = rule["borderline"].split("-")
            if float(low) <= value <= float(high):
                status = "borderline"

        if "high" in rule and ">=" in rule["high"]:
            threshold = float(rule["high"].replace(">=", "").strip())
            if value >= threshold:
                status = "high"

        if "low" in rule and "<" in rule["low"]:
            threshold = float(rule["low"].replace("<", "").strip())
            if value < threshold:
                status = "low"

        results.append({
            "parameter": record.test_name,   # canonical ID
            "test_name": record.test_name,
            "value": record.value,
            "unit": record.unit,
            "status": status,
            "risk": rule.get("risk", ""),
            "date": record.report_date
        })


    return results


import re


MEDICAL_RULES = {
    **MEDICAL_RULES,
    "cholesterol_hdl": {
        "normal": ">= 40",
        "low": "< 40",
        "risk": "Low HDL reduces cardiovascular protection against heart disease",
    },
    "hemoglobin": {
        "normal": ">= 13",
        "low": "< 13",
        "risk": "Low hemoglobin may indicate anemia",
    },
}


def _parse_numeric_values(text: str):
    return [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", text or "")]


def _evaluate_condition(value: float, expression: str):
    expression = (expression or "").strip()
    if not expression:
        return False

    if "-" in expression or "–" in expression:
        numbers = _parse_numeric_values(expression.replace("–", "-"))
        if len(numbers) >= 2:
            low, high = numbers[0], numbers[1]
            return low <= value <= high

    if expression.startswith(">="):
        numbers = _parse_numeric_values(expression)
        return bool(numbers) and value >= numbers[0]
    if expression.startswith("<="):
        numbers = _parse_numeric_values(expression)
        return bool(numbers) and value <= numbers[0]
    if expression.startswith(">"):
        numbers = _parse_numeric_values(expression)
        return bool(numbers) and value > numbers[0]
    if expression.startswith("<"):
        numbers = _parse_numeric_values(expression)
        return bool(numbers) and value < numbers[0]

    return False


def classify_by_rule(test_name: str, value: float):
    rule = MEDICAL_RULES.get(test_name)
    if not rule:
        return "unknown", ""

    for label in ("critical", "diabetes", "prediabetes", "high", "borderline", "low", "normal"):
        if label in rule and _evaluate_condition(value, rule[label]):
            return label, rule.get("risk", "")

    return "unknown", rule.get("risk", "")


def classify_by_reference_range(value: float, reference_range: str):
    text = (reference_range or "").strip()
    if not text:
        return "unknown"

    normalized = text.replace("–", "-")
    numbers = _parse_numeric_values(normalized)

    if "-" in normalized and len(numbers) >= 2:
        low, high = numbers[0], numbers[1]
        if value < low:
            return "low"
        if value > high:
            return "high"
        return "normal"

    if normalized.startswith(">=") and numbers:
        return "normal" if value >= numbers[0] else "low"
    if normalized.startswith(">") and numbers:
        return "normal" if value > numbers[0] else "low"
    if normalized.startswith("<=") and numbers:
        return "normal" if value <= numbers[0] else "high"
    if normalized.startswith("<") and numbers:
        return "normal" if value < numbers[0] else "high"

    return "unknown"


def apply_medical_rules(records):
    """
    Classify extracted medical records.

    Uses hardcoded clinical rules when available, otherwise falls back to the
    reference range printed inside the uploaded report.
    """

    results = []

    for record in records:
        status, risk = classify_by_rule(record.test_name, record.value)
        if status == "unknown":
            status = classify_by_reference_range(record.value, record.reference_range)

        results.append({
            "parameter": record.test_name,
            "test_name": record.test_name,
            "value": record.value,
            "unit": record.unit,
            "status": status,
            "risk": risk,
            "reference_range": record.reference_range,
            "date": record.report_date,
        })

    return results

