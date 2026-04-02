import json
import re

from backend.data_schema import MedicalRecord
from backend.llm_engine import run_llm
from backend.medical_normalizer import normalize_test_name
from backend.medical_rules import apply_medical_rules
from backend.pdf_parser import (
    detect_report_type,
    extract_report_date,
    extract_report_sections,
    parse_medical_file,
)
from backend.rag.vector_store import build_vector_store
from backend.summary_engine import (
    generate_detailed_health_report,
    generate_llm_summary,
)
from backend.trends.clinical_risk_engine import compute_clinical_risk
from backend.trends.insight_narrator import generate_health_narrative
from backend.trends.trend_analyzer import analyze_trends


def _build_trend_input(rule_results):
    return [
        {
            'parameter': result['test_name'],
            'value': result['value'],
            'unit': result['unit'],
            'date': result['date'],
        }
        for result in rule_results
    ]


def _parse_override_text(raw_text):
    report_date = extract_report_date(raw_text)
    sections = extract_report_sections(raw_text)
    records = []
    report_type = detect_report_type(sections, raw_text)
    return records, sections, report_type, report_date


def _extract_number_and_unit(value_text):
    cleaned = (value_text or "").strip()
    match = re.search(r'(-?\d+(?:\.\d+)?)\s*([A-Za-z/%^\d\.]+)?', cleaned)
    if not match:
        return None, ""
    return float(match.group(1)), (match.group(2) or "").strip()


def _parse_llm_json(text):
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return {}


def _ai_extract_lab_records(raw_text, report_date):
    prompt = f"""
You are a lab specialist analysis AI.

Read the below content and extract:
- Test names
- Their exact values without changing them

Return ONLY valid JSON like:
{{
  "Hemoglobin": "13.5 g/dL",
  "BNP": "587 pg/mL"
}}

If the content is unclear, return {{}}

DOCUMENT:
{raw_text[:4000]}
"""
    llm_output = run_llm(prompt)
    extracted = _parse_llm_json(llm_output)
    records = []

    for raw_name, raw_value in extracted.items():
        value, unit = _extract_number_and_unit(str(raw_value))
        if value is None:
            continue
        records.append(
            MedicalRecord(
                test_name=normalize_test_name(str(raw_name)),
                value=value,
                unit=unit,
                reference_range="",
                report_date=report_date,
            )
        )

    return records


def run_full_pipeline(file_path, override_text=None):
    """Run the end-to-end medical report pipeline for a single uploaded report file."""

    try:
        if override_text and override_text.strip():
            raw_text = override_text.strip()
            records, sections, report_type, report_date = _parse_override_text(raw_text)
        else:
            parsed = parse_medical_file(file_path)
            records = parsed.get('records', [])
            raw_text = parsed.get('raw_text', '')
            sections = parsed.get('sections', {})
            report_type = parsed.get('report_type', 'lab')
            report_date = parsed.get('report_date')
    except Exception as exc:
        print(f'[WARN] Failed to parse {file_path}: {exc}')
        records, raw_text, sections, report_type, report_date = [], '', {}, 'unknown', None

    if report_type == 'lab' and raw_text and len(records) < 2:
        ai_records = _ai_extract_lab_records(raw_text, report_date)
        if len(ai_records) > len(records):
            records = ai_records

    rule_results = apply_medical_rules(records) if records else []

    trend_data = {}
    if report_type == 'lab' and rule_results:
        trend_data = analyze_trends(_build_trend_input(rule_results))

    risk = compute_clinical_risk(
        trend_data,
        knn_insight=None,
        raw_text=raw_text,
        report_sections=sections,
        report_type=report_type,
        records=rule_results,
    )

    try:
        build_vector_store([file_path])
    except Exception as exc:
        print(f'[WARN] Vector store build failed: {exc}')

    summary = generate_llm_summary(
        rule_results,
        raw_text=raw_text,
        report_sections=sections,
        report_type=report_type,
    )
    narrative = generate_health_narrative(
        trend_data,
        knn_insight=None,
        risk=risk,
        raw_text=raw_text,
        report_sections=sections,
        report_type=report_type,
    )
    detailed_health_report = generate_detailed_health_report(
        summary=summary,
        narrative=narrative,
        risk=risk,
        corrected_report=raw_text,
        report_type=report_type,
    )

    if not raw_text and not rule_results:
        summary = 'No medical data found in the uploaded report.'

    return {
        'summary': summary,
        'narrative': narrative,
        'trends': trend_data,
        'risk': risk,
        'records': rule_results,
        'report_type': report_type,
        'sections': sections,
        'report_date': report_date,
        'raw_extracted_text': raw_text,
        'detailed_health_report': detailed_health_report,
        'pdfplumber_text': parsed.get('pdfplumber_text', '') if 'parsed' in locals() and isinstance(parsed, dict) else '',
        'pypdf2_text': parsed.get('pypdf2_text', '') if 'parsed' in locals() and isinstance(parsed, dict) else '',
        'ocr_text': parsed.get('ocr_text', '') if 'parsed' in locals() and isinstance(parsed, dict) else '',
    }
