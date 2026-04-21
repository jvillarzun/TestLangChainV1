# ── Base ───────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

# ── System dependencies ────────────────────────────────────────────────────────
# gcc / libpq-dev  → psycopg2-binary (por si se migra a Postgres)
# libsqlite3-dev   → sqlite3 nativo
# curl             → healthchecks opcionales
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        libsqlite3-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Persistent data directories ───────────────────────────────────────────────
# Los volúmenes de docker-compose se montan aquí; creamos los dirs por si acaso.
RUN mkdir -p /app/outputs /app/data

# ── Ports ─────────────────────────────────────────────────────────────────────
EXPOSE 8000
EXPOSE 8501

# ── Entrypoint flexible ───────────────────────────────────────────────────────
# CMD por defecto: API. docker-compose.yml lo sobreescribe por servicio.
# Para correr ad-hoc: docker run <image> python main.py
CMD ["uvicorn", "api.slack_webhook:app", "--host", "0.0.0.0", "--port", "8000"]
