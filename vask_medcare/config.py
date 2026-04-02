from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = "vask-medcare-dev-secret"
    DATABASE_PATH = str(BASE_DIR / "vask_store.json")
    UPLOAD_FOLDER = str(BASE_DIR / "medical_data" / "pdfs")
    CHART_FOLDER = str(BASE_DIR / "static" / "generated")
    OLLAMA_MODEL = "phi3:mini"
    MAIL_FROM = ""
    MAIL_TO_ADMIN = ""
    SMTP_HOST = ""
    SMTP_PORT = 587
    SMTP_USERNAME = ""
    SMTP_PASSWORD = ""
    SMTP_USE_TLS = True
