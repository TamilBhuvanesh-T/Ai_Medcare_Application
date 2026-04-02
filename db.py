import json
import os
import random
import re
from datetime import datetime

# ✅ Use proper JSON files
DB_FILE = "user_data.json"
EMO_FILE = "emotion_db.json"


# ==========================
# 🔧 SAFE JSON LOAD
# ==========================
def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"?? Error loading {file}:", e)
            return {}
    return {}


# ==========================
# ?? SAFE JSON SAVE
# ==========================
def save_json(file, data):
    try:
        with open(file, "w") as f:
            json.dump(data, f, indent=4)
            print(f"✅ Saved → {file}")
    except Exception as e:
        print(f"❌ Error saving {file}:", e)


        # ==========================
        # 🔥 EMOTION HELPERS
        # ==========================
def get_llm_line(emotion):
    parts = re.split(r'[.\n]', emotion.strip())
    parts = [p.strip() for p in parts if p.strip()]
    return parts[2] if len(parts) >= 3 else (parts[0] if parts else "")


def fallback_emotion(text):
    text = text.lower()

    if any(w in text for w in ["suicide", "kill myself", "end my life"]):
        return "Distressed"

    if any(w in text for w in ["depressed", "hopeless"]):
        return "Distressed"

    if any(w in text for w in ["anxious", "worried", "fear"]):
        return "Anxious"

    if any(w in text for w in ["happy", "good", "great"]):
        return "Good Happy"

    return "Neutral"


def final_emotion(llm_output, user_input):
    text = (get_llm_line(llm_output) + " " + user_input).lower()

    if any(w in text for w in ["suicide", "kill myself", "die"]):
        return "Distressed"

    if any(w in text for w in ["depressed", "hopeless", "worthless"]):
        return "Depressed"

    if any(w in text for w in ["anxious", "worried", "stress"]):
        return "Anxious"

    if any(w in text for w in ["happy", "great", "excited"]):
        return "Good Happy"

    return fallback_emotion(user_input)


def clean_mood(text):
    parts = re.split(r'[.\n]', text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    return parts[2] if len(parts) >= 3 else (parts[0] if parts else text)


# ==========================
# 🔥 SAVE EMOTION
# ==========================
def save_emotion(phone, emotion):
    if not phone:
        return

    data = load_json(EMO_FILE)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = data.get(phone, {})

    if isinstance(emotion, dict):
        payload = dict(emotion)
        payload["time"] = now
        user["latest"] = payload
        user.setdefault("history", []).append(payload)
    else:
        final = final_emotion(emotion, emotion)
        mood = clean_mood(emotion)
        payload = {
            "emotion": final,
            "mood": mood,
            "time": now,
        }
        user["latest"] = payload
        user["emotion"] = final
        user["mood"] = mood
        user["time"] = now
        user.setdefault("history", []).append(payload)

    data[phone] = user
    save_json(EMO_FILE, data)


    # ==========================
    # 🔥 SAVE DATA (FIXED)
    # ==========================
def save_data(phone, risk, date=None, time=None):
    if not phone:
        print("No phone")
        return

    data = load_json(DB_FILE)
    user = data.get(phone, {})
    user["risk"] = {
        "risk_level": risk.get("risk_level", "Unknown"),
        "risk_score": risk.get("risk_score", 0),
    }
    data[phone] = user
    save_json(DB_FILE, data)


def _generate_unique_token(data):
    used_tokens = set()
    for user in data.values():
        appointment = user.get("appointment")
        if isinstance(appointment, dict) and appointment.get("token"):
            used_tokens.add(str(appointment.get("token")))
        for item in user.get("appointments", []):
            if item.get("token"):
                used_tokens.add(str(item.get("token")))

    while True:
        token = random.randint(1000, 9999)
        if str(token) not in used_tokens:
            return token


def save_appointment(phone, risk, appointment_date, appointment_time, doctor, token=None):
    if not phone:
        return False, "No phone number available."

    data = load_json(DB_FILE)
    user = data.get(phone, {})
    user["risk"] = {
        "risk_level": risk.get("risk_level", "Unknown"),
        "risk_score": risk.get("risk_score", 0),
    }

    if token is None:
        token = _generate_unique_token(data)

    appointment = {
        "date": str(appointment_date),
        "time": appointment_time,
        "doctor": doctor,
        "status": "waiting",
        "hospital_status": "scheduled",
        "token": token,
    }

    appointments = user.get("appointments", [])
    appointments.append(appointment)
    user["appointments"] = appointments
    user["appointment"] = appointment
    data[phone] = user
    save_json(DB_FILE, data)
    return True, appointment


def generate_token(phone):
    if not phone:
        return False, "No phone number available."

    data = load_json(DB_FILE)
    user = data.get(phone, {})
    appointment = user.get("appointment", {})

    if not appointment:
        return False, "Book an appointment first."
    if appointment.get("status") == "completed":
        return False, "This appointment is already completed."
    if appointment.get("token"):
        return False, "An active token already exists for this appointment."

    token = random.randint(1000, 9999)
    appointment["token"] = token
    appointment["status"] = "waiting"
    user["appointment"] = appointment
    data[phone] = user
    save_json(DB_FILE, data)
    return True, token


def complete_appointment(phone, token=None):
    if not phone:
        return False, "No phone number available."

    data = load_json(DB_FILE)
    user = data.get(phone, {})
    appointments = user.get("appointments", [])
    appointment = None

    if token is not None:
        for item in appointments:
            if str(item.get("token")) == str(token):
                appointment = item
                break

    if appointment is None:
        appointment = user.get("appointment", {})

    if not appointment:
        return False, "No active appointment found."

    appointment["status"] = "completed"
    for item in appointments:
        if str(item.get("token")) == str(appointment.get("token")):
            item["status"] = "completed"

    user["appointment"] = appointment
    user["appointments"] = appointments
    data[phone] = user
    save_json(DB_FILE, data)
    return True, appointment


def update_hospital_appointment_status(phone, token, hospital_status="completed"):
    if not phone:
        return False, "No phone number available."

    data = load_json(DB_FILE)
    user = data.get(phone, {})
    appointments = user.get("appointments", [])

    if not appointments:
        return False, "No appointments found for this patient."

    target = None
    for item in appointments:
        if str(item.get("token")) == str(token):
            item["hospital_status"] = hospital_status
            item["hospital_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            target = item
            break

    if target is None:
        return False, "Appointment token not found."

    latest = user.get("appointment")
    if isinstance(latest, dict) and str(latest.get("token")) == str(token):
        latest["hospital_status"] = hospital_status
        latest["hospital_updated_at"] = target["hospital_updated_at"]
        user["appointment"] = latest

    user["appointments"] = appointments
    data[phone] = user
    save_json(DB_FILE, data)
    return True, target


def load_data(phone):
    data = load_json(DB_FILE)
    return data.get(phone)


def load_all():
    return load_json(DB_FILE)


def load_emotion(phone):
    data = load_json(EMO_FILE)
    return data.get(phone)


def load_all_emotions():
    return load_json(EMO_FILE)
