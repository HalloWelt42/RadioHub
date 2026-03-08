FROM python:3.11-slim

WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python-Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App kopieren
COPY backend/ ./backend/

# Port
EXPOSE 8000

# Start
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
