from app.vertex_utils import summarize_text, generate_embedding
from app.pdf_utils import extract_text_from_pdf
import logging
import re
import random
from collections import Counter
from langdetect import detect, DetectorFactory

logger = logging.getLogger(__name__)
DetectorFactory.seed = 0  # stabilniejsze wyniki

# =============================
# 🧠 ANALIZA PDF
# =============================
def analyze_pdf(path_or_bytes) -> str:
    """Generate a meaningful summary for the document using Vertex AI if available,
    otherwise keyword-based local summary. Automatically matches document language."""
    try:
        # 1️⃣ Extract text
        if isinstance(path_or_bytes, (bytes, bytearray)):
            text = path_or_bytes.decode("utf-8", errors="ignore")
        else:
            text = extract_text_from_pdf(path_or_bytes)

        if not text or len(text.strip()) == 0:
            return "Brak treści w pliku PDF."

        text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
        text = text[:15000]

        # 2️⃣ Detect language
        lang = detect_language(text)
        logger.info(f"[AI] Detected language: {lang}")

        # 3️⃣ Try Vertex AI summary
        prompt_prefix = {
            "pl": "Streść poniższy tekst w kilku zdaniach w języku polskim:",
            "en": "Summarize the following text in English in a few sentences:",
            "de": "Fasse den folgenden Text auf Deutsch in wenigen Sätzen zusammen:",
        }.get(lang, "Summarize the following text briefly:")

        summary = summarize_text(f"{prompt_prefix}\n\n{text}")
        if summary and summary.strip():
            return summary.strip()

        # 4️⃣ Local fallback (keyword-based)
        words = re.findall(r"\b\w{5,}\b", text.lower())
        common = [w for w, _ in Counter(words).most_common(10)]
        keywords = ", ".join(common[:7])

        sentences = re.split(r'(?<=[.!?])\s+', text)
        middle_section = sentences[len(sentences)//3 : len(sentences)//3 + 3]
        preview = " ".join(middle_section)

        if lang == "pl":
            return (
                f"Dokument dotyczy tematów takich jak: {keywords}. "
                f"Opisuje kluczowe zagadnienia, m.in. {common[0] if common else 'temat główny'}. "
                f"Omawia również: {preview[:400].strip()}..."
            )
        elif lang == "en":
            return (
                f"The document covers topics such as: {keywords}. "
                f"It describes key issues like {common[0] if common else 'the main topic'}. "
                f"It also discusses: {preview[:400].strip()}..."
            )
        else:
            return (
                f"Main topics: {keywords}. "
                f"Key point: {common[0] if common else 'main subject'}. "
                f"Excerpt: {preview[:400].strip()}..."
            )

    except Exception as e:
        logger.error(f"[AI] Error analyzing PDF: {e}")
        return "Błąd generowania streszczenia."


# =============================
# 🌍 DETEKCJA JĘZYKA
# =============================
def detect_language(text: str) -> str:
    """Detect dominant language of text, cleaning spacing and diacritics."""
    try:
        if not text or len(text.strip()) < 50:
            return "unknown"

        clean = re.sub(r"[\n\r\t]", " ", text)
        clean = re.sub(r"[^A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż ]", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        lang = detect(clean)
        print(f"[LANG DEBUG RESULT] {lang}")
        return lang
    except Exception as e:
        print(f"[LANG ERROR] {e}")

        if re.search(r"[ĄąĆćĘęŁłŃńÓóŚśŹźŻż]", text):
            return "pl"
        elif re.search(r"[ßüöä]", text):
            return "de"
        elif re.search(r"[àâçéèêëîïôùûüÿœ]", text):
            return "fr"
        else:
            return "unknown"


# =============================
# 🤖 AI SMART FOLDER CLUSTERING
# =============================
def suggest_dynamic_folders(docs: list[dict]) -> list[dict]:
    """Vertex AI-based semantic clustering of documents into folders."""
    from sklearn.cluster import KMeans
    import numpy as np

    if not docs:
        return []

    print("[AI] Step 1: Preparing documents...")

    # Limit for performance
    if len(docs) > 20:
        docs = docs[:20]
        print("[AI] Too many docs, limited to 20 for faster clustering.")

    vectors, filenames, summaries = [], [], []

    print("[AI] Step 2: Generating embeddings...")
    for d in docs:
        text = f"{d.get('filename','')} - {d.get('summary','')}"
        emb = generate_embedding(text)
        if not emb:
            emb = [random.random() for _ in range(256)]  # fallback
        vectors.append(emb)
        filenames.append(d.get("filename"))
        summaries.append(d.get("summary", ""))

    if not vectors:
        print("[AI Folder Clustering] No embeddings available.")
        return [{"folder": "📁 Uncategorized", "files": [d["filename"] for d in docs]}]

    print("[AI] Step 3: Clustering embeddings...")
    n_clusters = min(5, len(vectors))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(vectors)

    clustered = {}
    for label, name, summary in zip(labels, filenames, summaries):
        clustered.setdefault(label, []).append({"name": name, "summary": summary})

    print("[AI] Step 4: Naming folders...")
    folders = []
    for idx, docs_in_cluster in clustered.items():
        text_block = "\n".join(f"- {d['name']}: {d['summary'][:200]}" for d in docs_in_cluster)
        prompt = f"""
        You are an AI assistant that assigns thematic folder names to document groups.
        Suggest a short, clear folder name (max 3 words) describing this group of documents:

        {text_block}

        Return only the folder name, no extra text.
        """
        folder_name = summarize_text(prompt).strip().replace('"', "")
        if not folder_name or len(folder_name) < 3:
            folder_name = f"Category {idx+1}"
        folders.append({
            "folder": folder_name,
            "files": [d["name"] for d in docs_in_cluster],
        })

    # --- 🔹 Ensure "Uncategorized" folder exists ---
    print("[AI] Step 5: Adding Uncategorized folder if needed...")
    all_files = {d["filename"] for d in docs}
    clustered_files = {f for c in folders for f in c["files"]}
    uncategorized = list(all_files - clustered_files)

    if uncategorized:
        folders.append({
            "folder": "📁 Uncategorized",
            "files": uncategorized
        })
        print(f"[AI] Added Uncategorized folder for {len(uncategorized)} unclassified documents.")

    print("[AI Folder Clustering Result]", folders)
    return folders

# =============================
# 💬 ASK AI (context-aware Q&A in English)
# =============================
def ask_ai(query: str) -> dict:
    """
    Understands the user's question in any language,
    retrieves relevant document summaries from Elasticsearch,
    and generates a natural language answer using Vertex AI.
    """
    from app.elasticsearch_utils import es, ES_INDEX, check_connection
    from app.vertex_utils import summarize_text

    # 1️⃣ Detect language of the query
    lang = detect_language(query)
    print(f"[ASK AI] Detected query language: {lang}")

    # 2️⃣ Check Elasticsearch connection
    if not check_connection():
        return {"answer": "❌ Elasticsearch is not available.", "sources": []}

    # 3️⃣ Retrieve top matching documents from Elasticsearch
    try:
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["filename^3", "summary^2", "content"],
                    "fuzziness": "AUTO"
                }
            },
            "size": 5
        }

        results = es.search(index=ES_INDEX, body=search_body)
        hits = results.get("hits", {}).get("hits", [])
    except Exception as e:
        print(f"[ASK AI ERROR] {e}")
        return {"answer": f"Search error: {e}", "sources": []}

    # 4️⃣ Handle no search results
    if not hits:
        fallback_prompt = f"""
        You are SmartDocFinder AI, an assistant that helps users find information inside their PDF documents.
        The user asked: "{query}"

        No matching documents were found in the index.
        Suggest alternative keywords or explain what type of document might contain the answer.
        Respond in English or in the same language as the question.
        """
        suggestion = summarize_text(fallback_prompt)
        return {
            "answer": suggestion or "No relevant documents were found.",
            "sources": []
        }

    # 5️⃣ Build context for the AI model
    context_text = "\n\n".join(
        f"📄 {h['_source'].get('filename')}\n{h['_source'].get('summary', '')[:600]}"
        for h in hits
    )

    # 6️⃣ Multilingual prompt templates
    prompts = {
        "en": f"""
        You are SmartDocFinder AI – an intelligent assistant that analyzes the user's PDF documents.
        Your task is to answer the question using only the context from the indexed files below.

        🧠 Rules:
        - Respond in English.
        - Base your answer only on the summaries and filenames provided.
        - If you are unsure, mention the most relevant document or say "I'm not completely sure, but...".

        ❓ Question:
        "{query}"

        📚 Document summaries:
        {context_text}

        ✍️ Write a clear, concise answer in English.
        """,
        "pl": f"""
        You are SmartDocFinder AI – an intelligent assistant that analyzes PDF documents.
        Answer the question **in Polish**, using the context from the indexed files below.

        🧠 Rules:
        - If the exact answer is not clear, mention the most related document.
        - Be natural and use short, clear sentences.

        ❓ Question:
        "{query}"

        📚 Document summaries:
        {context_text}

        ✍️ Provide the answer in Polish.
        """,
        "de": f"""
        You are SmartDocFinder AI – an intelligent assistant that analyzes PDF documents.
        Answer in **German**, using the context from the indexed files below.

        ❓ Question:
        "{query}"

        📚 Document summaries:
        {context_text}

        ✍️ Respond naturally and briefly in German.
        """
    }

    # 7️⃣ Choose prompt based on detected language
    prompt_text = prompts.get(lang, prompts["en"])

    # 8️⃣ Ask Vertex AI for an answer
    answer = summarize_text(prompt_text)
    print("🔍 Vertex returned:", repr(answer))

    if not answer or len(answer.strip()) < 5 or "I couldn`t" in answer:
        fallback_sources = [h["_source"].get("filename", "") for h in hits]
        answer = f"Based on your query, I found the following relevant documents: {', '.join(fallback_sources)}."

    # 9️⃣ Prepare list of document sources
    sources = [h["_source"].get("filename", "") for h in hits]

    # 10️⃣ Return structured response
    return {
        "answer": answer.strip(),
        "sources": sources
    }