# mail_service.py

import smtplib
from email.mime.text import MIMEText

# 🔐 Configure these
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"  # use Gmail App Password
RECEIVER_EMAIL = "doctor_email@gmail.com"


def send_emotion_alert(score):

    subject = "🚨 Patient Emotional Alert"

    body = f"""
    Patient Emotional Score: {score}

    Range:
        -1 → Very Negative (Distress)
        0 → Neutral
        +1 → Positive

        ⚠️ Low score may indicate emotional stress.
        """

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
            server.quit()

            print("📧 Email sent successfully")

    except Exception as e:
            print("❌ Mail error:", e)