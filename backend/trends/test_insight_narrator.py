from backend.trends.insight_narrator import generate_health_narrative

trend_data = """
LDL Cholesterol: Decreasing (180 → 150)
HDL Cholesterol: Increasing (35 → 40)
"""

knn_data = """
Dominant Pattern: Moderate Risk
Distribution:
- Moderate Risk: 1
- High Risk: 1
- Low Risk: 1
"""

narrative = generate_health_narrative(trend_data, knn_data)

print("\n=== HEALTH NARRATIVE ===\n")
print(narrative)
