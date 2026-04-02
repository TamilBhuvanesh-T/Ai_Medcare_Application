from backend.rag.chunker import chunk_text
from backend.rag.embedder import Embedder

text = """
Total Cholesterol is 240 mg/dL which is above the normal range.
LDL cholesterol is elevated.
HDL cholesterol is lower than recommended.
Triglycerides are also high.
"""

chunks = chunk_text(text, chunk_size=20, overlap=5)

embedder = Embedder()
embeddings = embedder.embed_chunks(chunks)

print("Embedding shape:", embeddings.shape)
print("Sample vector (first 5 values):", embeddings[0][:5])
