FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Build deps for mysqlclient (only needed once you switch to MySQL, harmless before)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Non-root user created BEFORE copying the code, so it can write
# train.spacy, modelfiles, etc. inside /app
RUN useradd -m appuser \
    && mkdir -p /data /app/modelo /app/staticfiles \
    && chown -R appuser /data /app

WORKDIR /app

# Install dependencies first so this layer is cached between code changes
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=appuser:appuser . .
RUN chmod +x docker/*.sh

USER appuser
EXPOSE 8000
ENTRYPOINT ["./docker/entrypoint.sh"]

# CHANGE "config" to the folder that contains your settings.py / wsgi.py
# gthread + long timeout because LLM answers can take a while
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--worker-class", "gthread", "--workers", "2", "--threads", "4", \
     "--timeout", "300"]