# Backend von RadioHub. Gebaut aus dem Wurzelordner des Repos (docker-compose.yml, compose.pi.yml: context .), damit
# version.json, die einzige Quelle der Fassung, mit ins Abbild kommt.
FROM python:3.12-slim

WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python-Dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App kopieren, die Fassung daneben (app/fassung.py sucht sie oberhalb des Pakets)
COPY version.json ./
COPY backend/app/ ./app/

# Nicht als root (wie die Vorlage des Appkerns: 1000:1000, der Nutzer pi besitzt die Daten auf dem Pi); ohne eigenes
# Heimverzeichnis, darum HOME in /tmp
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
USER 1000:1000

# Nur im Netz der Container (vor der Oberfläche steht der Vorschaltdienst)
EXPOSE 8000

# Start
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
