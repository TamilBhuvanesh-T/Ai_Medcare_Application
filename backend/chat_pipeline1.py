# chat_pipeline.py

from rag_pipeline import generate_ai_response
from icpa_validator import validate_response
from mail_service import send_emotion_alert

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()


def run_medical_chat(query, vector_store, patient_data, embed_fn):

    # --------------------------
    # 1️⃣ Emotion Score
    # --------------------------
    scores = analyzer.polarity_scores(query)
    emotion_score = scores["compound"]

    # --------------------------
    # 2️⃣ RAG + LLM
    # --------------------------
    ai_response = generate_ai_response(
        vector_store,
        query,
        embed_fn
    )

    # --------------------------
    # 3️⃣ ICPa Validation
    # --------------------------
    validation = validate_response(patient_data, ai_response)

    final_answer = validation["final_answer"]

    # --------------------------
    # 4️⃣ Tone Adjustment
    # --------------------------
    if emotion_score < -0.5:
        final_answer = "I understand your concern. " + final_answer

        validation["final_answer"] = final_answer
        validation["emotion_score"] = emotion_score

        # --------------------------
        # 5️⃣ 🚨 EMAIL ALERT
        # --------------------------
        if emotion_score < -0.5:
            send_emotion_alert(emotion_score)
            print("Validation result:", validation)

    return validation
