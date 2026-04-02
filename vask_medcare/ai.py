import json
import shutil
import subprocess


def run_ollama(prompt: str, model: str = "phi3:mini", timeout: int = 5) -> str:
    executable = shutil.which("ollama")
    if not executable:
        return ""
    try:
        result = subprocess.run(
            [executable, "run", model],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout,
            encoding="utf-8",
            errors="ignore",
        )
        return result.stdout.strip()
    except Exception:
        return ""


def ask_llm_json(prompt: str) -> dict:
    raw = run_ollama(prompt)
    if not raw:
        return {}
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return {}
        return {}


def ask_llm_text(prompt: str) -> str:
    return run_ollama(prompt)


def analyze_message(message: str, context_summary: str, doctor_guidance: str = "") -> dict:
    prompt = f"""
Analyze the full patient message semantically.
Do not rely only on keywords. Use the whole meaning, tone, and implied concern.

Patient context summary:
{context_summary}

Doctor guidance:
{doctor_guidance or 'None'}

User message:
{message}

Return JSON:
{{
  "intent": "report question / reassurance / appointment / distress / trend question / other",
  "emotion": "Distressed | Anxious | Neutral | Calm | Happy | Confused | Overwhelmed | Sad",
  "mood": "short phrase",
  "urgency": "low | medium | high",
  "safety_risk": "none | watch | urgent"
}}
"""
    data = ask_llm_json(prompt)
    if data.get("emotion"):
        return data

    lowered = message.lower()
    emotion = "Neutral"
    urgency = "low"
    safety = "none"
    mood = "steady and information-seeking"
    intent = "report question"

    if any(phrase in lowered for phrase in ["scared", "worried", "afraid", "stress", "anxious"]):
        emotion = "Anxious"
        urgency = "medium"
        mood = "worried about current health findings"
    if any(phrase in lowered for phrase in ["can't handle", "hopeless", "worthless", "end it", "kill myself", "suicide"]):
        emotion = "Distressed"
        urgency = "high"
        safety = "urgent"
        mood = "deeply distressed and may need immediate support"
        intent = "distress"
    elif any(phrase in lowered for phrase in ["confused", "don't understand", "not sure"]):
        emotion = "Confused"
        mood = "uncertain and seeking explanation"

    return {
        "intent": intent,
        "emotion": emotion,
        "mood": mood,
        "urgency": urgency,
        "safety_risk": safety,
    }


def generate_chat_reply(message: str, report_context: str, doctor_guidance: str, emotion_result: dict, recommendations: list[str]) -> str:
    prompt = f"""
You are the VASK MedCare assistant.
Answer using the patient report context. Keep it safe, calm, and clear.
Do not diagnose. Explain findings and suggest practical next steps only.

Doctor guidance:
{doctor_guidance or 'None'}

Emotion context:
{emotion_result}

Report context:
{report_context[:5000]}

Dynamic recommendations:
{recommendations}

Question:
{message}
"""
    reply = ask_llm_text(prompt)
    if reply:
        return reply.strip()

    base = "I can help explain what your report suggests based on the uploaded data."
    if emotion_result.get("emotion") in {"Anxious", "Overwhelmed"}:
        base = "I can see this feels stressful, so I’ll keep this simple and calm."
    if emotion_result.get("safety_risk") == "urgent":
        return (
            "Your message sounds urgent. Please reach out to a trusted person or local emergency support now, "
            "and contact your care team immediately. I can still summarize the report, but urgent human help matters first."
        )
    if recommendations:
        return f"{base} Based on your latest report, the main focus is careful monitoring. Suggested next steps: {', '.join(recommendations[:3])}."
    return f"{base} Based on the latest report, the current risk should be reviewed with your doctor for tailored follow-up."
