from collections import defaultdict
from statistics import mean
from datetime import datetime

def analyze_trends(records):
    """
    Builds true time-series from real lab report dates.
    Uses MedicalRecord.report_date coming from PDF parser.
    """

    grouped = defaultdict(list)

    for r in records:
        # Correct field names
        param = r.get("parameter")
        date = r.get("date")   # This is record.report_date from PDF

        if not param or not date:
            continue

        # Convert to datetime if needed
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date)
            except:
                continue

        grouped[param].append((date, r["value"]))

    trends = {}

    for param, rows in grouped.items():
        rows.sort(key=lambda x: x[0])   # sort by date

        dates = [d.strftime("%Y-%m-%d") for d, _ in rows]
        values = [v for _, v in rows]

        if len(values) < 2:
            trend = "Insufficient data"
        elif values[-1] > values[0]:
            trend = "Increasing"
        elif values[-1] < values[0]:
            trend = "Decreasing"
        else:
            trend = "Stable"

        trends[param] = {
            "trend": trend,
            "start": values[0],
            "end": values[-1],
            "average": round(mean(values), 2),
            "dates": dates,
            "values": values
        }

    return trends
