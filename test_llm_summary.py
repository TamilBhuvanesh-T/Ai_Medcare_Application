from backend.pdf_parser import extract_text, parse_medical_text
from backend.summary_engine import generate_llm_summary
from datetime import datetime

text = extract_text("data/pdfs/lipid_2024.pdf")
records = parse_medical_text(text, datetime(2024, 1, 15))

summary = generate_llm_summary(records)

print("=== LLM GENERATED SUMMARY ===")
print(summary)
