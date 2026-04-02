from backend.llm_engine import run_llm
from backend.prompts import INSIGHT_PROMPT


def _build_clinical_narrative(report_sections, risk):
    diagnosis = report_sections.get('Diagnosis', 'The diagnosis section was not clearly extracted.')
    condition = report_sections.get('Current Condition', '')
    treatment = report_sections.get('Treatment', '')
    recommendations = report_sections.get('Recommendations', '')
    complaints = report_sections.get('Chief Complaint', '')

    parts = [
        f"This report describes an acute clinical event with {risk['risk_level'].lower()} overall risk.",
        f'Key concern: {diagnosis}',
    ]

    if complaints:
        parts.append(f'Presenting symptoms include {complaints}.')
    if treatment:
        parts.append(f'Current management includes {treatment}.')
    if condition:
        parts.append(f'Current condition: {condition}.')
    if recommendations:
        parts.append(f'Recommended next steps: {recommendations}.')

    return ' '.join(parts)


def generate_health_narrative(
    trends,
    knn_insight=None,
    risk=None,
    raw_text='',
    report_sections=None,
    report_type='lab',
):
    if report_type == 'clinical':
        return _build_clinical_narrative(
            report_sections or {},
            risk or {'risk_level': 'Unknown'},
        )

    if not knn_insight:
        knn_insight = 'Similarity data not available.'

    risk_text = ''
    if risk:
        risk_text = f"""
Overall Health Status: {risk['flag']} {risk['risk_level']} Risk
Risk Score: {risk['risk_score']} / 100
Main contributing factors: {', '.join(risk['main_drivers'])}
"""

    prompt = INSIGHT_PROMPT.format(
        trends=trends,
        knn=knn_insight,
    )

    return run_llm(risk_text + '\n' + prompt)
