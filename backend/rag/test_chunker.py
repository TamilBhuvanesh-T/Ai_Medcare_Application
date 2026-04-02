from backend.rag.chunker import chunk_text

sample_text = """
Total Cholesterol is 240 mg/dL which is above the normal range.
LDL cholesterol is elevated.
HDL cholesterol is lower than recommended.
Triglycerides are also high.
This indicates a risk for cardiovascular disease.
"""

chunks = chunk_text(sample_text, chunk_size=20, overlap=5)

for c in chunks:
    print(f"\nChunk {c['chunk_id']}:")
    print(c['text'])
