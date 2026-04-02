MEDICAL_KNOWLEDGE = {
    "cholesterol_total": {
        "description": (
            "Total cholesterol represents the overall amount of cholesterol "
            "in your blood. Cholesterol is a waxy substance required for "
            "cell membrane formation and hormone production."
        ),
        "why_high": (
            "Elevated total cholesterol is commonly caused by diets high in "
            "saturated fats, lack of physical activity, obesity, smoking, "
            "genetic factors, or underlying metabolic conditions."
        ),
        "impact": (
            "Persistently high cholesterol can lead to plaque buildup in arteries "
            "(atherosclerosis), increasing the risk of heart attack, stroke, "
            "and other cardiovascular diseases."
        ),
        "monitoring": (
            "Mild elevations may be managed with lifestyle changes, while "
            "significantly high levels often require medical supervision."
        )
    },

    "cholesterol_ldl": {
        "description": (
            "LDL cholesterol is often referred to as 'bad cholesterol'. "
            "It transports cholesterol particles throughout the body."
        ),
        "why_high": (
            "High LDL levels are associated with poor diet, smoking, insulin "
            "resistance, stress, and genetic predisposition."
        ),
        "impact": (
            "Excess LDL deposits cholesterol on artery walls, narrowing blood "
            "vessels and restricting blood flow to vital organs."
        ),
        "monitoring": (
            "High LDL is a major cardiovascular risk factor and usually "
            "requires prompt medical evaluation."
        )
    },

    "cholesterol_hdl": {
        "description": (
            "HDL cholesterol is known as 'good cholesterol'. It helps remove "
            "excess cholesterol from the bloodstream and transport it to the liver."
        ),
        "why_low": (
            "Low HDL levels are linked to sedentary lifestyle, obesity, smoking, "
            "and poor dietary habits."
        ),
        "impact": (
            "Low HDL reduces the body's ability to protect itself from cholesterol "
            "accumulation, increasing heart disease risk."
        ),
        "monitoring": (
            "HDL can often be improved through exercise, diet modification, "
            "and lifestyle changes."
        )
    },

    "triglycerides": {
        "description": (
            "Triglycerides are a type of fat found in the blood and are used "
            "as an energy source."
        ),
        "why_high": (
            "High triglycerides are commonly caused by excessive calorie intake, "
            "high sugar consumption, alcohol use, obesity, and uncontrolled diabetes."
        ),
        "impact": (
            "Elevated triglycerides increase the risk of pancreatitis and "
            "cardiovascular disease, especially when combined with high LDL."
        ),
        "monitoring": (
            "Lifestyle changes are usually effective, but very high levels "
            "require medical treatment."
        )
    }, 

    "glucose_fasting": {
        "description": (
            "Fasting blood glucose measures the amount of sugar in the blood "
            "after an overnight fast."
        ),
        "why_high": (
            "Elevated glucose levels are often caused by insulin resistance, "
            "poor dietary habits, stress, or early diabetes."
        ),
        "impact": (
            "Chronically high glucose damages blood vessels and nerves, "
            "leading to complications affecting the eyes, kidneys, heart, "
            "and nerves."
        ),
        "monitoring": (
            "Prediabetic levels require close monitoring and lifestyle intervention "
            "to prevent progression."
        )
    },

    "hba1c": {
        "description": (
            "HbA1c reflects the average blood sugar levels over the past "
            "2–3 months."
        ),
        "why_high": (
            "High HbA1c indicates sustained elevated blood glucose, often due "
            "to diabetes or poor glucose control."
        ),
        "impact": (
            "Poor long-term glucose control significantly increases the risk "
            "of organ damage."
        ),
        "monitoring": (
            "Medical supervision is strongly recommended for elevated HbA1c levels."
        )
    },

    "hemoglobin": {
        "description": (
            "Hemoglobin is a protein in red blood cells responsible for "
            "transporting oxygen throughout the body."
        ),
        "why_low": (
            "Low hemoglobin may be caused by iron deficiency, vitamin deficiencies, "
            "chronic illness, or blood loss."
        ),
        "impact": (
            "Reduced oxygen delivery can lead to fatigue, weakness, dizziness, "
            "and reduced physical performance."
        ),
        "monitoring": (
            "Persistent low hemoglobin should be medically evaluated to "
            "identify the underlying cause."
        )
    }
}


def get_medical_context(test_name: str):
    return MEDICAL_KNOWLEDGE.get(test_name)

