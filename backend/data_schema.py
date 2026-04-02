from dataclasses import dataclass
from datetime import date

@dataclass
class MedicalRecord:
    test_name: str
    value: float
    unit: str
    reference_range: str
    report_date: date
