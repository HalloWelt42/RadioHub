# RadioHub in einem Container wie in der Vorlage des Appkerns (gebaut auf dem Pi von tools/ausrollen.sh): das Backend
# liefert die gebaute Oberfläche selbst aus. Gebaut aus dem Wurzelordner, damit version.json, die einzige Quelle der
# Fassung, in beide Stufen kommt.

# --- Oberfläche bauen ------------------------------------------------------------------------------------------------
FROM node:22-slim AS oberflaeche
# git für die Oberfläche des Appkerns von GitHub (wie in der Vorlage des Appkerns), über https statt ssh
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/* && \
    git config --global url."https://github.com/".insteadOf "ssh://git@github.com/" && \
    git config --global --add url."https://github.com/".insteadOf "git@github.com:"
WORKDIR /bau
COPY version.json ./
# Abhängigkeiten genau nach package-lock.json; Schriften und Symbole kommen über npm, nichts aus dem Netz zur Laufzeit.
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci --no-audit --no-fund
COPY frontend ./frontend
RUN cd frontend && npm run build

# --- Backend ----------------------------------------------------------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 RADIOHUB_DATEN=/data RADIOHUB_SICHERUNGEN=/sicherungen HOME=/tmp
WORKDIR /app
# FFmpeg für Aufnahme, Zeitversatz, Schnitt, Wellenform und Zeitansage
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
# Fassung, Backend und Oberfläche wie im Repo (app/fassung.py findet version.json oberhalb des Pakets, app/main.py die
# Oberfläche unter frontend/dist)
COPY version.json ./
COPY backend/app ./backend/app
COPY --from=oberflaeche /bau/frontend/dist ./frontend/dist
WORKDIR /app/backend
# Nicht als root (der Nutzer pi, 1000, besitzt die Daten auf dem Pi); ohne eigenes Heimverzeichnis, darum HOME in /tmp
USER 1000:1000
# Nur im Netz der Container; TLS macht der Vorschaltdienst (deploy/Caddyfile), er reicht die Adresse des Aufrufers weiter
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
