# ── Python Backend — FastAPI + LangGraph ──────────────────────────────────────
FROM python:3.12-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        libsqlite3-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorios necesarios
RUN mkdir -p /app/outputs /app/data

EXPOSE 8000
EXPOSE 8501

# Comando por defecto (puede ser sobreescrito en docker-compose.yml)
CMD ["uvicorn", "api.slack_webhook:app", "--host", "0.0.0.0", "--port", "8000"]
