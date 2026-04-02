from .gemini_engine import run_gemini
from .llm_engine import run_llm
from .medical_knowledge import get_medical_context
from .prompts import SUMMARY_PROMPT


CLINICAL_SUMMARY_TEMPLATE = (
    'This report describes a clinical event rather than a routine lab-only check. '
    'Primary diagnosis: {diagnosis}. '
    '{complaints}'
    '{history}'
    '{exam}'
    '{investigations}'
    '{treatment}'
    '{condition}'
    '{recommendations}'
)


def _pretty_label(test_name: str) -> str:
    return (test_name or 'parameter').replace('_', ' ').title()


def _build_sentence(prefix, value):
    return f'{prefix}{value}. ' if value else ''


def generate_corrected_report(raw_text='', report_sections=None, report_type='lab', records=None):
    report_sections = report_sections or {}
    records = records or []

    if report_sections:
        ordered_sections = [
            'Patient Information',
            'Chief Complaint',
            'Medical History',
            'Clinical Examination',
            'Investigations',
            'Diagnosis',
            'Treatment',
            'Current Condition',
            'Recommendations',
            'Doctor',
        ]
        lines = []
        for section in ordered_sections:
            value = report_sections.get(section)
            if value:
                lines.append(f'{section}:\n{value}')

        if lines:
            return '\n\n'.join(lines)

    if report_type == 'lab' and records:
        lines = ['Extracted Lab Report:']
        for record in records:
            lines.append(
                f"Parameter: {_pretty_label(record.get('test_name'))}\n"
                f"Value: {record.get('value')} {record.get('unit', '')}\n"
                f"Status: {record.get('status', 'unknown')}\n"
                f"Reference Range: {record.get('reference_range', 'n/a')}"
            )
        return '\n'.join(lines)

    return raw_text.strip() if raw_text else 'No extracted report text available.'


def generate_clinical_summary(report_sections):
    diagnosis = report_sections.get('Diagnosis', 'Diagnosis was not clearly extracted')
    return CLINICAL_SUMMARY_TEMPLATE.format(
        diagnosis=diagnosis,
        complaints=_build_sentence('Key presenting features: ', report_sections.get('Chief Complaint', '')),
        history=_build_sentence('Relevant history: ', report_sections.get('Medical History', '')),
        exam=_build_sentence('Clinical examination: ', report_sections.get('Clinical Examination', '')),
        investigations=_build_sentence('Investigations show: ', report_sections.get('Investigations', '')),
        treatment=_build_sentence('Treatment given: ', report_sections.get('Treatment', '')),
        condition=_build_sentence('Current condition: ', report_sections.get('Current Condition', '')),
        recommendations=_build_sentence('Recommendations: ', report_sections.get('Recommendations', '')),
    ).strip()


def generate_extended_summary(records):
    explanations = []
    has_abnormality = False

    for record in records:
        status = (record.get('status') or 'unknown').lower()
        if status in {'normal', 'unknown'}:
            continue

        has_abnormality = True
        test_name = record.get('test_name', '')
        value = record.get('value')
        unit = record.get('unit', '')
        reference_range = record.get('reference_range', '')
        risk = record.get('risk', '')
        knowledge = get_medical_context(test_name)
        label = _pretty_label(test_name)

        if knowledge:
            reasons = knowledge.get('why_high') or knowledge.get('why_low') or 'Clinical correlation may be needed.'
            explanation = (
                f'{label}: reported as {value} {unit} ({status}). '
                f'What it is: {knowledge.get("description", "")} '
                f'Possible reasons: {reasons} '
                f'Potential impact: {knowledge.get("impact", "")} '
                f'Monitoring: {knowledge.get("monitoring", "")}'
            ).strip()
        else:
            explanation = (
                f'{label}: reported as {value} {unit} ({status}). '
                f'Reference range: {reference_range or "Not clearly available in the report"}. '
                f'{risk or "Interpret using the report reference range and clinical context."}'
            ).strip()

        explanations.append(explanation)

    if not has_abnormality:
        return {
            'summary': 'All extracted parameters that could be evaluated appear within range or could not be confidently classified.',
            'recommendation': 'Continue routine follow-up as advised by a clinician.',
        }

    return {
        'summary': '\n'.join(explanations),
        'recommendation': 'Abnormal or borderline findings should be correlated with a healthcare professional.',
    }


def build_structured_findings(records):
    findings = []

    for record in records:
        parameter = record.get('parameter') or record.get('test_name')
        value = record.get('value')
        unit = record.get('unit', '')
        status = record.get('status', 'unknown')
        reference_range = record.get('reference_range', '')

        if parameter is None or value is None:
            continue

        findings.append(
            f'{_pretty_label(parameter)}: {value} {unit} | status={status} | reference={reference_range or "n/a"}'
        )

    return '\n'.join(f'- {finding}' for finding in findings) if findings else '- No structured findings available.'


def generate_llm_summary(records, raw_text='', report_sections=None, report_type='lab'):
    if report_type == 'clinical':
        return generate_clinical_summary(report_sections or {})

    if not records:
        return 'No medical data available.'

    full_data = []
    for record in records:
        full_data.append(
            f'{_pretty_label(record.get("test_name"))}: '
            f'{record.get("value")} {record.get("unit", "")} '
            f'(status: {record.get("status", "unknown")}, '
            f'reference: {record.get("reference_range", "n/a")}, '
            f'date: {record.get("date")})'
        )

    full_data_text = '\n'.join(full_data)
    structured_findings = build_structured_findings(records)
    extended = generate_extended_summary(records)
    rule_summary = extended.get('summary', '')

    prompt = SUMMARY_PROMPT.format(
        findings=structured_findings,
        full_data=full_data_text,
        rule_summary=rule_summary,
        raw_text=raw_text[:4000] if raw_text else 'Not available.',
    )

    try:
        gemini_output = run_gemini(prompt)
        if gemini_output and gemini_output.strip():
            return gemini_output.strip()
    except Exception:
        pass

    llm_output = run_llm(prompt)
    if llm_output and llm_output.strip():
        return llm_output.strip()

    return rule_summary or 'Summary could not be generated.'


def generate_detailed_health_report(summary, narrative, risk, corrected_report, report_type='lab'):
    headline = 'This is an AI summarized detailed health report based on the extracted medical document.'
    risk_line = (
        f"Overall risk level is {risk.get('risk_level', 'Unknown')} with score "
        f"{risk.get('risk_score', 0)} out of 100. Main drivers: "
        f"{', '.join(risk.get('main_drivers', [])) or 'Not clearly identified'}."
    )
    report_label = 'clinical case summary' if report_type == 'clinical' else 'laboratory-style medical report'

    prompt = f"""
You are a senior medical report explainer AI.

Write a detailed processed medical discussion of at least 700 words.

Requirements:
- Make it feel like a carefully reviewed medical case discussion, not a short summary
- Organize it in coherent paragraphs with clear medical reasoning
- Explain what the report appears to show, the likely significance of the findings, clinical context, possible implications, and practical follow-up meaning
- Do not invent new patient facts beyond the provided content
- Do not prescribe medication
- Keep the tone informative, medically oriented, and easy to understand
- Use the processed findings, risk information, and extracted report text below

Report type:
{report_label}

Risk:
{risk_line}

Summary:
{summary}

Narrative:
{narrative}

Extracted report text:
{corrected_report[:6000]}
"""

    try:
        llm_output = run_llm(prompt)
        if llm_output and len(llm_output.split()) >= 350:
            return llm_output.strip()
    except Exception:
        pass

    return (
        f"{headline} This document has been interpreted as a {report_label}. {risk_line} "
        f"The processed summary indicates the following: {summary} "
        f"The broader health narrative is as follows: {narrative} "
        f"In practical terms, this means the report should be read not just as isolated values or isolated clinical statements, but as a connected medical picture where the extracted findings, background context, and apparent follow-up needs all contribute to overall interpretation. "
        f"When the report is clinical in nature, the focus should remain on diagnosis, presenting features, investigations, current treatment direction, and monitoring priorities. "
        f"When the report is laboratory-oriented, the focus should remain on which parameters appear normal, abnormal, borderline, or clinically relevant, and how those findings may influence future review or repeat testing. "
        f"The extracted report text also provides important context that should be considered alongside the summarized interpretation: {corrected_report[:4000]}"
    ).strip()
