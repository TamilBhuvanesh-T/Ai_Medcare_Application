from backend.pdf_parser import extract_text, parse_medical_text
from backend.summary_engine import generate_extended_summary
from datetime import datetime

text = extract_text("data/pdfs/lipid_2024.pdf")
records = parse_medical_text(text, datetime(2024, 1, 15))

result = generate_extended_summary(records)

print(result["summary"])
print("\nRecommendation:")
print(result["recommendation"])
