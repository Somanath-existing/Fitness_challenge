# ── Stage 1: Build dependencies ───────────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /app

# System deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runner
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser

# Copy installed packages from builder to appuser home
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

COPY . .
RUN chown -R appuser:appuser /app /home/appuser/.local

USER appuser

EXPOSE 3001

# Run migrations, seed if empty, then start server (uses Render's injected $PORT)
CMD ["sh", "-c", "alembic upgrade head && python seed.py && uvicorn main:app --host 0.0.0.0 --port ${PORT:-3001} --workers 2"]
