from pdf2image import convert_from_bytes
import streamlit as st
import pdfplumber
from PyPDF2 import PdfReader
import pytesseract
from PIL import Image
import google.generativeai as genai
from backend.llm_engine import run_llm
import re
import unicodedata

# 🔒 Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

st.title("📄 Smart PDF & Image Parser (Text + OCR + AI)")

# ✅ Allow PDF + Images
uploaded_file = st.file_uploader("Upload File", type=["pdf", "png", "jpg", "jpeg"])


def clean_final_text(text):
    allowed = r'[^a-zA-Z0-9\s.,:/()\-\n]'
    text = re.sub(allowed, ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


combined_text = ""

if uploaded_file:

    file_type = uploaded_file.type

    text_pdfplumber = ""
    text_pypdf2 = ""
    text_ocr = ""

    # =========================
    # 📄 PDF PROCESSING
    # =========================
    if file_type == "application/pdf":

        # ---------- pdfplumber ----------
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text_pdfplumber += page.extract_text() or ""
    
        # ---------- PyPDF2 ----------
        uploaded_file.seek(0)
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            text_pypdf2 += page.extract_text() or ""
    
        # ---------- OCR ----------
        uploaded_file.seek(0)
        images = convert_from_bytes(
            uploaded_file.read(),
            poppler_path=r"C:\poppler-25.12.0\Library\bin"
        )
    
        for i, img in enumerate(images):
            page_text = pytesseract.image_to_string(img, config="--oem 3 --psm 6")
            text_ocr += f"\n--- Page {i+1} ---\n{page_text}"
    
        # ---------- Display ----------
        st.subheader("📄 pdfplumber Output")
        st.text_area("pdfplumber", text_pdfplumber, height=200)
    
        st.subheader("📄 PyPDF2 Output")
        st.text_area("pypdf2", text_pypdf2, height=200)

    # =========================
    # 🖼️ IMAGE PROCESSING
    # =========================
    elif file_type in ["image/png", "image/jpeg", "image/jpg"]:

        image = Image.open(uploaded_file)

        # Optional preprocessing (better OCR)
        image = image.convert("L")

        text_ocr = pytesseract.image_to_string(image, config="--oem 3 --psm 6")

        st.image(image, caption="Uploaded Image", use_column_width=True)

        # =========================
        # 📸 OCR OUTPUT
        # =========================
        st.subheader("📸 OCR Output")
        st.text_area("ocr", text_ocr, height=300)

    # Combine text
    final_text = text_pdfplumber + text_pypdf2
    cleaned_versions = clean_final_text(final_text)
    combined_text = text_ocr + cleaned_versions
    
        # =========================
        # 🤖 AI ANALYSIS
        # =========================
    if st.button("🧠 Analyze with Local AI"):
    
            if not combined_text.strip():
                st.warning("⚠️ No content to analyze")
            else:
                with st.spinner("Thinking... 🤖"):
    
                    # 🔹 Summary Prompt
                    prompt = f"""
                    You are a document analysis AI.
    
                    Read the below content carefully and give:
                        1. Clear summary
                        2. Key points
                        3. Important details only from the document
    
                        If the content is unclear, say "Content not clear".
    
                        DOCUMENT:
                            {combined_text[:3000]}
                            """
    
                    ai_output = run_llm(prompt)
    
                    st.subheader("🤖 AI Output")
                    st.text_area("Result", ai_output, height=300)
    
                    # 🔹 Lab Extraction Prompt
                    test_prompt = f"""
                    You are a lab specialist analysis AI.
    
                    Read the below content and extract:
                        - Test names
                        - Their exact values (DO NOT modify)
    
                        Return ONLY in JSON format like:
                            {{
                                "test_name1": "13.5 g/dL",
                                "test_name2": "5600 cells/mcL"
                            }}
    
                            If unclear, return "Content not clear".
    
                            DOCUMENT:
                                {combined_text[:3000]}
                                """
    
                    test_values = run_llm(test_prompt)
    
                    st.subheader("🧪 Extracted Test Values")
                    st.text_area("values", test_values, height=300)