from backend.llm_engine import run_llm
from backend.medical_knowledge import MEDICAL_KNOWLEDGE

QA_PROMPT = """
You are a medical AI assistant.

You have:
1. Verified medical evidence from the user's reports
2. A trusted medical knowledge base
3. A processed case-oriented summary prepared from the uploaded report

Rules:
- Never invent personal medical data
- If the question is about the user's values, use ONLY the evidence
- If the question is about medical meaning, you may use the knowledge base
- Prefer the processed report discussion when it helps explain the user's case more clearly
- Keep the answer very concise
- Use no more than 2 sentences
- Focus only on the user's report-related question
- Never diagnose
- Never prescribe medication

User question:
{question}

Processed case discussion:
{processed_context}

Medical evidence:
{evidence}

Medical knowledge:
{knowledge}

Answer:
"""

def answer_question(context_chunks, question, processed_context=""):

    # Build evidence block
    if context_chunks:
        evidence_text = "\n\n".join(
            f"[{i+1}] {c['text']}\nSource: {c['source']} | Date: {c['date']}"
            for i, c in enumerate(context_chunks)
        )
    else:
        evidence_text = "No personal medical data found."

    # Build medical knowledge block
    knowledge_text = ""
    for key, data in MEDICAL_KNOWLEDGE.items():
        if key.replace("_", " ") in question.lower():
            knowledge_text += (
                f"{key.replace('_',' ').title()}:\n"
                f"{data['description']}\n"
                f"Health impact: {data['impact']}\n\n"
            )

    if not knowledge_text:
        knowledge_text = "General medical knowledge available."

    prompt = QA_PROMPT.format(
        question=question,
        processed_context=processed_context or "No processed case discussion available.",
        evidence=evidence_text,
        knowledge=knowledge_text
    )

    return run_llm(prompt)
