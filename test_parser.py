from backend.pdf_parser import extract_text, parse_medical_text
from datetime import datetime

pdf_path = "data/pdfs/lipid_2024.pdf"

text = extract_text(pdf_path)
records = parse_medical_text(text, datetime(2024, 1, 15))

print("Extracted Records:")
for r in records:
    print(r)
