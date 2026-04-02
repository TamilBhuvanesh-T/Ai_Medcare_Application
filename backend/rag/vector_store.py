import faiss
import numpy as np
import os

from backend.rag.chunker import chunk_text
from backend.rag.embedder import embed_texts
from backend.pdf_parser import extract_text

VECTOR_DIR = "medical_data/vectors"
PDF_DIR = "medical_data/pdfs"

os.makedirs(VECTOR_DIR, exist_ok=True)


class VectorStore:
    """
    FAISS-backed vector store with medical evidence tracking.
    Stores semantic vectors + full chunk metadata (text, source, date).
    """

    def __init__(self, embedding_dim: int):
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.chunks = []   # each entry = {text, source, date, chunk_id}

    def add(self, embeddings: np.ndarray, chunks: list):
        if len(embeddings) != len(chunks):
            raise ValueError("Embeddings and chunks length mismatch")

        self.index.add(embeddings)
        self.chunks.extend(chunks)

    def search(self, query_embedding: np.ndarray, top_k: int = 5):
        if self.index.ntotal == 0:
            return []

        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for idx in indices[0]:
            if 0 <= idx < len(self.chunks):
                results.append(self.chunks[idx])

        return results


from backend.pdf_parser import extract_text, parse_medical_file


def build_vector_store(pdf_paths=None):
    all_chunks = []

    if pdf_paths is None:
        pdf_candidates = [
            os.path.join(PDF_DIR, file)
            for file in os.listdir(PDF_DIR)
            if file.lower().endswith(".pdf")
        ]
    else:
        pdf_candidates = list(pdf_paths)

    for pdf_path in pdf_candidates:
        file = os.path.basename(pdf_path)

        try:
            text = extract_text(pdf_path)
            parsed = parse_medical_file(pdf_path)
            report_date = parsed.get("report_date")

            if not parsed.get("raw_text"):
                continue

        except Exception as e:
            print(f"[WARN] Failed {file}: {e}")
            continue

        chunks = chunk_text(text, source_file=file, report_date=report_date)
        all_chunks.extend(chunks)

    if not all_chunks:
        return None

    embeddings = embed_texts([c["text"] for c in all_chunks])

    store = VectorStore(embedding_dim=embeddings.shape[1])
    store.add(embeddings, all_chunks)

    faiss.write_index(store.index, os.path.join(VECTOR_DIR, "medical.index"))
    np.save(os.path.join(VECTOR_DIR, "chunks.npy"), np.array(all_chunks, dtype=object))

    print(f"[OK] Vector store rebuilt with real medical dates")

    return store




def load_vector_store(embedding_dim: int):
    """
    Loads FAISS index + chunk metadata from disk.
    """

    index_path = os.path.join(VECTOR_DIR, "medical.index")
    meta_path = os.path.join(VECTOR_DIR, "chunks.npy")

    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        print("[INFO] No existing vector store found.")
        return None

    index = faiss.read_index(index_path)
    chunks = np.load(meta_path, allow_pickle=True).tolist()

    store = VectorStore(embedding_dim)
    store.index = index
    store.chunks = chunks

    print(f"[OK] Loaded vector store with {len(chunks)} chunks")
    return store
