#!/bin/bash
#=============================================================================
# Dockerización Automática - Chatbot Django con spaCy y Ollama
#=============================================================================
# Pasos:
#   1) Asistente de configuración (pide los datos y escribe .env)
#   2) Build de la imagen
#   3) Ollama arriba
#   4) Descarga del modelo de Ollama
#   5) Bootstrap (migraciones + datos + entrenamiento spaCy + modelfiles)
#   6) Servicio web con gunicorn + gthread
#   7) Verificación
#
# Uso:
#   ./docker_setup.sh              # normal (pregunta si hay que configurar)
#   ./docker_setup.sh --config     # forzar la reconfiguración del .env
#   ./docker_setup.sh --sin-config # no lanzar el asistente de configuración
#=============================================================================

set -e

CONFIG_FLAGS=""
SIN_CONFIG=false

for arg in "$@"; do
    case "$arg" in
        --config)
            CONFIG_FLAGS="--fuerza"
            ;;
        --sin-config)
            SIN_CONFIG=true
            ;;
        -h|--help)
            echo "Uso: $0 [--config] [--sin-config]"
            echo "  --config      reconfigurar el .env aunque ya exista"
            echo "  --sin-config  no lanzar el asistente de configuración"
            exit 0
            ;;
        *)
            echo "Opción desconocida: $arg (usa --help)"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "  Dockerización Automática - Chatbot"
echo "=========================================="

if command -v python3 >/dev/null 2>&1; then
    PY=python3
else
    PY=python
fi

# ---------------------------------------------------------------------------
# 1) Configuración: el asistente va pidiendo los datos y escribe .env
# ---------------------------------------------------------------------------
echo ""
echo ">>> [1/7] Configuración del entorno (.env)"
if [ "$SIN_CONFIG" = false ]; then
    $PY configurar_entorno.py $CONFIG_FLAGS
fi

if [ ! -f .env ]; then
    echo "ERROR: no existe .env. Ejecuta: $PY configurar_entorno.py"
    exit 1
fi

# Puerto elegido (para el mensaje final)
WEB_PORT=$(grep -E '^WEB_PORT=' .env | tail -n 1 | cut -d= -f2)
WEB_PORT=${WEB_PORT:-8000}

# ---------------------------------------------------------------------------
# 2) Build de la imagen
echo ""
echo ">>> [2/7] Construyendo la imagen Docker..."
docker build -t chatbot-app .

# 3) Levantar Ollama primero (necesario para setup y web)
echo ""
echo ">>> [3/7] Arrancando Ollama..."
docker compose up -d ollama
echo "   Esperando que Ollama esté listo..."
docker compose exec ollama ollama list

# 4) Descargar el modelo de Ollama (el configurado en .env)
echo ""
echo ">>> [4/7] Descargando el modelo de Ollama..."
docker compose up --force-recreate ollama-init

# 5) Ejecutar setup (migrations + data import + spaCy training + modelfiles)
echo ""
echo ">>> [5/7] Setup (migraciones + datos + entrenamiento + modelfiles)..."
docker compose up --force-recreate setup

# 6) Levantar el servicio web
echo ""
echo ">>> [6/7] Arrancando el servicio web..."
docker compose up -d web

# 7) Verificar que todo funciona
echo ""
echo ">>> [7/7] Verificando el despliegue..."
docker compose ps

echo ""
echo "=========================================="
echo "  ¡Dockerización completada!"
echo "  El chatbot estará disponible en:"
echo "  - HTTP:         http://localhost:$WEB_PORT"
echo "  - Admin Django: http://localhost:$WEB_PORT/admin"
echo "  - Ollama:       ollama list (desde el contenedor)"
echo "=========================================="
