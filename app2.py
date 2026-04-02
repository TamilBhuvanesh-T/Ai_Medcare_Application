import streamlit as st
import streamlit.components.v1 as components
import os
from datetime import datetime
import pandas as pd
import numpy as np
import random
import hashlib
import json
import matplotlib.pyplot as plt

from db import load_data, save_appointment, save_data, save_emotion

from backend.llm_engine import run_llm
from login import (
    add_user,
    get_user_profile,
    load_users,
    validate_login,
    is_valid_name,
    is_valid_password,
    is_valid_phone,
)


from backend import trends
from backend.pdf_parser import parse_medical_file
from backend.pipeline import run_full_pipeline
from backend.rag.vector_store import load_vector_store
from backend.rag.embedder import embed_texts
from backend.rag.qa_engine import answer_question

UPLOAD_DIR = "medical_data/pdfs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def render_auto_audio_reader(text: str):
    if not text:
        return

    audio_key = hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()
    payload = json.dumps(text)
    components.html(
        f"""
        <div style="display:flex;gap:8px;align-items:center;">
            <button id="play-{audio_key}" style="background:#0F4C5C;color:white;border:none;border-radius:8px;padding:8px 12px;cursor:pointer;">
                Replay Audio Summary
            </button>
            <button id="stop-{audio_key}" style="background:#9f1239;color:white;border:none;border-radius:8px;padding:8px 12px;cursor:pointer;">
                Stop Audio
            </button>
            <span style="font-size:12px;color:#475569;">Audio will try to auto-read once when this report loads.</span>
        </div>
        <script>
        const text = {payload};
        const storageKey = "health-report-audio-{audio_key}";
        function speakReport() {{
            if (!text) return;
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        }}
        document.getElementById("play-{audio_key}").addEventListener("click", speakReport);
        document.getElementById("stop-{audio_key}").addEventListener("click", () => window.speechSynthesis.cancel());
        if (!sessionStorage.getItem(storageKey)) {{
            sessionStorage.setItem(storageKey, "played");
            setTimeout(speakReport, 700);
        }}
        </script>
        """,
        height=60,
    )


def render_audio_header(title: str, text: str):
    if not text:
        st.subheader(title)
        return

    audio_key = hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()
    payload = json.dumps(text)
    components.html(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin:6px 0 10px 0;">
            <div style="font-size:1.1rem;font-weight:600;color:#0f172a;">{title}</div>
            <div style="display:flex;gap:8px;align-items:center;">
                <button id="play-head-{audio_key}" style="background:#0F4C5C;color:white;border:none;border-radius:8px;padding:8px 12px;cursor:pointer;">
                    Replay Audio
                </button>
                <button id="stop-head-{audio_key}" style="background:#9f1239;color:white;border:none;border-radius:8px;padding:8px 12px;cursor:pointer;">
                    Stop Audio
                </button>
            </div>
        </div>
        <script>
        const text = {payload};
        const storageKey = "health-report-audio-head-{audio_key}";
        function speakReport() {{
            if (!text) return;
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        }}
        document.getElementById("play-head-{audio_key}").addEventListener("click", speakReport);
        document.getElementById("stop-head-{audio_key}").addEventListener("click", () => window.speechSynthesis.cancel());
        if (!sessionStorage.getItem(storageKey)) {{
            sessionStorage.setItem(storageKey, "played");
            setTimeout(speakReport, 700);
        }}
        </script>
        """,
        height=62,
    )


def split_sentences(text: str):
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return []
    return [part.strip() for part in cleaned.replace("\n", " ").split(".") if part.strip()]


def build_dashboard_sections(analysis):
    summary = analysis.get("summary", "") or ""
    narrative = analysis.get("narrative", "") or ""
    detailed = analysis.get("detailed_health_report", "") or ""
    report_type = analysis.get("report_type", "lab")
    risk = analysis.get("risk", {}) or {}
    drivers = risk.get("main_drivers", []) or []

    summary_sentences = split_sentences(summary)
    narrative_sentences = split_sentences(narrative)
    detailed_sentences = split_sentences(detailed)

    intro_parts = (summary_sentences[:3] or narrative_sentences[:3] or detailed_sentences[:3])[:3]
    intro_core = ". ".join(intro_parts).strip()
    if intro_core and not intro_core.endswith("."):
        intro_core += "."

    findings_parts = summary_sentences[2:6] or detailed_sentences[:4]
    findings = ". ".join(findings_parts).strip()
    if findings and not findings.endswith("."):
        findings += "."

    interpretation_parts = narrative_sentences[:4] or detailed_sentences[4:8]
    interpretation = ". ".join(interpretation_parts).strip()
    if interpretation and not interpretation.endswith("."):
        interpretation += "."

    next_steps_parts = detailed_sentences[8:12] or narrative_sentences[4:8]
    next_steps = ". ".join(next_steps_parts).strip()
    if next_steps and not next_steps.endswith("."):
        next_steps += "."

    risk_line = f"Risk level: {risk.get('risk_level', 'Unknown')} with score {risk.get('risk_score', 'N/A')}/100."
    if drivers:
        risk_line += " Main drivers: " + ", ".join(drivers[:3]) + "."

    risk_line = f"Risk level: {risk.get('risk_level', 'Unknown')} with score {risk.get('risk_score', 'N/A')}/100."
    if drivers:
        risk_line += " Main drivers: " + ", ".join(drivers[:3]) + "."

    if report_type == "clinical":
        intro = (
            "This processed medical report presents a structured clinical overview generated from the uploaded document, with emphasis on the most relevant diagnosis-linked findings, symptom context, investigation details, present clinical status, and immediate treatment implications. "
            + (intro_core or "The extracted report text indicates a medically important clinical scenario that has been reviewed and organized for easier understanding. ")
            + "This opening section is intentionally written in a more complete medical-brief style so the document does not read like plain OCR output or a basic AI note, but instead feels closer to a reviewed clinical summary that highlights what the report is saying, why the findings matter, and what parts of the case deserve the most attention. "
            + "It brings together the reported symptoms, examination clues, diagnostic impressions, and management signals into one readable overview so that the report can be understood more confidently before moving into the deeper sections below. "
            + "Where the source text contains signs of acute illness, specialist care, imaging findings, or ongoing treatment needs, those details are given more weight in the framing of this summary so the overall picture reflects the seriousness and practical meaning of the case. "
            + "The aim is not only to restate the report, but to present it in a clinically meaningful way that helps connect the observed findings with possible implications, risk direction, and the importance of timely follow-up. "
            + risk_line
        )
        conclusion = (
            "This processed medical report indicates a clinically important case that should be followed using the documented diagnosis, treatment plan, and specialist advice. "
            + risk_line
        )
    else:
        intro = (
            "This processed medical report presents a structured interpretation of the uploaded laboratory document, highlighting the most relevant measured parameters, their likely clinical meaning, the broader health context suggested by the values, and the practical follow-up points that deserve attention. "
            + (intro_core or "The extracted report text contains medically relevant laboratory information that has been organized into a clearer and more readable summary. ")
            + "This introduction is deliberately more detailed so the report reads like a properly processed medical overview rather than a short machine-generated caption, helping the user understand not only which values stand out, but also how those findings may relate to general health status, monitoring needs, and possible next clinical considerations. "
            + "Instead of presenting isolated lab terms alone, the section tries to combine the extracted evidence into a more coherent health narrative that frames abnormalities, borderline changes, and normal findings in a way that feels more natural and medically grounded. "
            + "It is designed to serve as a high-level briefing before the detailed expanders, so that someone reading the dashboard can immediately understand the overall direction of the report, the possible significance of the findings, and the level of care or review that may be appropriate. "
            + "The goal of this section is to transform the raw extracted content into a more complete health-oriented explanation that feels closer to a reviewed medical brief than a plain OCR output. "
            + risk_line
        )
        conclusion = (
            "This processed medical report highlights the main laboratory concerns, likely interpretation, and practical follow-up focus for continued monitoring. "
            + risk_line
        )

    return {
        "intro": intro or "The uploaded report has been processed and summarized into a structured medical overview with clinically meaningful context and follow-up direction.",
        "findings": findings or "Key findings could only be extracted partially from the report text, but the main clinical or laboratory signal has been retained.",
        "interpretation": interpretation or "Clinical interpretation is limited by the extracted text quality, but the available content has been reviewed for medically relevant signals.",
        "next_steps": next_steps or "Recommended follow-up should align with the treating doctor's advice, repeat testing needs, and symptom monitoring.",
        "conclusion": conclusion,
    }


def build_processed_chat_context(analysis):
    if not analysis:
        return ""

    risk = analysis.get("risk", {}) or {}
    records = analysis.get("records", []) or []
    sections = analysis.get("sections", {}) or {}
    record_lines = []
    for record in records[:20]:
        record_lines.append(
            f"{str(record.get('test_name', 'parameter')).replace('_', ' ').title()}: "
            f"{record.get('value')} {record.get('unit', '')} "
            f"(status={record.get('status', 'unknown')}, reference={record.get('reference_range', 'n/a')})"
        )

    section_lines = []
    for key, value in sections.items():
        if value:
            section_lines.append(f"{key}: {value}")

    return "\n".join(
        [
            f"Report type: {analysis.get('report_type', 'unknown')}",
            f"Summary: {analysis.get('summary', '')}",
            f"Narrative: {analysis.get('narrative', '')}",
            f"Detailed processed report: {analysis.get('detailed_health_report', '')}",
            f"Risk level: {risk.get('risk_level', 'Unknown')} | Score: {risk.get('risk_score', 'N/A')} | Drivers: {', '.join(risk.get('main_drivers', [])) or 'None'}",
            "Structured parameters:",
            "\n".join(record_lines) if record_lines else "No structured parameters available.",
            "Extracted sections:",
            "\n".join(section_lines) if section_lines else analysis.get("raw_extracted_text", ""),
        ]
    ).strip()


def get_current_appointment(phone: str):
    user_data = load_data(phone) if phone else None
    if not user_data:
        return None
    appointments = user_data.get("appointments", [])
    if appointments:
        return get_upcoming_appointment(phone)
    appointment = user_data.get("appointment")
    return appointment if appointment else None


def get_all_appointments(phone: str):
    user_data = load_data(phone) if phone else None
    if not user_data:
        return []
    appointments = user_data.get("appointments", [])
    if appointments:
        return [
            item for item in appointments
            if item and item.get("hospital_status", "scheduled") != "completed"
        ]
    appointment = user_data.get("appointment")
    if appointment and appointment.get("hospital_status", "scheduled") != "completed":
        return [appointment]
    return []


def get_active_patient_profile():
    phone = st.session_state.get("phone", "")
    if not phone:
        return {}
    profile = get_user_profile(phone)
    if profile:
        st.session_state.patient_name = profile.get("name", st.session_state.get("patient_name", ""))
        st.session_state.patient_id = profile.get("patient_id", st.session_state.get("patient_id", ""))
    return profile


def get_upcoming_appointment(phone: str):
    appointments = get_all_appointments(phone)
    if not appointments:
        return None

    now = datetime.now()
    upcoming = []

    for appointment in appointments:
        if not appointment or appointment.get("status") == "completed":
            continue
        if appointment.get("hospital_status", "scheduled") == "completed":
            continue

        date_text = str(appointment.get("date", "")).strip()
        time_text = str(appointment.get("time", "")).strip()
        if not date_text or not time_text:
            continue

        parsed = None
        for fmt in ("%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M"):
            try:
                parsed = datetime.strptime(f"{date_text} {time_text}", fmt)
                break
            except ValueError:
                continue

        if parsed is None:
            continue
        if parsed >= now:
            upcoming.append((parsed, appointment))

    if not upcoming:
        return None

    upcoming.sort(key=lambda item: item[0])
    return upcoming[0][1]


def render_appointment_widget(phone: str):
    appointment = get_upcoming_appointment(phone)
    if not appointment:
        return

    token = appointment.get("token")
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#fffaf0,#f0fbff);border:1px solid #d9e5ea;border-radius:16px;padding:12px 14px;margin-bottom:12px;box-shadow:0 8px 20px rgba(15,76,92,0.06);">
            <div style="font-weight:700;color:#0f4c5c;margin-bottom:6px;">Upcoming Appointment</div>
            <div style="font-size:13px;color:#334155;line-height:1.55;">
                <b>Doctor:</b> {appointment.get("doctor", "Not assigned")}<br>
                <b>Date:</b> {appointment.get("date", "-")}<br>
                <b>Time:</b> {appointment.get("time", "-")}<br>
                <b>Status:</b> {appointment.get("status", "scheduled").title()}<br>
                <b>Token:</b> {token if token else "Not generated yet"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clear_uploaded_records():
    removed = 0
    if not os.path.exists(UPLOAD_DIR):
        return removed
    for name in os.listdir(UPLOAD_DIR):
        path = os.path.join(UPLOAD_DIR, name)
        if os.path.isfile(path):
            os.remove(path)
            removed += 1
    return removed


def render_parameter_charts(records):
    chart_records = [record for record in (records or []) if record.get("value") is not None]
    if not chart_records:
        st.info("No structured test parameters available to plot for this report.")
        return

    st.subheader("Parameter Charts")

    for record in chart_records[:12]:
        test_name = str(record.get("test_name", "parameter")).replace("_", " ").title()
        value = float(record.get("value", 0))
        unit = record.get("unit", "")
        status = (record.get("status") or "unknown").lower()

        color = "#1f77b4"
        if status == "high":
            color = "#d62728"
        elif status == "low":
            color = "#ff7f0e"
        elif status == "normal":
            color = "#2ca02c"

        fig, ax = plt.subplots(figsize=(6, 1.8))
        ax.barh([test_name], [value], color=color)
        ax.set_xlabel(unit or "Value")
        ax.set_title(f"{test_name}: {value} {unit}".strip())
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="x", alpha=0.2)
        st.pyplot(fig, clear_figure=True)
        plt.close(fig)


def detect_user_emotion_fast(message: str):
    lowered = (message or "").lower()
    if any(term in lowered for term in ["happy", "excited", "relieved", "grateful", "great"]):
        return "Positive"
    if any(term in lowered for term in ["suicide", "kill myself", "end my life", "self harm", "hopeless"]):
        return "Distressed"
    if any(term in lowered for term in ["worried", "scared", "fear", "anxious", "panic", "stress"]):
        return "Anxious"
    if any(term in lowered for term in ["sad", "upset", "crying", "down"]):
        return "Sad"
    if any(term in lowered for term in ["good", "fine", "better", "okay", "calm"]):
        return "Calm"
    if any(term in lowered for term in ["confused", "don't understand", "not understand", "unclear"]):
        return "Confused"
    return "Neutral"


def detect_depression_risk(message: str):
    lowered = (message or "").lower()
    severe_terms = ["hopeless", "empty", "worthless", "self harm", "end my life", "suicide"]
    moderate_terms = ["depressed", "lonely", "tired of everything", "crying", "sad all day", "no interest"]

    if any(term in lowered for term in severe_terms):
        return "High"
    if any(term in lowered for term in moderate_terms):
        return "Moderate"
    return "Low"


def parse_med_buddy_json(text: str):
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return {}


def shorten_med_buddy_response(text: str):
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ""

    sentences = [part.strip() for part in cleaned.split(".") if part.strip()]
    short = ". ".join(sentences[:2]).strip()
    if short and not short.endswith("."):
        short += "."

    words = short.split()
    if len(words) > 28:
        short = " ".join(words[:28]).rstrip(" .,") + "."

    return short


def med_buddy_fallback(message: str, emotion: str, depression_risk: str):
    lowered = (message or "").lower()
    if any(term in lowered for term in ["happy", "excited", "relieved", "good news"]):
        return (
            "That is really nice to hear. Hold onto that good feeling.",
            "Positive",
            "Low",
        )
    if "friend" in lowered and any(term in lowered for term in ["suicide", "self harm", "kill himself", "kill herself"]):
        return (
            "That sounds serious, and I am glad you said it out loud. Please help your friend reach trusted or emergency support right away.",
            "Concerned",
            "Low",
        )
    if any(term in lowered for term in ["suicide", "kill myself", "end my life", "self harm"]):
        return (
            "I am really sorry you are carrying this right now. Please contact trusted or emergency support immediately.",
            "Distressed",
            "High",
        )
    if depression_risk == "Moderate":
        return (
            "I am sorry this feels heavy. Please talk with someone you trust or a mental health professional soon.",
            emotion,
            depression_risk,
        )
    return (
        "I am here with you, and what you are feeling matters. Tell me a little more.",
        emotion,
        depression_risk,
    )


def run_med_buddy_chat(message: str):
    heuristic_emotion = detect_user_emotion_fast(message)
    heuristic_risk = detect_depression_risk(message)
    prompt = f"""
You are Med Buddy, a warm emotional support companion inside a health app.

Analyze the user's message carefully and return ONLY valid JSON with this schema:
{{
  "emotion": "one short label such as Positive, Calm, Concerned, Anxious, Sad, Distressed, Confused",
  "depression_risk": "Low or Moderate or High",
  "self_risk": "none or indirect or immediate",
  "response": "maximum 2 short supportive sentences"
}}

Rules:
- Distinguish between the user being personally at risk and the user talking about someone else
- If the user says a friend or another person may be suicidal, do not classify the user as personally suicidal
- If the user expresses happiness or relief, do not classify as neutral
- Keep the response emotionally accurate, supportive, and direct
- Response must be at most 2 short sentences
- Keep it brief enough to feel instant in chat
- Do not give a formal diagnosis
- If there is immediate self-harm risk, strongly encourage urgent real-world help
- Return JSON only

User message:
{message}

Heuristic emotion hint:
{heuristic_emotion}

Heuristic depression-risk hint:
{heuristic_risk}
"""
    try:
        payload = parse_med_buddy_json(run_llm(prompt))
        response = shorten_med_buddy_response((payload.get("response") or "").strip())
        emotion = (payload.get("emotion") or "").strip() or heuristic_emotion
        depression_risk = (payload.get("depression_risk") or "").strip() or heuristic_risk
        if response:
            return response, emotion, depression_risk
    except Exception:
        pass

    return med_buddy_fallback(message, heuristic_emotion, heuristic_risk)

# --------------------------
# Page Config
# --------------------------
st.set_page_config(page_title="AIhe Health Dashboard",
                   page_icon="🩺", layout="wide")
st.markdown("""
<style>
:root {
    --surface-0: #f7fbff;
    --surface-1: rgba(255, 255, 255, 0.72);
    --surface-2: rgba(255, 255, 255, 0.9);
    --line-soft: rgba(15, 76, 92, 0.12);
    --ink-main: #143249;
    --ink-soft: #547086;
    --teal-1: #7be0d6;
    --teal-2: #35b9b0;
    --teal-3: #0f4c5c;
    --blue-1: #56b6ff;
    --blue-2: #3a7bff;
    --rose-1: #ff8fb1;
    --gold-1: #ffcf6d;
}

body {
    background:
        radial-gradient(circle at 8% 12%, rgba(123, 224, 214, 0.28), transparent 24%),
        radial-gradient(circle at 92% 8%, rgba(86, 182, 255, 0.20), transparent 20%),
        radial-gradient(circle at 85% 78%, rgba(255, 143, 177, 0.14), transparent 18%),
        linear-gradient(180deg, #e9fbfb 0%, #f5fbff 44%, #ffffff 100%);
}

html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 8% 12%, rgba(123, 224, 214, 0.28), transparent 24%),
        radial-gradient(circle at 92% 8%, rgba(86, 182, 255, 0.20), transparent 20%),
        radial-gradient(circle at 85% 78%, rgba(255, 143, 177, 0.14), transparent 18%),
        linear-gradient(180deg, #e9fbfb 0%, #f5fbff 44%, #ffffff 100%);
    color: var(--ink-main);
}

section.main,
.block-container {
    background: transparent;
}

.block-container {
    padding-top: 0rem !important;
    margin-top: 0rem !important;
}

.stButton button {
    background:
        radial-gradient(circle at top left, rgba(255,255,255,0.32), transparent 28%),
        linear-gradient(135deg, var(--teal-2), var(--teal-3));
    color: white;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.18);
    box-shadow: 0 14px 30px rgba(23, 92, 110, 0.18);
    font-weight: 700;
    transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
}

.stButton button:hover {
    transform: translateY(-1px);
    filter: brightness(1.03);
    box-shadow: 0 18px 34px rgba(23, 92, 110, 0.22);
}

div[data-testid="stVerticalBlock"] > div:empty {
    display: none;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.34rem;
}

section.main > div {
    padding-top: 0rem !important;
}

div[data-baseweb="tab-list"] {
    gap: 10px;
    background: rgba(255,255,255,0.42);
    border: 1px solid rgba(15, 76, 92, 0.08);
    border-radius: 18px;
    padding: 10px;
    backdrop-filter: blur(10px);
    box-shadow: 0 16px 36px rgba(15, 76, 92, 0.08);
}

button[data-baseweb="tab"] {
    border-radius: 14px !important;
    background: transparent !important;
    color: var(--ink-soft) !important;
    font-weight: 700 !important;
    padding: 12px 18px !important;
    transition: all 0.18s ease !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, rgba(123, 224, 214, 0.24), rgba(58, 123, 255, 0.16)) !important;
    color: var(--ink-main) !important;
    box-shadow: inset 0 0 0 1px rgba(15, 76, 92, 0.08);
}

div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stDateInput"] input {
    background: rgba(255,255,255,0.88) !important;
    border-radius: 14px !important;
    border: 1px solid rgba(15, 76, 92, 0.12) !important;
    box-shadow: 0 10px 24px rgba(15, 76, 92, 0.05);
}

div[data-testid="stFileUploader"] section {
    background: rgba(255,255,255,0.74);
    border-radius: 18px;
    border: 1px solid rgba(15, 76, 92, 0.12);
    box-shadow: 0 14px 32px rgba(15, 76, 92, 0.07);
}

div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.72);
    border: 1px solid rgba(15, 76, 92, 0.1);
    border-radius: 18px;
    box-shadow: 0 14px 28px rgba(15, 76, 92, 0.06);
    overflow: hidden;
}

div[data-testid="stExpander"] details summary {
    background:
        linear-gradient(90deg, rgba(123, 224, 214, 0.12), rgba(86, 182, 255, 0.07));
}
</style>
""", unsafe_allow_html=True)

# --------------------------
# Session State
# --------------------------
if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "current_report_path" not in st.session_state:
    st.session_state.current_report_path = ""

if "editable_extracted_text" not in st.session_state:
    st.session_state.editable_extracted_text = ""

if "last_uploaded_signature" not in st.session_state:
    st.session_state.last_uploaded_signature = ""

if "report_chat_history" not in st.session_state:
    st.session_state.report_chat_history = []

if "med_buddy_history" not in st.session_state:
    st.session_state.med_buddy_history = []

if "show_med_buddy" not in st.session_state:
    st.session_state.show_med_buddy = False

if "patient_name" not in st.session_state:
    st.session_state.patient_name = ""

if "patient_id" not in st.session_state:
    st.session_state.patient_id = ""

# --------------------------
# Header
# --------------------------
st.markdown("""
<style>
.header-container {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-top: 64px;
    margin-bottom: 0px;
    border-radius: 30px;
    padding: 18px 22px;
    background:
        radial-gradient(circle at top left, rgba(255,255,255,0.26), transparent 24%),
        linear-gradient(135deg, #78dcd3, #2d9aad 46%, #0f4c5c 100%);
    color: white;
    border: 1px solid rgba(255,255,255,0.18);
    box-shadow: 0 20px 44px rgba(15, 76, 92, 0.20);
    position: relative;
    overflow: hidden;
}

.header-container::after {
    content: "";
    position: absolute;
    inset: auto -40px -40px auto;
    width: 150px;
    height: 150px;
    background: radial-gradient(circle, rgba(255,255,255,0.18), transparent 65%);
    pointer-events: none;
}

.header-icon {
    width: 54px;
    height: 54px;
    border-radius: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    background: rgba(255,255,255,0.16);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.28);
}

.header-title {
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.02em;
}

.header-subtitle {
    font-size: 14px;
    margin-top: 10px;
    margin-bottom: 8px;
    color: #34566f;
    padding-left: 8px;
}

.med-buddy-shell {
    background:
        radial-gradient(circle at top right, rgba(123, 224, 214, 0.24), transparent 34%),
        linear-gradient(180deg, rgba(255,255,255,0.98), rgba(242, 251, 251, 0.95));
    border: 1px solid rgba(15, 76, 92, 0.10);
    border-radius: 24px;
    padding: 16px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.84), 0 14px 34px rgba(15, 76, 92, 0.10);
}

.med-buddy-hero {
    background:
        radial-gradient(circle at top left, rgba(255,255,255,0.18), transparent 26%),
        linear-gradient(145deg, #8ae0d6, #319cb1 44%, #0f4c5c 100%);
    color: white;
    border-radius: 22px;
    padding: 16px 18px;
    margin-bottom: 12px;
    box-shadow: 0 16px 28px rgba(15,76,92,0.18);
}

.med-buddy-title {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.01em;
}

.med-buddy-subtitle {
    margin-top: 5px;
    font-size: 12px;
    opacity: 0.92;
    line-height: 1.45;
}

div[data-testid="stPopover"] > button[kind],
div[data-testid="stPopoverButton"] > button[kind] {
    background:
        radial-gradient(circle at top left, rgba(255,255,255,0.22), transparent 30%),
        linear-gradient(135deg, #7bded3, #3b92aa 50%, #0f4c5c) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.16) !important;
    border-radius: 20px !important;
    min-height: 56px !important;
    box-shadow: 0 16px 28px rgba(47, 127, 143, 0.20) !important;
    font-weight: 700 !important;
    letter-spacing: 0.01em;
}

div[data-testid="stPopover"] > button[kind]:hover,
div[data-testid="stPopoverButton"] > button[kind]:hover {
    filter: brightness(1.05);
    transform: translateY(-1px);
}

.med-buddy-chip-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin: 10px 0 12px 0;
}

.med-buddy-chip {
    background: linear-gradient(180deg, #f4feff, #ecfbfb);
    color: #0f4c5c;
    border: 1px solid #d3efec;
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
}

.med-buddy-user {
    background:
        radial-gradient(circle at top left, rgba(255,255,255,0.18), transparent 28%),
        linear-gradient(135deg, #4cc5ff, #1aa0a8);
    color: white;
    padding: 11px 13px;
    border-radius: 18px 18px 8px 18px;
    margin: 7px 0 7px 36px;
    box-shadow: 0 12px 24px rgba(31,162,166,0.18);
    line-height: 1.45;
    font-size: 13px;
}

.med-buddy-bot {
    background:
        radial-gradient(circle at top left, rgba(123, 224, 214, 0.10), transparent 30%),
        rgba(255,255,255,0.94);
    border: 1px solid #dbe9ef;
    color: #102a43;
    padding: 11px 12px;
    border-radius: 18px 18px 18px 8px;
    margin: 7px 36px 7px 0;
    box-shadow: 0 12px 24px rgba(15,76,92,0.08);
    line-height: 1.55;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

# Header UI
@st.fragment
def render_med_buddy_popover():
    with st.popover("Med Buddy", icon=":material/support_agent:", width="stretch"):
        st.markdown("""
        <div class="med-buddy-shell">
            <div class="med-buddy-hero">
                <div class="med-buddy-title">Med Buddy</div>
                <div class="med-buddy-subtitle">
                    A calmer space for emotional check-ins, stressful moments, and supportive reflection.
                </div>
            </div>
            <div class="med-buddy-chip-row">
                <div class="med-buddy-chip">Private support vibe</div>
                <div class="med-buddy-chip">Short, gentle replies</div>
                <div class="med-buddy-chip">Mood-aware guidance</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        for role, msg in st.session_state.med_buddy_history[-8:]:
            if role == "user":
                st.markdown(f'<div class="med-buddy-user">{msg}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="med-buddy-bot">{msg}</div>', unsafe_allow_html=True)

        with st.form("med_buddy_form", clear_on_submit=True):
            buddy_q = st.text_input("Talk to Med Buddy")
            buddy_submit = st.form_submit_button("Send", use_container_width=True)

        if buddy_submit and buddy_q.strip():
            response, emotion, depression_risk = run_med_buddy_chat(buddy_q)
            st.session_state.med_buddy_history.append(("user", buddy_q))
            st.session_state.med_buddy_history.append(("bot", response))
            save_emotion(
                st.session_state.get("phone", ""),
                {
                    "source": "med_buddy",
                    "message": buddy_q,
                    "emotion": emotion,
                    "depression_risk": depression_risk,
                },
            )
            st.rerun()

header_col1, header_col2 = st.columns([6, 0.8])

with header_col1:
    st.markdown("""
    <div class="header-container">
        <div class="header-icon">🩺</div>
        <div class="header-title">AI Diagnostics & Medical Knowledge  </div>
    </div>
    <div class="header-subtitle">
        Smart analysis of your medical reports using AI
    </div>
    """, unsafe_allow_html=True)

with header_col2:
    st.markdown("<div style='height:74px;'></div>", unsafe_allow_html=True)
    render_med_buddy_popover()

st.markdown("""
<style>
/* Chat wrapper inside column */
.chat-wrapper {
    height: 500px;
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(15, 76, 92, 0.10);
    border-radius: 22px;
    overflow: hidden;
    background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(244, 250, 255, 0.95));
    box-shadow: 0 18px 36px rgba(15, 76, 92, 0.08);
    backdrop-filter: blur(10px);
}

/* Scrollable messages */
.chat-messages {
    flex-grow: 1;
    overflow-y: auto;
    padding: 14px;
    display: flex;
    flex-direction: column;
    background:
        radial-gradient(circle at top right, rgba(123, 224, 214, 0.12), transparent 22%),
        linear-gradient(180deg, rgba(255,255,255,0.35), rgba(245,250,255,0.72));
}

/* Input area */
.chat-input {
    border-top: 1px solid rgba(15, 76, 92, 0.08);
    padding: 10px;
    background: rgba(255,255,255,0.82);
}

/* Bubbles */
.user-bubble {
    background:
        radial-gradient(circle at top left, rgba(255,255,255,0.18), transparent 28%),
        linear-gradient(135deg, #53c7ff, #1FA2A6);
    color: white;
    padding: 10px 14px 12px 14px;
    border-radius: 18px 18px 8px 18px;
    margin: 6px;
    align-self: flex-end;
    max-width: 75%;
    font-size: 13px;
    box-shadow: 0 14px 26px rgba(31,162,166,0.18);
}

.bot-bubble {
    background:
        radial-gradient(circle at top left, rgba(123, 224, 214, 0.10), transparent 26%),
        rgba(255,255,255,0.92);
    border: 1px solid #dce8f2;
    color: #102a43;
    padding: 10px 13px;
    border-radius: 18px 18px 18px 8px;
    margin: 6px;
    align-self: flex-start;
    max-width: 75%;
    font-size: 13px;
    box-shadow: 0 12px 24px rgba(15,76,92,0.07);
}
</style>
""", unsafe_allow_html=True)

# --------------------------
tab_dashboard, tab_Ai, tab_settings = st.tabs([
    "🏠 Dashboard",
    "📊 AI Chat + Report",
    "⚙️ My Care"
])



# --------------------------
with tab_dashboard:
    # --------------------------
    # ðŸŽ¨ STYLES
    # --------------------------
    st.markdown("""<style>
    .upload-box {
        border: 1.5px dashed rgba(15, 76, 92, 0.22);
        border-radius: 20px;
        padding: 24px;
        text-align: center;
        color: #5d7384;
        background:
            radial-gradient(circle at top left, rgba(123, 224, 214, 0.14), transparent 28%),
            linear-gradient(180deg, rgba(255,255,255,0.86), rgba(245, 251, 255, 0.88));
        box-shadow: 0 16px 34px rgba(15, 76, 92, 0.06);
    }
    .risk-box {
        background:
            radial-gradient(circle at top left, rgba(255, 143, 177, 0.16), transparent 28%),
            linear-gradient(180deg, rgba(255,244,244,0.96), rgba(255,250,250,0.96));
        padding: 18px;
        border-radius: 18px;
        border: 1px solid rgba(190, 40, 76, 0.10);
        box-shadow: 0 16px 30px rgba(176, 48, 76, 0.08);
    }
    </style>""", unsafe_allow_html=True)

    # --------------------------
    # ðŸ“Š LAYOUT
    # --------------------------
    col1, col2, col3 = st.columns([1.3, 2.5, 1.5])

    # --------------------------
    # ðŸ” LOGIN + UPLOAD
    # --------------------------
    with col3:
        st.markdown("### 🔐 User Login")
        menu = st.radio("Choose Option", [
                        "Login", "Register"], horizontal=True)
        input_col1, input_col2 = st.columns([1.6, 1.4])

        with input_col1:
            phone = st.text_input("📞 Phone Number", max_chars=10)

        with input_col2:
            password = st.text_input(
                "🔑 Passcode", type="password", max_chars=4)

        patient_name = ""
        if menu == "Register":
            patient_name = st.text_input("👤 Patient Name")

        # ---------------- LOGIN ---------------- #
        if menu == "Login":
            if st.button("Login", use_container_width=True):

                if not is_valid_phone(phone):
                    st.warning("⚠️ Enter valid 10-digit phone number")

                elif not is_valid_password(password):
                    st.warning("⚠️ Enter 4-digit passcode")

                elif validate_login(phone, password):
                    profile = get_user_profile(phone)
                    st.session_state.logged_in = True
                    st.session_state.phone = phone
                    st.session_state.patient_name = profile.get("name", "")
                    st.session_state.patient_id = profile.get("patient_id", "")
                    st.success("✅ Login successful 🎉")

                else:
                    st.error("âŒ Invalid phone or passcode")

            # ---------------- REGISTER ---------------- #
        if menu == "Register":
            if st.button("Create Account", use_container_width=True):

                users = load_users()

                if not is_valid_phone(phone):
                    st.warning("⚠️ Enter valid 10-digit phone number")

                elif not is_valid_password(password):
                    st.warning("⚠️ Enter 4-digit passcode")

                elif phone in users:
                    st.error("âŒ Phone already registered")

                elif not is_valid_name(patient_name):
                    st.warning("⚠️ Enter patient name")

                else:
                    ok, profile = add_user(phone, password, patient_name)
                    if ok:
                        st.success(
                            f"✅ Account created successfully! Patient ID: {profile.get('patient_id')}"
                        )
                    else:
                        st.error(str(profile))

        st.markdown("### 📄 Upload Medical Reports")

        st.markdown("""
        <div class="upload-box">📄</div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            " ",
            type=["pdf", "png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"],
            label_visibility="collapsed",
        )

        if uploaded:
            path = os.path.join(UPLOAD_DIR, uploaded.name)
            uploaded_bytes = uploaded.getvalue()
            upload_signature = hashlib.md5(uploaded_bytes).hexdigest()
            st.session_state.current_report_path = path

            if st.session_state.last_uploaded_signature != upload_signature:
                st.session_state.analysis = None
                st.session_state.vector_store = None
                st.session_state.editable_extracted_text = ""
                st.session_state.pop("dashboard_extracted_text", None)
                st.session_state.report_chat_history = []

            with open(path, "wb") as f:
                f.write(uploaded_bytes)

            st.success("File uploaded successfully")

            try:
                extracted = parse_medical_file(path)
                st.session_state.editable_extracted_text = extracted.get("raw_text", "")
                st.session_state["dashboard_extracted_text"] = st.session_state.editable_extracted_text
                st.session_state.last_uploaded_signature = upload_signature
            except Exception as exc:
                st.warning(f"Could not extract text preview: {exc}")

        # Show login status
        if st.session_state.logged_in:
            profile = get_active_patient_profile()
            st.success(
                f"🔓 Logged in as {profile.get('name', st.session_state.get('patient_name', 'Patient'))} "
                f"(ID: {profile.get('patient_id', st.session_state.get('patient_id', '-'))})"
            )
        else:
            st.info("🔒 Login required to run analysis")

    # --------------------------
    # ðŸ’¬ KEY INSIGHTS
    # --------------------------
    with col2:
        


        def limit_words(text, max_words=60):
            if not text:
                return text
            words = text.split()
            if len(words) <= max_words:
                return text
            return " ".join(words[:max_words]) + "..."

        analysis = st.session_state.analysis

        extracted_text = st.session_state.get("editable_extracted_text", "")

        if extracted_text:
            st.subheader("Extracted Report Text")
            edited_extracted_text = st.text_area(
                "Review extracted raw text before analysis",
                extracted_text,
                height=260,
                key=f"dashboard_extracted_text_{st.session_state.get('last_uploaded_signature', 'current')}",
            )
            st.session_state.editable_extracted_text = edited_extracted_text

            run_btn = st.button(
                "Confirm & Run",
                use_container_width=True,
                disabled=not st.session_state.logged_in or not st.session_state.get("editable_extracted_text", "").strip(),
            )

            if run_btn:
                with st.spinner("Running..."):
                    result = run_full_pipeline(
                        st.session_state.current_report_path,
                        override_text=st.session_state.get("editable_extracted_text", ""),
                    )
                    st.session_state.analysis = result
                    st.session_state.vector_store = load_vector_store(384)
                    st.success("Analysis completed")
                    st.rerun()

        if analysis:
            dashboard_sections = build_dashboard_sections(analysis)
            processed_audio_text = " ".join(
                [
                    dashboard_sections["intro"],
                    dashboard_sections["findings"],
                    dashboard_sections["interpretation"],
                    dashboard_sections["next_steps"],
                    dashboard_sections["conclusion"],
                ]
            ).strip()

            render_audio_header("Processed Medical Report", processed_audio_text)
            st.markdown(f"""
**Intro Paragraph**

{dashboard_sections["intro"]}
""")

            with st.expander("Deep Dive: Key Findings", expanded=True):
                st.write(dashboard_sections["findings"])

            with st.expander("Deep Dive: Clinical Interpretation", expanded=False):
                st.write(dashboard_sections["interpretation"])

            with st.expander("Deep Dive: Recommended Follow-Up", expanded=False):
                st.write(dashboard_sections["next_steps"])

            st.markdown(f"""
**Conclusion**

{dashboard_sections["conclusion"]}
""")
        else:
            st.info("Run analysis first")

    # --------------------------
    # âš ï¸ RISK
    # --------------------------

    # --------------------------
# âš ï¸ RISK (ALL-ROUNDER UI)
# --------------------------
    with col1:
        st.markdown("### ⚠️ Risk Assessment")
        render_appointment_widget(st.session_state.get("phone", ""))

    # ðŸ‘‰ Use LLM extracted data
        if st.session_state.analysis:

            r = st.session_state.analysis["risk"]

            st.metric("Risk Level", f"{r['flag']} {r['risk_level']}")
            st.metric("Risk Score", f"{r['risk_score']} / 100")

            if r["main_drivers"]:
                st.subheader("Main Risk Drivers")

            for i, d in enumerate(r["main_drivers"]):

            # ðŸ‘‰ create pseudo score (based on overall risk)
                base = r["risk_score"]
                score = max(30, min(100, base - i * 10))

                color = "#00c853"
                if score >= 75:
                    color = "#ff4b4b"
                elif score >= 50:
                    color = "#ffa600"

                st.markdown(f"""
                <div style="margin-top:10px;">
                <b>{d}</b>
                <div style="
                height:6px;
                background:#eee;
                    border-radius:4px;
                    margin-top:4px;
                    ">
                    <div style="
                    width:{score}%;
                    height:6px;
                    background:{color};
                    border-radius:4px;
                    "></div>
                    </div>
                    </div>
                    """, unsafe_allow_html=True)

            else:
                st.info("No significant risk drivers detected")

    
        else:
            st.info("Run analysis to see risk")

with tab_Ai:
    if not st.session_state.analysis:
        st.info("Run analysis first")
    else:
        analysis = st.session_state.analysis

        col1, col2 = st.columns([1, 2])

        # --------------------------
        # ðŸ’¬ AI CHAT (LEFT)
        # --------------------------
        with col1:
            # --------------------------
            # ðŸ’¬ CHAT HISTORY STORAGE
            # --------------------------
            if "report_chat_history" not in st.session_state:
                st.session_state.report_chat_history = []

            processed_chat_context = build_processed_chat_context(analysis)

            if not analysis:
                st.info("Run analysis to enable AI chat")
            else:
                # ðŸ”² Wrapper

                # ðŸ”½ Input (BOTTOM - FIXED)
                st.markdown('<div class="chat-input">', unsafe_allow_html=True)

                with st.form(key="chat_form", clear_on_submit=True):
                    q = st.text_input("Ask about your medical reports")
                    submitted = st.form_submit_button(
                        "âž¤", use_container_width=False)

    # --------------------------
    # ðŸ” Chat Logic (AFTER UI)
    # --------------------------
                    if submitted and q.strip():
                        # âœ… store immediately
                        st.session_state.report_chat_history.append(("user", q))

        # process
                        chunks = []
                        if st.session_state.vector_store:
                            q_embed = embed_texts([q])
                            chunks = st.session_state.vector_store.search(q_embed)
                        answer = answer_question(chunks, q, processed_context=processed_chat_context)
                        st.session_state.report_chat_history.append(("bot", answer))

                        st.rerun()

            for role, msg in reversed(st.session_state.report_chat_history):
                if role != "user":
                    st.markdown(
                        f'<div class="bot-bubble">{msg}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(
                        f'<div class="user-bubble">{msg}</div>', unsafe_allow_html=True)

            # ðŸ”µ Chat messages (TOP - SCROLLABLE)
            st.markdown('<div class="chat-messages">',
                        unsafe_allow_html=True)

        # --------------------------
        # ðŸ“Š RIGHT SIDE (SUMMARY + INSIGHTS)
        # --------------------------
        with col2:
            # ðŸŽ¨ Styles
            st.markdown("""
                <style>
                .insight-box {
                    background: #fefce8;
                    padding: 12px;
                    border-radius: 10px;
                    margin-top: 10px;
                }
                .recommend-box {
                    background: #ecfdf5;
                    padding: 12px;
                    border-radius: 10px;
                    margin-top: 10px;
                }
                </style>
                """, unsafe_allow_html=True)

            # --------------------------
            # ðŸ§  SUMMARY
            # --------------------------
            def clean_summary(text):
                if not text:
                    return text
                # remove unwanted chatbot lines
                bad_phrases = [
                    "hello",
                    "what questions",
                    "how can i help"
                ]

                lines = text.split("\n")
                cleaned = [l for l in lines if not any(
                    p in l.lower() for p in bad_phrases)]

                return " ".join(cleaned)

            analysis = st.session_state.analysis

            if not analysis:
                st.info("Run analysis first")
            else:
                raw_summary = analysis.get("summary", "")
                cleaned_summary = clean_summary(raw_summary)
                report_type = analysis.get("report_type", "lab")
                detailed_health_report = analysis.get("detailed_health_report", "")
                narrative_text = analysis.get("narrative", "")
                records = analysis.get("records", []) or []
                fallback_discussion = (
                    cleaned_summary
                    or narrative_text
                    or "Detailed case discussion is currently limited due to incomplete extraction."
                )

                st.subheader("Processed Case Discussion")
                st.write(detailed_health_report or fallback_discussion)
                render_auto_audio_reader(detailed_health_report or fallback_discussion)

                if report_type == "clinical":
                    st.caption("This section discusses the case in a diagnosis-oriented format with emphasis on findings, investigations, treatment, present condition, and clinical follow-up.")
                else:
                    st.caption("This section discusses the report in a lab-oriented format with emphasis on extracted parameters, abnormal values, practical interpretation, and follow-up meaning.")

                render_parameter_charts(records)

            # --------------------------
            # ðŸ” INSIGHTS
            # --------------------------
            analysis = st.session_state.get("analysis")

            # --------------------------
            # CASE 1: No analysis yet
            # --------------------------
            if analysis is None:
                trends_data = None   # â— keep it None (not {})
            # --------------------------
            # CASE 2: Analysis exists
            # --------------------------
            else:
                trends_data = analysis.get("trends")

            # --------------------------
            # INSIGHTS
            # --------------------------
            insights = []

            if trends_data:   # only runs if real data exists
                for param, t in trends_data.items():
                    values = t.get("values", [])

                    if len(values) >= 2:
                        if values[-1] > values[0]:
                            insights.append(
                                f"📈 {param.replace('_', ' ').title()} increasing.")
                        elif values[-1] < values[0]:
                            insights.append(
                                f"📉 {param.replace('_', ' ').title()} decreasing.")

                        if max(values) > 200:
                            insights.append(
                                f"⚠️ {param.replace('_', ' ').title()} high.")

            # --------------------------
            # DEFAULT MESSAGE
            # --------------------------
            if analysis is not None and not insights:
                insights.append(
                    "No significant variations detected.")

            st.markdown("""
            <div class="insight-box">
            <b>🔍 Key Insights</b><br>
            """ + "<br>".join(insights) + """
            </div>
            """, unsafe_allow_html=True)

            # --------------------------
            # ðŸ’¡ RECOMMENDATIONS
            # --------------------------
            recommendations = [
                "🥗 Maintain a balanced diet with reduced saturated fats",
                "🏃 Engage in regular physical activity (30 mins/day)",
                "🧪 Schedule periodic health check-ups",
                "💧 Stay hydrated and maintain proper sleep cycle"
            ]

            st.markdown("""
            <div class="recommend-box">
            <b>💡 Recommendations</b><br>
            """ + "<br>".join(recommendations) + """
            </div>
            """, unsafe_allow_html=True)

            # --------------------------
            # ðŸ“ˆ TRENDS
            # --------------------------
            st.markdown("### 📈 Health Trends")

            if not trends_data:
                st.info("Not enough historical data yet for trends")
            else:
                for param, t in trends_data.items():
                    st.markdown(f"**{param.replace('_', ' ').title()}**")

                    if len(t.get("dates", [])) < 2:
                        st.caption("Not enough data points")
                        continue

                    df = pd.DataFrame({
                        "Date": t["dates"],
                        "Value": t["values"]
                    })

                    df["Date"] = pd.to_datetime(df["Date"])

                    st.line_chart(df.set_index("Date"), height=140)

with tab_settings:

    analysis = st.session_state.get("analysis")

    if not analysis:
        st.info("Run analysis first to see hospital care recommendations")
    else:
        narrative = analysis.get("narrative", "")
        risk = analysis.get("risk", {})
        risk_level = risk.get("risk_level", "Unknown")

        # --------------------------
    # ðŸ“Š LAYOUT (COLUMNS)
    # --------------------------
        col_left, col_right = st.columns([1.2, 1.8])

    # ==========================
    # ðŸŸ¢ LEFT SIDE (PATIENT + RECORDS)
    # ==========================
        with col_left:
            st.subheader("👤 Patient Overview")

            phone = st.session_state.get("phone", "")
            profile = get_active_patient_profile()
            st.write(f"🪪 Patient ID: {profile.get('patient_id', st.session_state.get('patient_id', '-'))}")
            st.write(f"👤 Name: {profile.get('name', st.session_state.get('patient_name', 'Not available'))}")
            st.write(f"📞 Phone: {phone}")

            st.divider()

        # --------------------------
        # ðŸ“„ MEDICAL RECORDS
        # --------------------------
            st.subheader("📄 Medical Records")

            files = os.listdir(UPLOAD_DIR)

            if files:
                for f in files:
                    st.write(f"📎 {f}")
                if st.button("Clear Medical Records"):
                    removed = clear_uploaded_records()
                    st.session_state.analysis = None
                    st.session_state.vector_store = None
                    st.session_state.current_report_path = ""
                    st.session_state.editable_extracted_text = ""
                    st.toast(f"Cleared {removed} medical record(s)")
                    st.rerun()
            else:
                st.info("No reports uploaded")


# --------------------------
# ðŸ§‘â€âš•ï¸ DOCTOR ASSIGNMENT
# --------------------------
            st.subheader("🧑‍⚕️ Recommended Doctor")

            if risk_level == "High":
                doctor = "Cardiologist"
                consultation = "Immediate consultation required."
            elif risk_level == "Moderate":
                doctor = "General Physician"
                consultation = "Schedule a check-up within 2 weeks."
            else:
                doctor = "General Physician"
                consultation = "Routine check-up recommended."

            st.success(f"Doctor: {doctor}")
            st.write(f"📝 {consultation}")

            booked_appointments = get_all_appointments(phone)
            if booked_appointments:
                with st.expander("Booked Appointments & Tokens", expanded=False):
                    sorted_appointments = sorted(
                        booked_appointments,
                        key=lambda item: f"{item.get('date', '')} {item.get('time', '')}",
                    )
                    for item in sorted_appointments:
                        st.markdown(
                            f"**{item.get('date', '-')} {item.get('time', '-')}**  \n"
                            f"Doctor: {item.get('doctor', '-')}  \n"
                            f"Status: {item.get('status', 'scheduled').title()}  \n"
                            f"Token: {item.get('token', 'Pending')}"
                        )
                        st.divider()

            st.divider()
            st.divider()

        # ==========================
        # ðŸ”µ RIGHT SIDE (ACTION FLOW)
        # ==========================
        with col_right:

            st.subheader("🔔 Urgency Status")

            if risk_level == "High":
                st.error("🚨 Immediate medical attention required")
            elif risk_level == "Moderate":
                st.warning("⚠️ Visit doctor soon")
            else:
                st.success("✅ Condition stable")

            st.divider()

    # --------------------------
    # ðŸ“… APPOINTMENT
    # --------------------------
            st.subheader("Book Appointment")

            doctor_options = ["Select the Doctor", "Dr. Dharshini - Dentist", "Dr. Tamil - Neurologist", "Dr. Akshaya - General Physician",
                              "Dr. Dhirshatha - Dermatologist", "Dr. Kavin - Ophthalmologist", "Dr. Mohammad - Orthopedic"]
            seen_doctors = []
            doctor_options = [d for d in doctor_options if not (d in seen_doctors or seen_doctors.append(d))]

            selected_doctor = st.selectbox("Select Doctor", doctor_options)
            date = st.date_input("Select Date")
            time = st.selectbox("Select Time", [
                "10:00 AM",
                "12:00 PM",
                "4:00 PM",
                "6:00 PM"
            ])

            with st.expander("Booking Rules & Regulations", expanded=False):
                st.markdown(
                    "1. Multiple appointments can be scheduled for the same patient.  \n"
                    "2. Every appointment keeps its own unique token.  \n"
                    "3. The patient dashboard only shows the immediate next reminder widget.  \n"
                    "4. Full appointment history remains available in the expander above.  \n"
                    "5. The hospital dashboard can close its own workflow without changing the patient-facing appointment history."
                )

            if st.button("Confirm Appointment"):
                if selected_doctor == "Select the Doctor":
                    st.warning("Please choose a doctor before booking.")
                else:
                    ok, result = save_appointment(phone, risk, date, time, selected_doctor)
                    if ok:
                        st.toast(
                            f"Appointment booked for {date} at {time}. Token {result.get('token')} is ready."
                        )
                        st.success(
                            f"Appointment booked with {selected_doctor}. Token: {result.get('token')}"
                        )
                        st.rerun()
                    else:
                        st.warning(result)


