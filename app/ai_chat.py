# app/ai_chat.py
from typing import List, Dict
from app.elasticsearch_utils import search as es_search, check_connection
from app.vertex_utils import summarize_text  # użyjemy go jako stabilnego generatora (Gemini/Bison)
from app.pdf_utils import extract_text_from_pdf
from pathlib import Path

SYSTEM_RULES = (
    "You are a helpful assistant for Q&A over a document collection. "
    "Answer concisely and ONLY from the provided context. "
    "If the answer is not in the context, say you don't know."
)

def get_context_for_query(query: str, k: int = 5) -> List[Dict]:
    """
    Pobierz top-k dokumentów z ES. Jeśli ES niedostępny, kontekst = pusty.
    """
    if not check_connection():
        return []

    results = es_search(query) or []
    # Bierzemy filename + summary (jeśli brak summary, spróbujmy krótki preview)
    ctx = []
    for r in results[:k]:
        ctx.append({
            "filename": r.get("filename", "unknown"),
            "summary": r.get("summary", "") or r.get("content", "")[:600]
        })
    return ctx

def build_prompt(question: str, context_docs: List[Dict]) -> str:
    """
    Zbuduj prompt: system rules + pozycje kontekstu + pytanie.
    """
    context_block = "\n".join(
        f"- [{i+1}] {d['filename']}: {d['summary']}"
        for i, d in enumerate(context_docs)
    ) or "(no context)"

    prompt = (
        f"{SYSTEM_RULES}\n\n"
        f"CONTEXT:\n{context_block}\n\n"
        f"QUESTION: {question}\n\n"
        f"Answer in the language of the question. Provide a concise answer."
    )
    return prompt

def answer_question(question: str) -> Dict:
    """
    Zwraca: { 'answer': str, 'sources': [filenames] }
    """
    ctx = get_context_for_query(question, k=5)
    prompt = build_prompt(question, ctx)
    answer = summarize_text(prompt, max_length=600) or "I don't know based on the available context."
    sources = [d["filename"] for d in ctx]
    return {"answer": answer, "sources": sources}