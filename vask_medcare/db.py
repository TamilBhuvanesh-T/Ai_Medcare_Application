import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash


def utcnow() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def dumps(data) -> str:
    return json.dumps(data, ensure_ascii=True)


def loads(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def init_db(db_path: str) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            json.dumps(
                {
                    "users": [],
                    "doctors": [],
                    "reports": [],
                    "chat_messages": [],
                    "emotions": [],
                    "doctor_guidance": [],
                    "appointments": [],
                    "alerts": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    with get_db(db_path) as conn:
        seed_defaults(conn)


class QueryResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class JsonConnection:
    def __init__(self, db_path: str):
        self.path = Path(db_path)
        self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def commit(self):
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def _next_id(self, table: str) -> int:
        rows = self.data[table]
        return max((row["id"] for row in rows), default=0) + 1

    def execute(self, query: str, params=()):
        q = " ".join(query.split())

        if q.startswith("SELECT id FROM doctors LIMIT 1"):
            return QueryResult([{"id": row["id"]} for row in self.data["doctors"][:1]])

        if q.startswith("INSERT INTO doctors"):
            for name, department, email in params:
                self.data["doctors"].append(
                    {
                        "id": self._next_id("doctors"),
                        "name": name,
                        "department": department,
                        "email": email,
                        "active": 1,
                    }
                )
            return QueryResult([])

        if q.startswith("SELECT id FROM users WHERE phone = ?"):
            phone = params[0]
            rows = [{"id": row["id"]} for row in self.data["users"] if row["phone"] == phone]
            return QueryResult(rows[:1])

        if q.startswith("SELECT * FROM users WHERE phone = ?"):
            phone = params[0]
            rows = [row for row in self.data["users"] if row["phone"] == phone]
            return QueryResult(rows[:1])

        if q.startswith("SELECT * FROM users WHERE id = ?"):
            user_id = params[0]
            rows = [row for row in self.data["users"] if row["id"] == user_id]
            return QueryResult(rows[:1])

        if q.startswith("INSERT INTO users"):
            if len(params) == 6:
                name, phone, email, password_hash, role, created_at = params
            else:
                name, phone, email, password_hash, created_at = params
                role = "patient"
            self.data["users"].append(
                {
                    "id": self._next_id("users"),
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "password_hash": password_hash,
                    "role": role,
                    "created_at": created_at,
                }
            )
            return QueryResult([])

        if q.startswith("SELECT * FROM reports WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1"):
            user_id = params[0]
            rows = [row for row in self.data["reports"] if row["user_id"] == user_id]
            rows.sort(key=lambda row: row["uploaded_at"], reverse=True)
            return QueryResult(rows[:1])

        if q.startswith("SELECT id, uploaded_at, parameters_json FROM reports WHERE user_id = ? AND analysis_status = 'complete' ORDER BY uploaded_at ASC"):
            user_id = params[0]
            rows = [
                {"id": row["id"], "uploaded_at": row["uploaded_at"], "parameters_json": row["parameters_json"]}
                for row in self.data["reports"]
                if row["user_id"] == user_id and row["analysis_status"] == "complete"
            ]
            rows.sort(key=lambda row: row["uploaded_at"])
            return QueryResult(rows)

        if q.startswith("INSERT INTO reports"):
            user_id, filename, stored_path, uploaded_at = params
            self.data["reports"].append(
                {
                    "id": self._next_id("reports"),
                    "user_id": user_id,
                    "filename": filename,
                    "stored_path": stored_path,
                    "uploaded_at": uploaded_at,
                    "pdf_text": "",
                    "ocr_text": "",
                    "combined_text": "",
                    "summary": "",
                    "narrative": "",
                    "voice_text": "",
                    "risk_level": "Low",
                    "risk_score": 0,
                    "parameters_json": "[]",
                    "trends_json": "{}",
                    "recommendations_json": "[]",
                    "analysis_status": "pending",
                }
            )
            return QueryResult([])

        if q.startswith("UPDATE reports SET"):
            report_id = params[-1]
            for row in self.data["reports"]:
                if row["id"] == report_id:
                    (
                        row["pdf_text"],
                        row["ocr_text"],
                        row["combined_text"],
                        row["summary"],
                        row["narrative"],
                        row["voice_text"],
                        row["risk_level"],
                        row["risk_score"],
                        row["parameters_json"],
                        row["trends_json"],
                        row["recommendations_json"],
                    ) = params[:-1]
                    row["analysis_status"] = "complete"
                    break
            return QueryResult([])

        if q.startswith("SELECT * FROM emotions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20"):
            user_id = params[0]
            rows = [row for row in self.data["emotions"] if row["user_id"] == user_id]
            rows.sort(key=lambda row: row["created_at"], reverse=True)
            return QueryResult(rows[:20])

        if q.startswith("INSERT INTO emotions"):
            user_id, emotion, mood, urgency, safety_risk, source_text, created_at = params
            self.data["emotions"].append(
                {
                    "id": self._next_id("emotions"),
                    "user_id": user_id,
                    "emotion": emotion,
                    "mood": mood,
                    "urgency": urgency,
                    "safety_risk": safety_risk,
                    "source_text": source_text,
                    "created_at": created_at,
                }
            )
            return QueryResult([])

        if q.startswith("SELECT guidance FROM doctor_guidance WHERE user_id = ?"):
            user_id = params[0]
            rows = [{"guidance": row["guidance"]} for row in self.data["doctor_guidance"] if row["user_id"] == user_id]
            return QueryResult(rows[:1])

        if q.startswith("SELECT * FROM doctor_guidance WHERE user_id = ?"):
            user_id = params[0]
            rows = [row for row in self.data["doctor_guidance"] if row["user_id"] == user_id]
            return QueryResult(rows[:1])

        if q.startswith("INSERT INTO doctor_guidance"):
            user_id, doctor_id, guidance, updated_at = params
            self.data["doctor_guidance"].append(
                {
                    "id": self._next_id("doctor_guidance"),
                    "user_id": user_id,
                    "doctor_id": doctor_id,
                    "guidance": guidance,
                    "updated_at": updated_at,
                }
            )
            return QueryResult([])

        if q.startswith("UPDATE doctor_guidance SET"):
            doctor_id, guidance, updated_at, user_id = params
            for row in self.data["doctor_guidance"]:
                if row["user_id"] == user_id:
                    row["doctor_id"] = doctor_id
                    row["guidance"] = guidance
                    row["updated_at"] = updated_at
                    break
            return QueryResult([])

        if q.startswith("SELECT * FROM doctors WHERE department = ? AND active = 1 ORDER BY name"):
            department = params[0]
            rows = [row for row in self.data["doctors"] if row["department"] == department and row["active"] == 1]
            rows.sort(key=lambda row: row["name"])
            return QueryResult(rows)

        if q.startswith("SELECT * FROM doctors WHERE active = 1 ORDER BY department, name"):
            rows = [row for row in self.data["doctors"] if row["active"] == 1]
            rows.sort(key=lambda row: (row["department"], row["name"]))
            return QueryResult(rows)

        if q.startswith("SELECT a.*, d.name AS doctor_name FROM appointments a JOIN doctors d"):
            user_id = params[0]
            rows = []
            for appointment in self.data["appointments"]:
                if appointment["user_id"] != user_id:
                    continue
                doctor = next((row for row in self.data["doctors"] if row["id"] == appointment["doctor_id"]), None)
                rows.append({**appointment, "doctor_name": doctor["name"] if doctor else "Unknown"})
            rows.sort(key=lambda row: row["created_at"], reverse=True)
            return QueryResult(rows)

        if q.startswith("SELECT COALESCE(MAX(token), 1000) + 1 AS token FROM appointments"):
            token = max((row["token"] for row in self.data["appointments"]), default=1000) + 1
            return QueryResult([{"token": token}])

        if q.startswith("INSERT INTO appointments"):
            user_id, doctor_id, department, appointment_date, appointment_time, token, created_at = params
            self.data["appointments"].append(
                {
                    "id": self._next_id("appointments"),
                    "user_id": user_id,
                    "doctor_id": int(doctor_id),
                    "department": department,
                    "appointment_date": appointment_date,
                    "appointment_time": appointment_time,
                    "token": token,
                    "status": "waiting",
                    "created_at": created_at,
                }
            )
            return QueryResult([])

        if q.startswith("UPDATE appointments SET status = ? WHERE id = ?"):
            status, appointment_id = params
            for row in self.data["appointments"]:
                if row["id"] == appointment_id:
                    row["status"] = status
                    break
            return QueryResult([])

        if q.startswith("INSERT INTO chat_messages"):
            (
                user_id,
                report_id,
                user_message,
                assistant_message,
                intent,
                emotion,
                mood,
                urgency,
                safety_risk,
                created_at,
            ) = params
            self.data["chat_messages"].append(
                {
                    "id": self._next_id("chat_messages"),
                    "user_id": user_id,
                    "report_id": report_id,
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                    "intent": intent,
                    "emotion": emotion,
                    "mood": mood,
                    "urgency": urgency,
                    "safety_risk": safety_risk,
                    "created_at": created_at,
                }
            )
            return QueryResult([])

        if q.startswith("SELECT * FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 12"):
            user_id = params[0]
            rows = [row for row in self.data["chat_messages"] if row["user_id"] == user_id]
            rows.sort(key=lambda row: row["created_at"], reverse=True)
            return QueryResult(rows[:12])

        if q.startswith("INSERT INTO alerts"):
            user_id, report_id, category, severity, message, email_status, created_at = params
            self.data["alerts"].append(
                {
                    "id": self._next_id("alerts"),
                    "user_id": user_id,
                    "report_id": report_id,
                    "category": category,
                    "severity": severity,
                    "message": message,
                    "email_status": email_status,
                    "created_at": created_at,
                }
            )
            return QueryResult([])

        if q.startswith("SELECT u.*, r.risk_level, r.risk_score, r.summary, r.uploaded_at,"):
            rows = []
            patients = [row for row in self.data["users"] if row["role"] == "patient"]
            for patient in patients:
                reports = [row for row in self.data["reports"] if row["user_id"] == patient["id"]]
                reports.sort(key=lambda row: row["uploaded_at"], reverse=True)
                report = reports[0] if reports else None
                emotions = [row for row in self.data["emotions"] if row["user_id"] == patient["id"]]
                emotions.sort(key=lambda row: row["created_at"], reverse=True)
                rows.append(
                    {
                        **patient,
                        "risk_level": report["risk_level"] if report else None,
                        "risk_score": report["risk_score"] if report else None,
                        "summary": report["summary"] if report else None,
                        "uploaded_at": report["uploaded_at"] if report else None,
                        "latest_emotion": emotions[0]["emotion"] if emotions else None,
                    }
                )
            rows.sort(key=lambda row: row["uploaded_at"] or row["created_at"], reverse=True)
            return QueryResult(rows)

        if q.startswith("SELECT a.*, u.name AS patient_name, d.name AS doctor_name FROM appointments a"):
            rows = []
            for appointment in self.data["appointments"]:
                patient = next((row for row in self.data["users"] if row["id"] == appointment["user_id"]), None)
                doctor = next((row for row in self.data["doctors"] if row["id"] == appointment["doctor_id"]), None)
                rows.append(
                    {
                        **appointment,
                        "patient_name": patient["name"] if patient else "Unknown",
                        "doctor_name": doctor["name"] if doctor else "Unknown",
                    }
                )
            rows.sort(key=lambda row: row["token"])
            return QueryResult(rows)

        if q.startswith("SELECT a.*, u.name AS patient_name FROM alerts a"):
            rows = []
            for alert in self.data["alerts"]:
                patient = next((row for row in self.data["users"] if row["id"] == alert["user_id"]), None)
                rows.append({**alert, "patient_name": patient["name"] if patient else None})
            rows.sort(key=lambda row: row["created_at"], reverse=True)
            return QueryResult(rows[:10])

        raise NotImplementedError(f"Unsupported query: {q}")


def seed_defaults(conn: JsonConnection) -> None:
    if not conn.execute("SELECT id FROM doctors LIMIT 1").fetchone():
        conn.execute(
            "INSERT INTO doctors (name, department, email) VALUES (?, ?, ?)",
            [
                ("Dr. Meera Nair", "General Medicine", "meera@vask.local"),
                ("Dr. Arjun Rao", "Cardiology", "arjun@vask.local"),
                ("Dr. Kavya Menon", "Endocrinology", "kavya@vask.local"),
                ("Dr. Ritesh Shah", "Nephrology", "ritesh@vask.local"),
                ("Dr. Sana Iqbal", "Mental Health", "sana@vask.local"),
            ],
        )
    if not conn.execute("SELECT id FROM users WHERE phone = ?", ("9999999999",)).fetchone():
        conn.execute(
            """
            INSERT INTO users (name, phone, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Hospital Admin",
                "9999999999",
                "admin@vask.local",
                generate_password_hash("admin123"),
                "admin",
                utcnow(),
            ),
        )


@contextmanager
def get_db(db_path: str):
    conn = JsonConnection(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.commit()
