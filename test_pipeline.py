from backend.pipeline import run_full_pipeline

result = run_full_pipeline()

print("\n=== SUMMARY ===")
print(result["summary"])

print("\n=== RISK ===")
print(result["risk"])

print("\n=== TRENDS ===")
for k,v in result["trends"].items():
    print(k, ":", v)

print("\n=== NARRATIVE ===")
print(result["narrative"])
