import re
import unicodedata
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pdfplumber
import pytesseract
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_bytes


pytesseract.pytesseract.tesseract_cmd = str(
    Path(__import__("os").getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe"))
)
POPPLER_PATH = __import__("os").getenv("POPPLER_PATH", r"C:\poppler-25.12.0\Library\bin")

SECTION_NAMES = [
    "Patient Information",
    "Chief Complaint",
    "Medical History",
    "Clinical Examination",
    "Investigations",
    "Diagnosis",
    "Treatment",
    "Current Condition",
    "Recommendations",
    "Doctor",
]

SECTION_HEADERS = {name.lower(): name for name in SECTION_NAMES}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def clean_final_text(text):
    allowed = r"[^a-zA-Z0-9\s.,:/()\-\n]"
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(allowed, " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_pdf_text(file_bytes):
    text_pdfplumber = ""
    text_pypdf2 = ""
    text_ocr = ""

    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text_pdfplumber += page.extract_text() or ""

    reader = PdfReader(BytesIO(file_bytes))
    for page in reader.pages:
        text_pypdf2 += page.extract_text() or ""

    images = convert_from_bytes(file_bytes, poppler_path=POPPLER_PATH)
    for index, image in enumerate(images, start=1):
        page_text = pytesseract.image_to_string(image, config="--oem 3 --psm 6")
        text_ocr += f"\n--- Page {index} ---\n{page_text}"

    final_text = text_pdfplumber + text_pypdf2
    cleaned_versions = clean_final_text(final_text)
    combined_text = (text_ocr + "\n" + cleaned_versions).strip()

    return {
        "pdfplumber_text": text_pdfplumber.strip(),
        "pypdf2_text": text_pypdf2.strip(),
        "ocr_text": text_ocr.strip(),
        "raw_text": combined_text,
    }


def _extract_image_text(file_bytes):
    image = Image.open(BytesIO(file_bytes)).convert("L")
    text_ocr = pytesseract.image_to_string(image, config="--oem 3 --psm 6")
    combined_text = clean_final_text(text_ocr)

    return {
        "pdfplumber_text": "",
        "pypdf2_text": "",
        "ocr_text": text_ocr.strip(),
        "raw_text": combined_text,
    }


def extract_text(file_path):
    parsed = parse_medical_file(file_path)
    return parsed.get("raw_text", "")


def extract_report_date(text):
    patterns = [
        r"(?:report date|date of report|reported on)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})",
        r"(?:report date|date of report|reported on)\s*[:\-]?\s*(\d{4}[/-]\d{2}[/-]\d{2})",
        r"(?:report date|date of report|reported on)\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        r"(\d{2}[/-]\d{2}[/-]\d{4})",
        r"(\d{4}[/-]\d{2}[/-]\d{2})",
        r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue

        raw = match.group(1).replace("-", "/")
        for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y", "%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue

    return datetime.today().date()


def extract_report_sections(text):
    sections = {}
    current_header = None
    buffer = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        normalized = line.rstrip(":").lower()
        if normalized in SECTION_HEADERS:
            if current_header and buffer:
                sections[current_header] = " ".join(buffer).strip()
            current_header = SECTION_HEADERS[normalized]
            buffer = []
            continue

        matched_inline = False
        for _, header in SECTION_HEADERS.items():
            prefix = f"{header}:"
            if line.lower().startswith(prefix.lower()):
                if current_header and buffer:
                    sections[current_header] = " ".join(buffer).strip()
                current_header = header
                value = line[len(prefix):].strip()
                buffer = [value] if value else []
                matched_inline = True
                break

        if matched_inline:
            continue

        if current_header:
            buffer.append(line)

    if current_header and buffer:
        sections[current_header] = " ".join(buffer).strip()

    return sections


def detect_report_type(sections, text):
    clinical_markers = ["Diagnosis", "Treatment", "Chief Complaint", "Clinical Examination"]
    if any(sections.get(marker) for marker in clinical_markers):
        diagnosis = (sections.get("Diagnosis", "") + " " + sections.get("Investigations", "")).lower()
        if any(word in diagnosis for word in ["hemorrhage", "stroke", "fracture", "tumor", "icu", "neurology"]):
            return "clinical"
        return "clinical"

    lowered = text.lower()
    if any(word in lowered for word in ["hemorrhage", "acute intracerebral", "icu care", "gcs", "motor function"]):
        return "clinical"

    return "lab"


def parse_medical_text(text, report_date):
    return []


def parse_medical_file(file_path):
    file_path_obj = Path(file_path)
    file_bytes = file_path_obj.read_bytes()

    if file_path_obj.suffix.lower() in IMAGE_EXTENSIONS:
        extracted = _extract_image_text(file_bytes)
    else:
        extracted = _extract_pdf_text(file_bytes)

    raw_text = extracted.get("raw_text", "")
    sections = extract_report_sections(raw_text)
    report_type = detect_report_type(sections, raw_text) if raw_text else "unknown"
    report_date = extract_report_date(raw_text) if raw_text else None

    return {
        "records": [],
        "raw_text": raw_text,
        "sections": sections,
        "report_type": report_type,
        "report_date": report_date,
        "pdfplumber_text": extracted.get("pdfplumber_text", ""),
        "pypdf2_text": extracted.get("pypdf2_text", ""),
        "ocr_text": extracted.get("ocr_text", ""),
    }


def parse_medical_pdf(pdf_path):
    return parse_medical_file(pdf_path)

