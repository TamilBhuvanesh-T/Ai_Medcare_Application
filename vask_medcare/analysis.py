import re
from collections import defaultdict

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

try:
    from pdf2image import convert_from_path
except ImportError:  # pragma: no cover
    convert_from_path = None

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None

from PyPDF2 import PdfReader

from .ai import ask_llm_json


KNOWN_PARAMETERS = {
    "glucose": {"aliases": ["glucose", "fasting glucose", "blood sugar"], "unit": "mg/dL", "range": "70-100"},
    "hba1c": {"aliases": ["hba1c", "hb a1c", "glycated hemoglobin"], "unit": "%", "range": "<5.7"},
    "creatinine": {"aliases": ["creatinine", "serum creatinine"], "unit": "mg/dL", "range": "0.7-1.3"},
    "cholesterol_total": {"aliases": ["total cholesterol", "cholesterol total", "cholesterol"], "unit": "mg/dL", "range": "<200"},
    "ldl": {"aliases": ["ldl", "ldl cholesterol"], "unit": "mg/dL", "range": "<100"},
    "hdl": {"aliases": ["hdl", "hdl cholesterol"], "unit": "mg/dL", "range": ">40"},
    "triglycerides": {"aliases": ["triglycerides"], "unit": "mg/dL", "range": "<150"},
    "hemoglobin": {"aliases": ["hemoglobin", "haemoglobin", "hb"], "unit": "g/dL", "range": "13-17"},
}


def extract_report_text(pdf_path: str) -> dict:
    pdf_text = extract_pdf_text(pdf_path)
    ocr_text = extract_ocr_text(pdf_path)
    combined = merge_text_layers(pdf_text, ocr_text)
    return {"pdf_text": pdf_text, "ocr_text": ocr_text, "combined_text": combined}


def extract_pdf_text(pdf_path: str) -> str:
    chunks = []
    if pdfplumber:
        with pdfplumber.open(pdf_path) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    chunks.append(f"PDF Page {index}\n{text}")
    else:
        reader = PdfReader(pdf_path)
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(f"PDF Page {index}\n{text}")
    return "\n\n".join(chunks).strip()


def extract_ocr_text(pdf_path: str) -> str:
    if not (convert_from_path and pytesseract):
        return ""
    try:
        images = convert_from_path(pdf_path)
    except Exception:
        return ""

    text_parts = []
    for index, image in enumerate(images, start=1):
        try:
            page_text = pytesseract.image_to_string(image, config="--oem 3 --psm 6")
        except Exception:
            page_text = ""
        if page_text.strip():
            text_parts.append(f"OCR Page {index}\n{page_text}")
    return "\n\n".join(text_parts).strip()


def merge_text_layers(pdf_text: str, ocr_text: str) -> str:
    sections = []
    if pdf_text:
        sections.append(pdf_text)
    if ocr_text:
        sections.append(ocr_text)
    if not sections:
        return ""

    seen = set()
    merged_lines = []
    for line in "\n".join(sections).splitlines():
        cleaned = " ".join(line.split())
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        merged_lines.append(cleaned)
    return "\n".join(merged_lines)


def extract_parameters(text: str) -> list[dict]:
    parameters = []
    lines = text.splitlines()
    for canonical, meta in KNOWN_PARAMETERS.items():
        for line in lines:
            lowered = line.lower()
            if not any(alias in lowered for alias in meta["aliases"]):
                continue
            match = re.search(r"(-?\d+(?:\.\d+)?)", line)
            if not match:
                continue
            value = float(match.group(1))
            parameters.append(
                {
                    "name": canonical,
                    "label": canonical.replace("_", " ").title(),
                    "value": value,
                    "unit": meta["unit"],
                    "reference_range": meta["range"],
                    "status": classify_parameter(canonical, value),
                    "line": line.strip(),
                }
            )
            break
    return parameters


def classify_parameter(name: str, value: float) -> str:
    if name == "glucose":
        return "High" if value >= 126 else "Borderline" if value >= 100 else "Normal"
    if name == "hba1c":
        return "High" if value >= 6.5 else "Borderline" if value >= 5.7 else "Normal"
    if name == "creatinine":
        return "High" if value > 1.3 else "Normal"
    if name == "cholesterol_total":
        return "High" if value >= 240 else "Borderline" if value >= 200 else "Normal"
    if name == "ldl":
        return "High" if value >= 160 else "Borderline" if value >= 100 else "Normal"
    if name == "hdl":
        return "Low" if value < 40 else "Normal"
    if name == "triglycerides":
        return "High" if value >= 200 else "Borderline" if value >= 150 else "Normal"
    if name == "hemoglobin":
        return "Low" if value < 13 else "Normal"
    return "Normal"


def compute_risk(parameters: list[dict]) -> dict:
    score = 20
    drivers = []
    for param in parameters:
        status = param["status"]
        if status == "High":
            score += 18
            drivers.append(f"{param['label']} elevated")
        elif status == "Borderline":
            score += 10
            drivers.append(f"{param['label']} borderline")
        elif status == "Low":
            score += 12
            drivers.append(f"{param['label']} low")

    score = max(5, min(score, 95))
    if score >= 70:
        level, flag = "High", "High attention required"
    elif score >= 40:
        level, flag = "Moderate", "Close monitoring advised"
    else:
        level, flag = "Low", "Stable with routine monitoring"
    return {"risk_score": score, "risk_level": level, "flag": flag, "main_drivers": drivers[:4]}


def build_trends(current_report_id: int, current_uploaded_at: str, current_parameters: list[dict], prior_reports: list[dict]) -> dict:
    grouped = defaultdict(lambda: {"dates": [], "values": [], "status": []})
    historical_reports = prior_reports + [
        {"id": current_report_id, "uploaded_at": current_uploaded_at, "parameters": current_parameters}
    ]
    for report in historical_reports:
        date_label = report["uploaded_at"][:10]
        for param in report["parameters"]:
            bucket = grouped[param["name"]]
            bucket["dates"].append(date_label)
            bucket["values"].append(param["value"])
            bucket["status"].append(param["status"])
    return dict(grouped)


def suggest_department(parameters: list[dict], risk_level: str, latest_emotion: str | None = None) -> str:
    names = {p["name"] for p in parameters if p["status"] != "Normal"}
    if latest_emotion in {"Distressed", "Overwhelmed"}:
        return "Mental Health"
    if {"cholesterol_total", "ldl", "triglycerides"} & names:
        return "Cardiology"
    if {"glucose", "hba1c"} & names:
        return "Endocrinology"
    if "creatinine" in names:
        return "Nephrology"
    if risk_level == "High":
        return "General Medicine"
    return "General Medicine"


def build_recommendations(parameters: list[dict], risk: dict, emotion: str | None = None) -> list[str]:
    prompt = f"""
You are generating safe health-support recommendations.
Use the patient findings to suggest 4 short, practical activities.
Do not diagnose. Keep each item under 16 words.

Risk: {risk['risk_level']} ({risk['risk_score']}/100)
Emotion: {emotion or 'Unknown'}
Parameters: {parameters}

Return JSON with this shape:
{{"recommendations": ["...", "..."]}}
"""
    result = ask_llm_json(prompt)
    recommendations = result.get("recommendations") if isinstance(result, dict) else None
    if recommendations:
        return [item for item in recommendations if isinstance(item, str)][:4]

    fallback = []
    abnormal = [p for p in parameters if p["status"] != "Normal"]
    if any(p["name"] in {"glucose", "hba1c"} for p in abnormal):
        fallback.append("Take a daily walk and monitor sugar-friendly meals")
    if any(p["name"] in {"cholesterol_total", "ldl", "triglycerides"} for p in abnormal):
        fallback.append("Choose lower saturated fat meals and follow up on lipid checks")
    if any(p["name"] == "creatinine" for p in abnormal):
        fallback.append("Stay hydrated and discuss kidney markers with your doctor")
    if emotion in {"Distressed", "Anxious", "Overwhelmed"}:
        fallback.append("Schedule quiet breathing breaks and seek support if worry rises")
    fallback.append("Keep a copy of this report for your next clinical review")
    return fallback[:4]


def generate_summary(combined_text: str, parameters: list[dict], risk: dict, recommendations: list[str]) -> dict:
    prompt = f"""
You are a validated healthcare explainer.
Summarize the report findings in plain language.
Do not diagnose. Mention patterns, risks, and follow-up focus.
Keep it clear, calm, and patient-safe.

Parameters: {parameters}
Risk: {risk}
Recommendations: {recommendations}
Report text:
{combined_text[:5000]}

Return JSON:
{{
  "summary": "...",
  "narrative": "...",
  "voice_text": "..."
}}
"""
    data = ask_llm_json(prompt)
    if isinstance(data, dict) and data.get("summary"):
        return {
            "summary": data.get("summary", ""),
            "narrative": data.get("narrative", data.get("summary", "")),
            "voice_text": data.get("voice_text", data.get("summary", "")),
        }

    abnormal = [p for p in parameters if p["status"] != "Normal"]
    if abnormal:
        findings = ", ".join(
            f"{p['label']} is {p['status'].lower()} at {p['value']} {p['unit']}" for p in abnormal[:4]
        )
        summary = f"The report shows {findings}. Overall risk is {risk['risk_level'].lower()} and should be monitored."
    else:
        summary = "Most extracted values appear stable in this report, with no major flagged abnormalities."
    narrative = f"{summary} Suggested next steps focus on monitoring, follow-up, and steady self-care."
    return {"summary": summary, "narrative": narrative, "voice_text": summary}


def analyze_report(pdf_path: str, prior_reports: list[dict], report_id: int, uploaded_at: str) -> dict:
    text_layers = extract_report_text(pdf_path)
    parameters = extract_parameters(text_layers["combined_text"])
    risk = compute_risk(parameters)
    trends = build_trends(report_id, uploaded_at, parameters, prior_reports)
    recommendations = build_recommendations(parameters, risk)
    summary = generate_summary(text_layers["combined_text"], parameters, risk, recommendations)
    department = suggest_department(parameters, risk["risk_level"])
    return {
        **text_layers,
        **summary,
        "parameters": parameters,
        "risk": risk,
        "trends": trends,
        "recommendations": recommendations,
        "department": department,
    }


def inline_svg_trend(values: list[float], width: int = 240, height: int = 72) -> str:
    if not values:
        return ""
    if len(values) == 1:
        points = f"0,{height/2} {width},{height/2}"
    else:
        minimum = min(values)
        maximum = max(values)
        span = (maximum - minimum) or 1
        points_list = []
        for index, value in enumerate(values):
            x = index * (width / max(1, len(values) - 1))
            y = height - ((value - minimum) / span) * (height - 10) - 5
            points_list.append(f"{x:.1f},{y:.1f}")
        points = " ".join(points_list)
    return (
        f"<svg viewBox='0 0 {width} {height}' width='{width}' height='{height}' "
        f"xmlns='http://www.w3.org/2000/svg'><polyline fill='none' stroke='#00838f' "
        f"stroke-width='3' points='{points}' /></svg>"
    )
