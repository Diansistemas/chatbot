#!/bin/bash
#=============================================================================
# Dockerización Automática - Chatbot Django con spaCy y Ollama
#=============================================================================
# Este script construye y levanta el contenedor completo con:
# - Build optimizado con capa de dependencias cacheada
# - Bootstrap setup (migrations + data import + spaCy training + modelfiles)
# - Servicio web con gunicorn + gthread
# - Ollama con modelo llama3.2
#=============================================================================

set -e

echo "=========================================="
echo "  Dockerización Automática - Chatbot"
echo "=========================================="

# 1. Build de la imagen
echo ""
echo ">>> [1/6] Building Docker image..."
docker build -t chatbot-app .

# 2. Levantar Ollama primero (necesario para setup y web)
echo ""
echo ">>> [2/6] Starting Ollama service..."
docker compose up -d ollama
echo "   Esperando que Ollama esté listo..."
docker compose exec ollama ollama list

# 3. Descargar modelo Llama
echo ""
echo ">>> [3/6] Downloading Llama model..."
docker compose up --force-recreate ollama-init

# 4. Ejecutar setup (migrations + data import + spaCy training + modelfiles)
echo ""
echo ">>> [4/6] Running setup (migrations + data + training + modelfiles)..."
docker compose up --force-recreate setup

# 5. Levantar el servicio web
echo ""
echo ">>> [5/6] Starting web service..."
docker compose up -d web

# 6. Verificar que todo funciona
echo ""
echo ">>> [6/6] Verifying deployment..."
echo "   Checking web service..."
docker compose ps

echo ""
echo "=========================================="
echo "  ¡Dockerización completada!"
echo "  El chatbot estará disponible en:"
echo "  - HTTP:      http://localhost:8000"
echo "  - Admin Django: http://localhost:8000/admin"
echo "  - Ollama:    ollama list (desde el contenedor)"
echo "=========================================="