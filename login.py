import json
import os
import random

FILE = "users.json"


if not os.path.exists(FILE):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)


def _read_users():
    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_users(users):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)


def _generate_patient_id(users):
    used_ids = set()
    for value in users.values():
        if isinstance(value, dict) and value.get("patient_id"):
            used_ids.add(str(value.get("patient_id")))

    while True:
        patient_id = f"{random.randint(0, 99999):05d}"
        if patient_id not in used_ids:
            return patient_id


def normalize_user_record(phone, record, users=None):
    if isinstance(record, dict):
        normalized = {
            "password": str(record.get("password", "")),
            "name": str(record.get("name") or f"Patient {phone[-4:]}").strip(),
            "patient_id": str(record.get("patient_id") or ""),
        }
        if not normalized["patient_id"] and users is not None:
            normalized["patient_id"] = _generate_patient_id(users)
        if record.get("email"):
            normalized["email"] = record.get("email")
        return normalized

    normalized = {
        "password": str(record),
        "name": f"Patient {phone[-4:]}",
        "patient_id": _generate_patient_id(users or {}),
    }
    return normalized


def load_users():
    raw_users = _read_users()
    normalized_users = {}
    changed = False

    for phone, record in raw_users.items():
        normalized = normalize_user_record(phone, record, raw_users)
        normalized_users[phone] = normalized
        if normalized != record:
            changed = True

    if changed:
        _write_users(normalized_users)

    return normalized_users


def get_user_profile(phone):
    users = load_users()
    return users.get(phone, {})


def add_user(phone, pwd, name):
    users = load_users()

    if phone in users:
        return False, "User already exists!"

    users[phone] = {
        "password": str(pwd),
        "name": str(name).strip(),
        "patient_id": _generate_patient_id(users),
    }
    _write_users(users)
    return True, users[phone]


def validate_login(phone, pwd):
    users = load_users()
    user = users.get(phone)
    if not user:
        return False
    return user.get("password") == str(pwd)


def is_valid_phone(phone):
    return phone.isdigit() and len(phone) == 10 and phone.startswith(("6", "7", "8", "9"))


def is_valid_password(pwd):
    return pwd.isdigit() and len(pwd) == 4


def is_valid_name(name):
    cleaned = " ".join((name or "").split())
    return len(cleaned) >= 2
