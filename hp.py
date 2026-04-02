from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from db import (
    load_all,
    load_all_emotions,
    update_hospital_appointment_status,
)
from login import get_user_profile


st.set_page_config(page_title="Hospital Dashboard", layout="wide")

st.markdown(
    """
<style>
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top left, rgba(77, 182, 172, 0.16), transparent 28%),
        linear-gradient(135deg, #edf6f7 0%, #e6eef8 52%, #f7fbff 100%);
}

.block-container {
    padding-top: 2.2rem !important;
    padding-bottom: 2rem !important;
}

.hero-card {
    background: linear-gradient(135deg, #0e5b6f 0%, #2ea4a4 52%, #8bd7d0 100%);
    color: white;
    border-radius: 24px;
    padding: 1.6rem 1.8rem;
    box-shadow: 0 18px 50px rgba(16, 71, 85, 0.18);
    margin-bottom: 1.2rem;
}

.hero-title {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin-bottom: 0.35rem;
}

.hero-subtitle {
    font-size: 1rem;
    opacity: 0.92;
    max-width: 900px;
    line-height: 1.55;
}

.glass-card {
    background: rgba(255, 255, 255, 0.82);
    border: 1px solid rgba(16, 71, 85, 0.09);
    border-radius: 22px;
    padding: 1rem 1.1rem;
    box-shadow: 0 16px 40px rgba(30, 42, 56, 0.08);
}

.metric-card {
    border-radius: 20px;
    padding: 1rem 1.1rem;
    min-height: 124px;
    color: white;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 16px 34px rgba(30, 42, 56, 0.12);
}

.metric-label {
    font-size: 0.88rem;
    opacity: 0.9;
}

.metric-value {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1;
    margin: 0.55rem 0;
}

.metric-note {
    font-size: 0.82rem;
    opacity: 0.86;
    line-height: 1.4;
}

.metric-teal { background: linear-gradient(135deg, #0f5c74, #2ca9a5); }
.metric-red { background: linear-gradient(135deg, #b4375d, #ef6c72); }
.metric-amber { background: linear-gradient(135deg, #ae6a16, #f0a53f); }
.metric-blue { background: linear-gradient(135deg, #295a9b, #3f8cff); }
.metric-violet { background: linear-gradient(135deg, #5f46a3, #8f72ff); }

.section-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #17324d;
    margin-bottom: 0.85rem;
}

.queue-card {
    background: rgba(255, 255, 255, 0.9);
    border: 1px solid rgba(17, 54, 75, 0.08);
    border-radius: 20px;
    padding: 1rem 1rem 0.9rem;
    margin-bottom: 0.85rem;
    box-shadow: 0 12px 28px rgba(30, 42, 56, 0.07);
}

.queue-top {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 0.8rem;
}

.patient-id {
    font-size: 1.02rem;
    font-weight: 800;
    color: #17324d;
}

.patient-meta {
    color: #5d6b7a;
    font-size: 0.88rem;
}

.chip-row {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.chip {
    border-radius: 999px;
    padding: 0.28rem 0.7rem;
    font-size: 0.8rem;
    font-weight: 700;
    border: 1px solid transparent;
}

.chip-high {
    background: rgba(215, 63, 84, 0.12);
    color: #b51f46;
    border-color: rgba(181, 31, 70, 0.18);
}

.chip-moderate {
    background: rgba(240, 165, 63, 0.15);
    color: #995800;
    border-color: rgba(153, 88, 0, 0.18);
}

.chip-low {
    background: rgba(55, 179, 126, 0.12);
    color: #1c7c53;
    border-color: rgba(28, 124, 83, 0.18);
}

.chip-neutral {
    background: rgba(64, 119, 193, 0.1);
    color: #295a9b;
    border-color: rgba(41, 90, 155, 0.16);
}

.queue-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.8rem;
}

.queue-stat {
    background: #f5fafc;
    border-radius: 16px;
    padding: 0.8rem 0.85rem;
}

.queue-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6c7a89;
    margin-bottom: 0.22rem;
}

.queue-value {
    font-size: 0.96rem;
    font-weight: 700;
    color: #17324d;
}

.tiny-note {
    color: #6b7886;
    font-size: 0.86rem;
    line-height: 1.5;
}

@media (max-width: 960px) {
    .queue-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
</style>
""",
    unsafe_allow_html=True,
)


def parse_dt(date_str, time_str):
    if not date_str:
        return None

    combined = f"{date_str} {time_str or ''}".strip()
    formats = [
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y %I:%M %p",
        "%d-%m-%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(combined, fmt)
        except ValueError:
            continue
    return None


def normalize_appointments(details):
    appointments = []

    for item in details.get("appointments", []):
        if isinstance(item, dict):
            appointments.append(dict(item))

    legacy = details.get("appointment")
    if isinstance(legacy, dict) and legacy:
        legacy_token = legacy.get("token", details.get("token"))
        legacy_status = legacy.get("status", details.get("status", "waiting"))
        legacy_doctor = legacy.get(
            "doctor", details.get("doctor", "Doctor not assigned"))
        normalized_legacy = {
            "date": legacy.get("date", ""),
            "time": legacy.get("time", ""),
            "doctor": legacy_doctor,
            "status": legacy_status,
            "token": legacy_token,
        }
        signature = (
            normalized_legacy["date"],
            normalized_legacy["time"],
            normalized_legacy["doctor"],
            str(normalized_legacy["token"]),
        )
        existing_signatures = {
            (
                item.get("date", ""),
                item.get("time", ""),
                item.get("doctor", ""),
                str(item.get("token", "")),
            )
            for item in appointments
        }
        if signature not in existing_signatures:
            appointments.append(normalized_legacy)

    for item in appointments:
        item.setdefault("doctor", "Doctor not assigned")
        item.setdefault("status", "waiting")
        item.setdefault("hospital_status", "scheduled")
        item["dt"] = parse_dt(item.get("date", ""), item.get("time", ""))

    appointments.sort(key=lambda item: item["dt"] or datetime.max)
    return appointments


def normalize_emotion(payload):
    latest = payload.get("latest")
    if isinstance(latest, dict):
        latest_emotion = latest.get("emotion", "Unknown")
        latest_risk = latest.get("depression_risk", "Not captured")
        latest_message = latest.get("message") or latest.get(
            "mood") or "No recent support note"
        latest_time = latest.get("time", payload.get("time", "-"))
    else:
        latest_emotion = payload.get("emotion", "Unknown")
        latest_risk = payload.get("depression_risk", "Not captured")
        latest_message = payload.get("mood", "No recent support note")
        latest_time = payload.get("time", "-")

    history = []
    for item in payload.get("history", []):
        if not isinstance(item, dict):
            continue
        history.append(
            {
                "emotion": item.get("emotion", "Unknown"),
                "time": item.get("time"),
                "depression_risk": item.get("depression_risk", "Not captured"),
                "message": item.get("message") or item.get("mood") or "",
            }
        )
# hello buddy git check
    return {
        "emotion": latest_emotion,
        "depression_risk": latest_risk,
        "message": latest_message,
        "time": latest_time,
        "history": history,
    }


def risk_chip_class(level):
    if level == "High":
        return "chip-high"
    if level == "Moderate":
        return "chip-moderate"
    if level == "Low":
        return "chip-low"
    return "chip-neutral"


def emotion_score(emotion):
    mapping = {
        "Distressed": 1,
        "Concerned": 2,
        "Anxious": 2,
        "Neutral": 3,
        "Calm": 4,
        "Good Happy": 5,
        "Happy": 5,
    }
    return mapping.get(emotion, 3)


raw_data = load_all()
raw_emotions = load_all_emotions()

patients = []
for phone, details in raw_data.items():
    risk = details.get("risk", {})
    profile = get_user_profile(phone)
    appointments = normalize_appointments(details)
    active_appointments = [
        item for item in appointments if item.get("hospital_status", "scheduled") != "completed"
    ]
    next_appointment = next(
        (
            item
            for item in active_appointments
            if item.get("dt") and item["dt"] >= datetime.now()
        ),
        active_appointments[0] if active_appointments else None,
    )
    emotion_payload = normalize_emotion(raw_emotions.get(phone, {}))
    patients.append(
        {
            "phone": phone,
            "name": profile.get("name", f"Patient {phone[-4:]}"),
            "patient_id": profile.get("patient_id", "-----"),
            "risk_level": risk.get("risk_level", "Unknown"),
            "risk_score": risk.get("risk_score", 0),
            "appointments": appointments,
            "active_appointments": active_appointments,
            "next_appointment": next_appointment,
            "latest_emotion": emotion_payload["emotion"],
            "latest_depression_risk": emotion_payload["depression_risk"],
            "emotion_payload": emotion_payload,
        }
    )

visible_patients = [item for item in patients if item["active_appointments"]]

patients.sort(
    key=lambda item: (
        item["next_appointment"]["dt"] if item["next_appointment"] and item["next_appointment"]["dt"] else datetime.max,
        -item["risk_score"],
    )
)
visible_patients.sort(
    key=lambda item: (
        item["next_appointment"]["dt"] if item["next_appointment"] and item["next_appointment"]["dt"] else datetime.max,
        -item["risk_score"],
    )
)

st.markdown(
    """
<div class="hero-card">
    <div class="hero-title">Hospital Command Board</div>
    <div class="hero-subtitle">
        A live operational view of patient risk, appointment flow, doctor allocation, and emotional follow-up signals.
        
   

""",
    unsafe_allow_html=True,
)

tab1, tab2 = st.tabs(["Operations Dashboard", "Emotional Monitoring"])

with tab1:
    if not visible_patients:
        st.warning("No patient data available yet.")
    else:
        high = sum(
            1 for item in visible_patients if item["risk_level"] == "High")
        moderate = sum(
            1 for item in visible_patients if item["risk_level"] == "Moderate")
        low = sum(
            1 for item in visible_patients if item["risk_level"] == "Low")
        booked = sum(len(item["active_appointments"])
                     for item in visible_patients)
        watchlist = sum(
            1
            for item in visible_patients
            if item["latest_depression_risk"] == "High" or item["latest_emotion"] in {"Distressed", "Concerned", "Anxious"}
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(
            '<div class="metric-card metric-teal"><div class="metric-label">Registered Patients</div><div class="metric-value">{}</div><div class="metric-note">Profiles currently stored in the hospital-facing dashboard.</div></div>'.format(
                len(visible_patients)
            ),
            unsafe_allow_html=True,
        )
        c2.markdown(
            '<div class="metric-card metric-red"><div class="metric-label">High-Risk Cases</div><div class="metric-value">{}</div><div class="metric-note">Patients who may need closer clinical attention and fast follow-up.</div></div>'.format(
                high
            ),
            unsafe_allow_html=True,
        )
        c3.markdown(
            '<div class="metric-card metric-amber"><div class="metric-label">Moderate-Risk Cases</div><div class="metric-value">{}</div><div class="metric-note">Patients with meaningful findings that may need monitored review.</div></div>'.format(
                moderate
            ),
            unsafe_allow_html=True,
        )
        c4.markdown(
            '<div class="metric-card metric-blue"><div class="metric-label">Booked Appointments</div><div class="metric-value">{}</div><div class="metric-note">All appointments saved across the newer multi-booking flow.</div></div>'.format(
                booked
            ),
            unsafe_allow_html=True,
        )
        c5.markdown(
            '<div class="metric-card metric-violet"><div class="metric-label">Emotional Watchlist</div><div class="metric-value">{}</div><div class="metric-note">Patients with higher distress or concern signals from Med Buddy history.</div></div>'.format(
                watchlist
            ),
            unsafe_allow_html=True,
        )

        st.write("")
        col_left, col_right = st.columns([2.2, 1])

        with col_left:
            st.markdown(
                '<div class="section-title">Patient Queue And Appointment Reflection</div>', unsafe_allow_html=True)
            for patient in visible_patients:
                next_item = patient["next_appointment"] or {}
                risk_level = patient["risk_level"]
                risk_score = patient["risk_score"]
                appointment_count = len(patient["active_appointments"])
                token_text = next_item.get("token", "Not assigned")
                doctor_text = next_item.get("doctor", "Doctor not assigned")
                date_text = next_item.get("date", "Not scheduled")
                time_text = next_item.get("time", "Not scheduled")
                status_text = next_item.get("status", "No appointment")
                emotion_text = patient["latest_emotion"]

                st.markdown(
                    f"""
<div class="queue-card">
    <div class="queue-top">
        <div>
            <div class="patient-id">{patient["name"]} • ID {patient["patient_id"]}</div>
            <div class="patient-meta">{patient["phone"]} • Risk score {risk_score} • Latest emotional note: {emotion_text}</div>
        </div>
        <div class="chip-row">
            <span class="chip {risk_chip_class(risk_level)}">{risk_level} Risk</span>
            <span class="chip chip-neutral">{appointment_count} Appointments</span>
            <span class="chip chip-neutral">{patient["latest_depression_risk"]} Mood Watch</span>
        </div>
    </div>
    <div class="queue-grid">
        <div class="queue-stat">
            <div class="queue-label">Next Visit</div>
            <div class="queue-value">{date_text}</div>
        </div>
        <div class="queue-stat">
            <div class="queue-label">Time</div>
            <div class="queue-value">{time_text}</div>
        </div>
        <div class="queue-stat">
            <div class="queue-label">Doctor</div>
            <div class="queue-value">{doctor_text}</div>
        </div>
        <div class="queue-stat">
            <div class="queue-label">Token / Status</div>
            <div class="queue-value">{token_text} • {str(status_text).title()}</div>
        </div>
    </div>
</div>
""",
                    unsafe_allow_html=True,
                )

                with st.expander(f"View booked appointments for {patient['name']} ({patient['patient_id']})", expanded=False):
                    if patient["active_appointments"]:
                        appointment_rows = []
                        for item in patient["active_appointments"]:
                            appointment_rows.append(
                                {
                                    "Date": item.get("date", "-"),
                                    "Time": item.get("time", "-"),
                                    "Doctor": item.get("doctor", "Doctor not assigned"),
                                    "Token": item.get("token", "Not assigned"),
                                    "Status": item.get("status", "waiting").title(),
                                }
                            )
                        st.dataframe(pd.DataFrame(appointment_rows),
                                     width="stretch", hide_index=True)

                    st.caption("Hospital desk action")
                    with st.form(f"status_form_{patient['phone']}"):
                        open_tokens = [
                            item
                            for item in patient["appointments"]
                            if item.get("hospital_status", "scheduled") != "completed"
                        ]
                        token_options = [
                            f"{item.get('token')} | {item.get('date', '-')} {item.get('time', '-')}"
                            for item in open_tokens
                        ]
                        selected_token = st.selectbox(
                            "Mark appointment as done",
                            token_options if token_options else [
                                "No active appointments"],
                            disabled=not token_options,
                            key=f"token_{patient['phone']}",
                        )
                        if st.form_submit_button("Mark done", width="stretch", disabled=not token_options):
                            token_value = selected_token.split("|")[0].strip()
                            ok, result = update_hospital_appointment_status(
                                patient["phone"],
                                token_value,
                                "completed",
                            )
                            if ok:
                                st.toast(
                                    f"Hospital desk marked token {token_value} as completed.")
                                st.rerun()
                            else:
                                st.warning(result)

        with col_right:
            st.markdown(
                '<div class="section-title">Operational Snapshot</div>', unsafe_allow_html=True)

            st.markdown(
                """
<div class="tiny-note">
This hospital view now reflects the same storage model used by the main medical app:
multi-appointment booking, per-appointment tokens, doctor assignment, status tracking,
and Med Buddy emotional summaries with timestamped history.
</div>
""",
                unsafe_allow_html=True,
            )

            doctor_counts = {}
            for patient in visible_patients:
                for item in patient["active_appointments"]:
                    doctor = item.get("doctor", "Doctor not assigned")
                    doctor_counts[doctor] = doctor_counts.get(doctor, 0) + 1

            if doctor_counts:
                st.write("")
                st.caption("Doctor Allocation")
                doctor_df = pd.DataFrame(
                    [{"Doctor": doctor, "Appointments": count}
                        for doctor, count in doctor_counts.items()]
                ).sort_values("Appointments", ascending=False)
                st.dataframe(doctor_df, width="stretch", hide_index=True)
            else:
                st.info(
                    "Doctor assignment will appear here once appointments are booked.")

            st.write("")
            st.caption("Low-Risk Count")
            st.progress(min(low / max(len(visible_patients), 1), 1.0),
                        text=f"{low} of {len(visible_patients)} active patients currently low risk")
            st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    if not patients:
        st.warning("No patient data available yet.")
    else:
        phone_options = [item["phone"] for item in patients]
        selected_phone = st.selectbox("Select Patient", phone_options)
        patient = next(
            item for item in patients if item["phone"] == selected_phone)
        emotion_payload = patient["emotion_payload"]
        next_item = patient["next_appointment"] or {}

        left, right = st.columns([1, 2])
        with left:

            st.markdown("### Patient Summary")
            st.write(f"**Name:** {patient['name']}")
            st.write(f"**Patient ID:** {patient['patient_id']}")
            st.write(f"**Phone:** {patient['phone']}")
            st.write(f"**Risk level:** {patient['risk_level']}")
            st.write(f"**Risk score:** {patient['risk_score']}")
            st.write(
                f"**Next appointment:** {next_item.get('date', 'Not scheduled')}")
            st.write(
                f"**Appointment time:** {next_item.get('time', 'Not scheduled')}")
            st.write(
                f"**Assigned doctor:** {next_item.get('doctor', 'Doctor not assigned')}")
            st.write(
                f"**Latest emotional label:** {emotion_payload['emotion']}")
            st.write(
                f"**Depression risk signal:** {emotion_payload['depression_risk']}")
            st.write(f"**Last emotional update:** {emotion_payload['time']}")
            st.caption(emotion_payload["message"])

            if patient["risk_level"] == "High" or emotion_payload["depression_risk"] == "High":
                st.error(
                    "Immediate review is recommended for this patient based on the latest stored signals.")
            elif emotion_payload["emotion"] in {"Concerned", "Anxious", "Distressed"}:
                st.warning(
                    "Supportive follow-up may be useful based on the recent emotional trend.")
            else:
                st.success(
                    "Current emotional signal does not indicate acute escalation.")
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            st.markdown("### Emotional Trend")
            history = emotion_payload["history"]
            if history:
                df = pd.DataFrame(history)
                df["time"] = pd.to_datetime(df["time"], errors="coerce")
                df = df.dropna(subset=["time"]).sort_values("time")
                df["score"] = df["emotion"].apply(emotion_score)

                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(df["time"], df["score"], color="#1976d2",
                        linewidth=2.4, marker="o", markersize=6)
                ax.fill_between(df["time"], df["score"], 0,
                                color="#90caf9", alpha=0.22)
                ax.set_yticks([1, 2, 3, 4, 5])
                ax.set_yticklabels(
                    ["Distressed", "Concerned", "Neutral", "Calm", "Happy"])
                ax.set_xlabel("Recorded Time")
                ax.set_ylabel("Emotional State")
                ax.grid(alpha=0.2)
                plt.xticks(rotation=25)
                st.pyplot(fig, width="stretch")

                if (df["score"] <= 2).any():
                    st.error(
                        "At least one emotionally sensitive check-in was detected in the recent history.")
                else:
                    st.info(
                        "Recent emotional history has stayed in the neutral-to-positive range.")

                trend_rows = df[["time", "emotion",
                                 "depression_risk", "message"]].copy()
                trend_rows["time"] = trend_rows["time"].dt.strftime(
                    "%Y-%m-%d %I:%M %p")
                trend_rows.columns = ["Time", "Emotion",
                                      "Depression Risk", "Captured Note"]
                with st.expander("View emotional history details", expanded=False):
                    st.dataframe(trend_rows, width="stretch", hide_index=True)
            else:
                st.info("No emotion history available for this patient yet.")
