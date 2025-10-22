FROM python:3.11-slim

# Ustaw folder roboczy
WORKDIR /app

# Skopiuj wymagania
COPY requirements.txt .

# Zainstaluj zależności
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj resztę projektu
COPY . .

# Ustaw zmienne środowiskowe
ENV PORT=8080

# Udostępnij port
EXPOSE 8080

# Uruchom FastAPI (jeśli main.py jest w folderze app/)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]