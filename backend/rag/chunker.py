def chunk_text(text, source_file, report_date, chunk_size=400, overlap=80):
    words = text.split()
    chunks = []

    start = 0
    chunk_id = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        chunks.append({
            "chunk_id": chunk_id,
            "text": chunk_text,
            "source": source_file,
            "date": report_date.isoformat()   # REAL medical date
        })

        chunk_id += 1
        start = end - overlap

    return chunks
