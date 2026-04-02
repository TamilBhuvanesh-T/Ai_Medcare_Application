from dataclasses import dataclass
from datetime import date

@dataclass
class LabRecord:
    parameter: str
    value: float
    unit: str
    test_date: date
