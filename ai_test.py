from app.pdf_utils import extract_text_from_pdf
from app.ai_utils import analyze_pdf, detect_language
from pathlib import Path

# Ścieżka do testowego PDF-a
pdf_path = Path("uploaded_pdfs/test.pdf")

print("🚀 Test AI analizy PDF")
print("📄 Plik:", pdf_path.resolve())

# 1️⃣ Ekstrakcja tekstu (OCR / PyPDF2)
text = extract_text_from_pdf(pdf_path)
print("\n🧩 Fragment tekstu:")
print(text[:400])
print(f"\n📄 Długość tekstu: {len(text)} znaków")

# 2️⃣ Detekcja języka
language = detect_language(text)
print(f"\n🌍 Wykryty język: {language}")

# 3️⃣ Analiza i streszczenie przez Vertex AI
print("\n🧠 Generuję streszczenie z Vertex AI...")
summary = analyze_pdf(pdf_path)

print("\n✅ Wygenerowane streszczenie:\n")
print(summary)

print("\n🎉 Test zakończony.")
