from backend.rag.chunker import chunk_text
from backend.rag.embedder import Embedder
from backend.rag.vector_store import VectorStore
from backend.rag.qa_engine import answer_question

text = """
Total Cholesterol is 240 mg/dL which is above the normal range.
LDL cholesterol is elevated.
HDL cholesterol is lower than recommended.
Triglycerides are also high.
"""

chunks = chunk_text(text, chunk_size=20, overlap=5)

embedder = Embedder()
embeddings = embedder.embed_chunks(chunks)

store = VectorStore(embedding_dim=embeddings.shape[1])
store.add(embeddings, chunks)

question = "Should I be worried about my cholesterol levels?"
query_embedding = embedder.model.encode([question])
relevant_chunks = store.search(query_embedding, top_k=3)

answer = answer_question(relevant_chunks, question)
print("\n=== ANSWER ===\n")
print(answer)
