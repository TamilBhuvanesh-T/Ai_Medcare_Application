def validate_response(patient_data, ai_response):

    # ✅ SAFETY CHECK (IMPORTANT)
    if not ai_response:

        print("AI RESPONSE:", ai_response)
        return {
            "final_answer": "Sorry, I couldn't generate a response. Please try again.",
            "issues": ["AI response was empty"],
            "confidence": "low"
        }


    issues = []
    corrected = ai_response

    glucose = patient_data.get("glucose")
    egfr = patient_data.get("egfr")

    response_lower = ai_response.lower()

# 🔍 Glucose Rule
    if glucose is not None and glucose > 110 and "normal" in response_lower:
        issues.append("Glucose mismatch")
        corrected = corrected.replace(
        "normal",
        "slightly elevated (pre-diabetic range)"
    )

    # 🔍 eGFR Rule
    if egfr is not None and egfr < 60 and "normal" in response_lower:
        issues.append("Kidney function mismatch")
        corrected += "\n\n⚠️ eGFR indicates reduced kidney function."

        confidence = "low" if issues else "high"

    return {
            "final_answer": corrected,
            "issues": issues,
            "confidence": confidence
        }
