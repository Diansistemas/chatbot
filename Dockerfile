FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps for spacy + mysqlclient fallback
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Non-root user created BEFORE copying the code, so it can write
# train.spacy, modelfiles, etc. inside /app
RUN useradd -m appuser \
    && mkdir -p /data /app/entrenamiento/spacy/modelo /app/staticfiles \
    && chown -R appuser /data /app

WORKDIR /app

# Install dependencies first so this layer is cached between code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the code (appuser will own it via chown below)
COPY --chown=appuser:appuser . .

# Ensure setup.sh is executable (it lives at project root, not in docker/)
RUN chmod +x setup.sh

# Expose the default Django port
EXPOSE 8000

ENTRYPOINT ["./setup.sh"]

# CHANGE "config" to the folder that contains your settings.py / wsgi.py
# gthread + long timeout because LLM answers can take a while
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--worker-class", "gthread", "--workers", "2", "--threads", "4", \
     "--timeout", "300"]