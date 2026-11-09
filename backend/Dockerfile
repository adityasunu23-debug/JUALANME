# backend/Dockerfile — FastAPI backend image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first for better layer caching.
# (backend/.dockerignore keeps .venv / __pycache__ / data out of the context.)
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app /app/app

# Non-root runtime user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
