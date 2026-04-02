from datetime import date
from backend.trends.lab_record import LabRecord
from backend.trends.trend_analyzer import analyze_trends

records = [
    LabRecord("LDL Cholesterol", 180, "mg/dL", date(2024, 1, 10)),
    LabRecord("LDL Cholesterol", 165, "mg/dL", date(2024, 3, 12)),
    LabRecord("LDL Cholesterol", 150, "mg/dL", date(2024, 6, 15)),
    LabRecord("HDL Cholesterol", 35, "mg/dL", date(2024, 1, 10)),
    LabRecord("HDL Cholesterol", 40, "mg/dL", date(2024, 6, 15)),
]

trends = analyze_trends(records)

for k, v in trends.items():
    print(f"\n{k}")
    print(v)
