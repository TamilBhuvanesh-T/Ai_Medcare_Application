import os
from functools import wraps

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from .ai import analyze_message, generate_chat_reply
from .analysis import analyze_report, inline_svg_trend, suggest_department
from .db import dumps, get_db, loads, utcnow
from .mailer import send_email_alert


def register_routes(app):
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["CHART_FOLDER"], exist_ok=True)

    def login_required(role=None):
        def decorator(view):
            @wraps(view)
            def wrapped(*args, **kwargs):
                user_id = session.get("user_id")
                user_role = session.get("role")
                if not user_id:
                    return redirect(url_for("login"))
                if role and user_role != role:
                    flash("Access denied for this page.", "error")
                    return redirect(url_for("dashboard"))
                return view(*args, **kwargs)

            return wrapped

        return decorator

    def current_user(conn):
        user_id = session.get("user_id")
        if not user_id:
            return None
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    def latest_report(conn, user_id):
        return conn.execute(
            "SELECT * FROM reports WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()

    def emotion_history(conn, user_id):
        return conn.execute(
            "SELECT * FROM emotions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
            (user_id,),
        ).fetchall()

    def patient_reports_for_trend(conn, user_id):
        rows = conn.execute(
            "SELECT id, uploaded_at, parameters_json FROM reports WHERE user_id = ? AND analysis_status = 'complete' ORDER BY uploaded_at ASC",
            (user_id,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "uploaded_at": row["uploaded_at"],
                "parameters": loads(row["parameters_json"], []),
            }
            for row in rows
        ]

    def recommend_doctors(conn, department):
        return conn.execute(
            "SELECT * FROM doctors WHERE department = ? AND active = 1 ORDER BY name",
            (department,),
        ).fetchall()

    def create_alert(conn, user_id, report_id, category, severity, message, patient_email=None):
        email_status = "sent" if patient_email and send_email_alert(
            app.config,
            patient_email,
            f"VASK MedCare Alert: {severity.title()} {category.title()}",
            message,
        ) else "not_sent"
        conn.execute(
            """
            INSERT INTO alerts (user_id, report_id, category, severity, message, email_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, report_id, category, severity, message, email_status, utcnow()),
        )

    @app.template_filter("trend_svg")
    def trend_svg(values):
        return inline_svg_trend(values)

    @app.route("/", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            phone = request.form.get("phone", "").strip()
            password = request.form.get("password", "")
            with get_db(app.config["DATABASE_PATH"]) as conn:
                user = conn.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()
                if user and check_password_hash(user["password_hash"], password):
                    session["user_id"] = user["id"]
                    session["role"] = user["role"]
                    session["name"] = user["name"]
                    if user["role"] == "admin":
                        return redirect(url_for("admin_dashboard"))
                    return redirect(url_for("dashboard"))
                flash("Invalid phone or password.", "error")
        return render_template("patient_login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            phone = request.form.get("phone", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            if not (name and phone and password):
                flash("Name, phone, and password are required.", "error")
                return render_template("patient_register.html")
            with get_db(app.config["DATABASE_PATH"]) as conn:
                existing = conn.execute("SELECT id FROM users WHERE phone = ?", (phone,)).fetchone()
                if existing:
                    flash("A user with this phone already exists.", "error")
                else:
                    conn.execute(
                        """
                        INSERT INTO users (name, phone, email, password_hash, role, created_at)
                        VALUES (?, ?, ?, ?, 'patient', ?)
                        """,
                        (name, phone, email, generate_password_hash(password), utcnow()),
                    )
                    flash("Account created. Please sign in.", "success")
                    return redirect(url_for("login"))
        return render_template("patient_register.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required(role="patient")
    def dashboard():
        active_tab = request.args.get("tab", "dashboard")
        with get_db(app.config["DATABASE_PATH"]) as conn:
            user = current_user(conn)
            report = latest_report(conn, user["id"])
            appointments = conn.execute(
                """
                SELECT a.*, d.name AS doctor_name
                FROM appointments a
                JOIN doctors d ON d.id = a.doctor_id
                WHERE a.user_id = ?
                ORDER BY a.created_at DESC
                """,
                (user["id"],),
            ).fetchall()
            chats = conn.execute(
                "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 12",
                (user["id"],),
            ).fetchall()
            emotions = emotion_history(conn, user["id"])
            guidance = conn.execute(
                "SELECT guidance FROM doctor_guidance WHERE user_id = ?",
                (user["id"],),
            ).fetchone()
            doctors = []
            department = "General Medicine"
            if report:
                hydrated = hydrate_report(report)
                department = suggest_department(
                    hydrated["parameters"],
                    report["risk_level"],
                    emotions[0]["emotion"] if emotions else None,
                )
                doctors = recommend_doctors(conn, department)
                report = hydrated
            return render_template(
                "patient_dashboard.html",
                user=user,
                active_tab=active_tab,
                report=report,
                appointments=appointments,
                chats=reversed(chats),
                emotions=reversed(emotions),
                guidance_text=guidance["guidance"] if guidance else "",
                doctors=doctors,
                department=department,
            )

    @app.route("/upload-report", methods=["POST"])
    @login_required(role="patient")
    def upload_report():
        file = request.files.get("report")
        if not file or not file.filename.lower().endswith(".pdf"):
            flash("Please upload a PDF report.", "error")
            return redirect(url_for("dashboard", tab="dashboard"))

        filename = secure_filename(file.filename)
        stored_name = f"{session['user_id']}_{utcnow().replace(':', '-')}_{filename}"
        stored_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
        file.save(stored_path)

        with get_db(app.config["DATABASE_PATH"]) as conn:
            conn.execute(
                """
                INSERT INTO reports (user_id, filename, stored_path, uploaded_at, analysis_status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (session["user_id"], filename, stored_path, utcnow()),
            )
        flash("Report uploaded. Run analysis to process it.", "success")
        return redirect(url_for("dashboard", tab="dashboard"))

    @app.route("/run-analysis", methods=["POST"])
    @login_required(role="patient")
    def run_analysis():
        with get_db(app.config["DATABASE_PATH"]) as conn:
            report = latest_report(conn, session["user_id"])
            user = current_user(conn)
            if not report:
                flash("Upload a report before running analysis.", "error")
                return redirect(url_for("dashboard", tab="dashboard"))

            prior = [
                row for row in patient_reports_for_trend(conn, session["user_id"]) if row["id"] != report["id"]
            ]
            result = analyze_report(report["stored_path"], prior, report["id"], report["uploaded_at"])

            conn.execute(
                """
                UPDATE reports
                SET pdf_text = ?, ocr_text = ?, combined_text = ?, summary = ?, narrative = ?,
                    voice_text = ?, risk_level = ?, risk_score = ?, parameters_json = ?,
                    trends_json = ?, recommendations_json = ?, analysis_status = 'complete'
                WHERE id = ?
                """,
                (
                    result["pdf_text"],
                    result["ocr_text"],
                    result["combined_text"],
                    result["summary"],
                    result["narrative"],
                    result["voice_text"],
                    result["risk"]["risk_level"],
                    result["risk"]["risk_score"],
                    dumps(result["parameters"]),
                    dumps(result["trends"]),
                    dumps(result["recommendations"]),
                    report["id"],
                ),
            )

            if result["risk"]["risk_level"] == "High":
                create_alert(
                    conn,
                    user["id"],
                    report["id"],
                    "medical",
                    "high",
                    f"High-risk report detected for {user['name']}. Review the latest summary and parameters.",
                    patient_email=user["email"],
                )
        flash("Medical AI analysis completed.", "success")
        return redirect(url_for("dashboard", tab="dashboard"))

    @app.route("/chat", methods=["POST"])
    @login_required(role="patient")
    def chat():
        message = request.form.get("message", "").strip()
        if not message:
            return redirect(url_for("dashboard", tab="assistant"))

        with get_db(app.config["DATABASE_PATH"]) as conn:
            user = current_user(conn)
            report = latest_report(conn, user["id"])
            if not report or report["analysis_status"] != "complete":
                flash("Run analysis before using the AI assistant.", "error")
                return redirect(url_for("dashboard", tab="assistant"))

            guidance_row = conn.execute(
                "SELECT guidance FROM doctor_guidance WHERE user_id = ?",
                (user["id"],),
            ).fetchone()
            guidance = guidance_row["guidance"] if guidance_row else ""
            hydrated = hydrate_report(report)
            emotion_result = analyze_message(message, hydrated["summary"], guidance)
            reply = generate_chat_reply(
                message,
                hydrated["combined_text"],
                guidance,
                emotion_result,
                hydrated["recommendations"],
            )
            timestamp = utcnow()
            conn.execute(
                """
                INSERT INTO chat_messages (user_id, report_id, user_message, assistant_message, intent, emotion, mood, urgency, safety_risk, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    report["id"],
                    message,
                    reply,
                    emotion_result.get("intent", "report question"),
                    emotion_result.get("emotion", "Neutral"),
                    emotion_result.get("mood", "steady"),
                    emotion_result.get("urgency", "low"),
                    emotion_result.get("safety_risk", "none"),
                    timestamp,
                ),
            )
            conn.execute(
                """
                INSERT INTO emotions (user_id, emotion, mood, urgency, safety_risk, source_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    emotion_result.get("emotion", "Neutral"),
                    emotion_result.get("mood", "steady"),
                    emotion_result.get("urgency", "low"),
                    emotion_result.get("safety_risk", "none"),
                    message,
                    timestamp,
                ),
            )
            if emotion_result.get("safety_risk") == "urgent":
                create_alert(
                    conn,
                    user["id"],
                    report["id"],
                    "mental_health",
                    "urgent",
                    f"Urgent distress signal detected for {user['name']}. Review chat and reach out quickly.",
                    patient_email=user["email"],
                )
        return redirect(url_for("dashboard", tab="assistant"))

    @app.route("/book-appointment", methods=["POST"])
    @login_required(role="patient")
    def book_appointment():
        doctor_id = request.form.get("doctor_id")
        department = request.form.get("department", "General Medicine")
        appointment_date = request.form.get("appointment_date")
        appointment_time = request.form.get("appointment_time")
        if not all([doctor_id, department, appointment_date, appointment_time]):
            flash("Select department, doctor, date, and time.", "error")
            return redirect(url_for("dashboard", tab="care"))

        with get_db(app.config["DATABASE_PATH"]) as conn:
            next_token_row = conn.execute("SELECT COALESCE(MAX(token), 1000) + 1 AS token FROM appointments").fetchone()
            token = next_token_row["token"]
            conn.execute(
                """
                INSERT INTO appointments (user_id, doctor_id, department, appointment_date, appointment_time, token, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'waiting', ?)
                """,
                (session["user_id"], doctor_id, department, appointment_date, appointment_time, token, utcnow()),
            )
            user = current_user(conn)
            create_alert(
                conn,
                user["id"],
                None,
                "appointment",
                "info",
                f"Appointment booked for {appointment_date} at {appointment_time}. Token: {token}.",
                patient_email=user["email"],
            )
        flash("Appointment booked successfully.", "success")
        return redirect(url_for("dashboard", tab="care"))

    @app.route("/admin")
    @login_required(role="admin")
    def admin_dashboard():
        patient_id = request.args.get("patient_id", type=int)
        with get_db(app.config["DATABASE_PATH"]) as conn:
            patients = conn.execute(
                """
                SELECT u.*, r.risk_level, r.risk_score, r.summary, r.uploaded_at,
                       (SELECT emotion FROM emotions e WHERE e.user_id = u.id ORDER BY created_at DESC LIMIT 1) AS latest_emotion
                FROM users u
                LEFT JOIN reports r ON r.id = (
                    SELECT id FROM reports rr WHERE rr.user_id = u.id ORDER BY uploaded_at DESC LIMIT 1
                )
                WHERE u.role = 'patient'
                ORDER BY COALESCE(r.uploaded_at, u.created_at) DESC
                """
            ).fetchall()
            appointments = conn.execute(
                """
                SELECT a.*, u.name AS patient_name, d.name AS doctor_name
                FROM appointments a
                JOIN users u ON u.id = a.user_id
                JOIN doctors d ON d.id = a.doctor_id
                ORDER BY a.token ASC
                """
            ).fetchall()
            alerts = conn.execute(
                """
                SELECT a.*, u.name AS patient_name
                FROM alerts a
                LEFT JOIN users u ON u.id = a.user_id
                ORDER BY a.created_at DESC LIMIT 10
                """
            ).fetchall()
            patient_detail = None
            patient_emotions = []
            patient_messages = []
            patient_guidance = None
            if patient_id:
                patient_detail = conn.execute("SELECT * FROM users WHERE id = ?", (patient_id,)).fetchone()
                report = latest_report(conn, patient_id)
                patient_detail = {**patient_detail, "report": hydrate_report(report) if report else None}
                patient_emotions = conn.execute(
                    "SELECT * FROM emotions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
                    (patient_id,),
                ).fetchall()
                patient_messages = conn.execute(
                    "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 12",
                    (patient_id,),
                ).fetchall()
                patient_guidance = conn.execute(
                    "SELECT * FROM doctor_guidance WHERE user_id = ?",
                    (patient_id,),
                ).fetchone()
            metrics = {
                "patients": len(patients),
                "high_risk": sum(1 for p in patients if p.get("risk_level") == "High"),
                "moderate_risk": sum(1 for p in patients if p.get("risk_level") == "Moderate"),
                "distress_alerts": sum(1 for a in alerts if a["category"] == "mental_health"),
            }
            doctors = conn.execute("SELECT * FROM doctors WHERE active = 1 ORDER BY department, name").fetchall()
            return render_template(
                "admin_dashboard.html",
                patients=patients,
                appointments=appointments,
                alerts=alerts,
                metrics=metrics,
                patient_detail=patient_detail,
                patient_emotions=reversed(patient_emotions),
                patient_messages=reversed(patient_messages),
                patient_guidance=patient_guidance,
                doctors=doctors,
            )

    @app.route("/admin/patient/<int:patient_id>/guidance", methods=["POST"])
    @login_required(role="admin")
    def save_guidance(patient_id):
        guidance = request.form.get("guidance", "").strip()
        doctor_id = request.form.get("doctor_id", type=int)
        with get_db(app.config["DATABASE_PATH"]) as conn:
            existing = conn.execute(
                "SELECT id FROM doctor_guidance WHERE user_id = ?",
                (patient_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE doctor_guidance
                    SET doctor_id = ?, guidance = ?, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (doctor_id, guidance, utcnow(), patient_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO doctor_guidance (user_id, doctor_id, guidance, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (patient_id, doctor_id, guidance, utcnow()),
                )
        flash("Doctor guidance updated for this patient.", "success")
        return redirect(url_for("admin_dashboard", patient_id=patient_id))

    @app.route("/admin/appointment/<int:appointment_id>/status", methods=["POST"])
    @login_required(role="admin")
    def update_appointment_status(appointment_id):
        status = request.form.get("status", "waiting")
        with get_db(app.config["DATABASE_PATH"]) as conn:
            conn.execute("UPDATE appointments SET status = ? WHERE id = ?", (status, appointment_id))
        flash("Appointment status updated.", "success")
        return redirect(url_for("admin_dashboard"))


def hydrate_report(report):
    if not report:
        return None
    hydrated = dict(report)
    hydrated["parameters"] = loads(report["parameters_json"], [])
    hydrated["trends"] = loads(report["trends_json"], {})
    hydrated["recommendations"] = loads(report["recommendations_json"], [])
    return hydrated
