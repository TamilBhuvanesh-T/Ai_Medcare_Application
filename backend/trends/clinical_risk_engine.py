PARAMETER_WEIGHTS = {
    'cholesterol_total': 1.2,
    'cholesterol_ldl': 1.4,
    'cholesterol_hdl': 1.0,
    'triglycerides': 1.2,
    'glucose_fasting': 1.3,
    'hba1c': 1.5,
    'hemoglobin': 1.0,
}

CLINICAL_KEYWORD_RULES = [
    ('intracerebral hemorrhage', 40, 'Intracerebral hemorrhage'),
    ('brain hemorrhage', 40, 'Brain hemorrhage'),
    ('hemorrhage', 25, 'Hemorrhage'),
    ('icu', 12, 'ICU care required'),
    ('loss of consciousness', 12, 'Loss of consciousness'),
    ('weakness', 8, 'Neurologic weakness'),
    ('edema', 8, 'Edema noted'),
    ('gcs', 10, 'Reduced Glasgow Coma Scale'),
    ('hypertensive', 8, 'Hypertensive emergency context'),
]


def compute_trend_risk(trend_data):
    risk = 0
    drivers = []

    for param, info in trend_data.items():
        trend = info['trend']
        weight = PARAMETER_WEIGHTS.get(param, 1.0)

        if trend == 'Increasing':
            risk += 10 * weight
            drivers.append(f"{param.replace('_', ' ').title()} increasing")
        elif trend == 'Decreasing':
            risk += 3 * weight
        elif trend == 'Stable':
            risk += 1 * weight

    return risk, drivers


def compute_knn_risk(knn_insight):
    if not knn_insight or 'distribution' not in knn_insight:
        return 10

    total = sum(knn_insight['distribution'].values())
    risky = 0

    for label, count in knn_insight['distribution'].items():
        if label.lower() in ['high_risk', 'worsening', 'abnormal']:
            risky += count

    if total == 0:
        return 10

    return (risky / total) * 40


def compute_record_risk(records):
    risk = 0
    drivers = []

    for record in records or []:
        status = (record.get('status') or '').lower()
        label = record.get('test_name', 'parameter').replace('_', ' ').title()

        if status in {'high', 'diabetes', 'critical'}:
            risk += 12
            drivers.append(f'{label} out of range')
        elif status in {'borderline', 'prediabetes', 'low'}:
            risk += 6
            drivers.append(f'{label} needs follow-up')

    return risk, drivers


def compute_text_risk(raw_text, report_sections):
    text = f'{raw_text}\n{report_sections}'.lower()
    score = 0
    drivers = []

    for keyword, weight, label in CLINICAL_KEYWORD_RULES:
        if keyword in text:
            score += weight
            drivers.append(label)

    if '180/110' in text or '180 / 110' in text:
        score += 15
        drivers.append('Severely elevated blood pressure')

    if 'stable' in text and score > 0:
        score -= 5

    return max(score, 0), drivers


def _risk_level_from_score(risk_score):
    if risk_score < 30:
        return 'Low', 'LOW'
    if risk_score < 65:
        return 'Moderate', 'MOD'
    return 'High', 'HIGH'


def compute_clinical_risk(
    trend_data,
    knn_insight=None,
    raw_text='',
    report_sections=None,
    report_type='lab',
    records=None,
):
    trend_risk, trend_drivers = compute_trend_risk(trend_data)
    knn_risk = compute_knn_risk(knn_insight)
    record_risk, record_drivers = compute_record_risk(records)
    text_risk, text_drivers = compute_text_risk(raw_text, report_sections or {})

    if report_type == 'clinical':
        raw_score = max(text_risk + record_risk, 20)
        if not text_drivers and not record_drivers:
            raw_score = 35
    else:
        raw_score = trend_risk + knn_risk + record_risk

    risk_score = min(int(raw_score), 100)
    risk_level, flag = _risk_level_from_score(risk_score)

    drivers = []
    for driver in text_drivers + record_drivers + trend_drivers:
        if driver not in drivers:
            drivers.append(driver)

    return {
        'risk_score': risk_score,
        'risk_level': risk_level,
        'flag': flag,
        'main_drivers': drivers[:4],
    }
