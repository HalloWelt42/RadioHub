# Backend von RadioHub. Gebaut aus dem Wurzelordner des Repos (docker-compose.yml, compose.pi.yml: context .), damit
# version.json, die einzige Quelle der Fassung, mit ins Abbild kommt.
FROM python:3.11-slim

WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python-Dependencies
COPY radiohub-backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App kopieren, die Fassung daneben (backend/fassung.py sucht sie oberhalb des Pakets)
COPY version.json ./
COPY radiohub-backend/backend/ ./backend/

# Port
EXPOSE 8000

# Start
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
