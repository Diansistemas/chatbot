#!/bin/bash
# 
# Instalador automático del Chatbot DianSistemas para Linux/macOS
# Uso: ./install.sh [opciones]
# Opciones:
#   --skip-nlp-train    Saltar entrenamiento del modelo NLP (tarda ~10 min)
#   --skip-llm-load     Saltar carga de modelos LLM en Ollama
#   --dev               Modo desarrollo (DEBUG=True, SQLite)
#   --help              Mostrar esta ayuda

set -e  # Salir si hay error

REPO_URL="https://github.com/josecursoprogramacion-coder/Chatbot.git"
TARGET_DIR="./Chatbot"
PYTHON_VERSION="3.10"
SKIP_NLP_TRAIN=false
SKIP_LLM_LOAD=false
DEV_MODE=false
USE_DOCKER=false

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-nlp-train)
            SKIP_NLP_TRAIN=true
            shift
            ;;
        --skip-llm-load)
            SKIP_LLM_LOAD=true
            shift
            ;;
        --use-docker)
            USE_DOCKER=true
            shift
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        --help)
            echo "Uso: $0 [opciones]"
            echo "Opciones:"
            echo "  --skip-nlp-train    Saltar entrenamiento del modelo NLP"
            echo "  --skip-llm-load     Saltar carga de modelos LLM en Ollama"
            echo "  --use-docker        Usar Docker (build + docker-compose up)"
            echo "  --dev               Modo desarrollo"
            echo "  --help              Mostrar esta ayuda"
            exit 0
            ;;
        *)
            echo "Opción desconocida: $1"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}  INSTALADOR CHATBOT DIANSISTEMAS (Linux/macOS)${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""

# Función para logging
log_step() {
    echo -e "${YELLOW}[${1}/8] ${2}${NC}"
}

log_ok() {
    echo -e "${GREEN}  ✓ ${1}${NC}"
}

log_warn() {
    echo -e "${YELLOW}  ⚠ ${1}${NC}"
}

log_error() {
    echo -e "${RED}  ✗ ${1}${NC}"
}

# Verificar prerrequisitos
log_step 1 "Verificando prerrequisitos..."

errors=()

# Git
if ! command -v git &> /dev/null; then
    errors+=("Git no está instalado. Instálalo: sudo apt install git / brew install git")
else
    log_ok "Git: $(git --version)"
fi

# Python
PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        errors+=("Python $PYTHON_VERSION+ no está instalado. Instálalo: sudo apt install python3 / brew install python")
    fi
fi
if [ ${#errors[@]} -eq 0 ]; then
    log_ok "Python: $($PYTHON_CMD --version)"
fi

# pip
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    errors+=("pip no está instalado. Instálalo: sudo apt install python3-pip / brew install pip")
fi

# Ollama (opcional)
if command -v ollama &> /dev/null; then
    log_ok "Ollama: $(ollama --version)"
else
    log_warn "Ollama no encontrado (necesario para LLM). Instálalo desde https://ollama.ai/"
fi

# Verificar versión de Python
PY_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.10"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PY_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    log_warn "Python $PY_VERSION detectado. Se recomienda $REQUIRED_VERSION+"
fi

if [ ${#errors[@]} -gt 0 ]; then
    echo -e "\n${RED}ERRORES:${NC}"
    for err in "${errors[@]}"; do
        echo -e "${RED}  - $err${NC}"
    done
    exit 1
fi

# Clonar repositorio
log_step 2 "Clonando repositorio..."
if [ -d "$TARGET_DIR" ]; then
    log_warn "Directorio $TARGET_DIR ya existe. Actualizando..."
    cd "$TARGET_DIR"
    git pull origin main
else
    git clone "$REPO_URL" "$TARGET_DIR"
    cd "$TARGET_DIR"
fi
log_ok "Repositorio en: $(pwd)"

# Crear entorno virtual
log_step 3 "Creando entorno virtual..."
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    $PYTHON_CMD -m venv "$VENV_DIR"
    log_ok "Entorno virtual creado"
else
    log_warn "Entorno virtual ya existe"
fi

# Activar entorno virtual
source "$VENV_DIR/bin/activate"

# Actualizar pip
log_step 4 "Instalando dependencias Python..."
pip install --upgrade pip -q
pip install -r requirements.txt
log_ok "Dependencias instaladas"

# Configurar .env con el asistente (va pidiendo los datos para configurarse)
log_step 5 "Configurando variables de entorno (asistente interactivo)..."
if command -v python3 &> /dev/null; then
    PY=python3
else
    PY=python
fi
if [ -f "configurar_entorno.py" ]; then
    $PY configurar_entorno.py || { log_error "Configuracion cancelada"; exit 1; }
    log_ok ".env configurado con el asistente"
elif [ ! -f ".env" ] && [ -f ".env.example" ]; then
    # Respaldo: copia de la plantilla si no esta el asistente
    cp ".env.example" ".env"
    log_ok ".env creado desde .env.example (editalo a mano)"
else
    log_warn ".env ya existe"
fi

# Migraciones y base de datos
log_step 6 "Configurando base de datos..."
python manage.py migrate
log_ok "Migraciones aplicadas"

# Cargar datos iniciales
log_step 7 "Cargando datos iniciales..."
python manage.py cargar_datos_iniciales
log_ok "Datos iniciales cargados"

# Entrenar modelo NLP (opcional)
if [ "$SKIP_NLP_TRAIN" = false ]; then
    log_step 8 "Entrenando modelo NLP (esto tarda ~10 min)..."
    python manage.py cargar_nlp --limpiar
    python manage.py generar_nlp
    python -m spacy train "./entrenamiento/spacy/config.cfg" --paths.train "./entrenamiento/spacy/train.spacy" --paths.dev "./entrenamiento/spacy/dev.spacy" --output "./entrenamiento/spacy/modelo"
    log_ok "Modelo NLP entrenado"
else
    log_warn "Saltando entrenamiento NLP (usa --skip-nlp-train para omitir)"
fi

# Cargar modelos LLM en Ollama (opcional)
if [ "$SKIP_LLM_LOAD" = false ] && command -v ollama &> /dev/null; then
    log_step 8 "Cargando modelos LLM en Ollama..."
    python manage.py cargar_llm
    log_ok "Modelos LLM cargados"
fi

# Opción Docker: Build y levantar con docker-compose
if [ "$USE_DOCKER" = true ]; then
    log_step 8 "Construyendo imagen y levantando contenedores con Docker..."
    
    # Puerto configurado en .env por el asistente (por defecto 8000)
    WEB_PORT=$(grep -E '^WEB_PORT=' .env 2>/dev/null | tail -n 1 | cut -d= -f2)
    WEB_PORT=${WEB_PORT:-8000}
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        log_warn "Docker no está instalado. Saltando opción Docker."
    elif ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_warn "docker-compose no está disponible. Saltando opción Docker."
    else
        # Usar docker compose (v2) o docker-compose (v1)
        if docker compose version &> /dev/null; then
            DC="docker compose"
        else
            DC="docker-compose"
        fi
        
        log_step 8 "  [1/3] Construyendo imagen..."
        $DC build
        
        log_step 8 "  [2/3] Levantando servicios (setup + web + ollama)..."
        $DC up -d
        
        log_step 8 "  [3/3] Esperando a que setup termine..."
        # Esperar a que setup termine (máx 5 min)
        timeout=300
        start=$(date +%s)
        while [ $(($(date +%s) - start)) -lt $timeout ]; do
            status=$($DC ps --format "table {{.Service}}\t{{.Status}}" 2>/dev/null | grep setup || true)
            if echo "$status" | grep -q "Exited (0)"; then
                log_ok "Setup completado exitosamente"
                break
            elif echo "$status" | grep -q "Exited ("; then
                log_error "Setup falló. Revisa logs con: $DC logs setup"
                break
            fi
            sleep 5
        done
        
        log_ok "Docker levantado. Web en http://localhost:$WEB_PORT"
        log_warn "Ver logs: $DC logs -f web"
    fi
fi

# Crear script de inicio rápido
cat > start_chatbot.sh << 'EOF'
#!/bin/bash
echo "Iniciando Chatbot DianSistemas..."
source venv/bin/activate
python manage.py runserver 127.0.0.1:8000
EOF
chmod +x start_chatbot.sh
log_ok "Script de inicio creado: ./start_chatbot.sh"

# Resumen final
echo -e "\n${CYAN}==========================================${NC}"
echo -e "${CYAN}  INSTALACIÓN COMPLETADA${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""
if [ "$USE_DOCKER" = true ]; then
    echo -e "${YELLOW}Docker levantado. Servicios:${NC}"
    echo -e "  - Web: ${GREEN}http://localhost:$WEB_PORT${NC}"
    echo -e "  - Admin: ${GREEN}http://localhost:$WEB_PORT/admin/${NC}"
    echo -e "  - Ollama: ${GREEN}http://localhost:11434${NC}"
    echo ""
    echo -e "${YELLOW}Comandos útiles:${NC}"
    echo -e "  Ver logs:    ${GREEN}docker compose logs -f web${NC}"
    echo -e "  Parar:       ${GREEN}docker compose down${NC}"
    echo -e "  Reiniciar:   ${GREEN}docker compose restart web${NC}"
    echo -e "  Rebuild:     ${GREEN}docker compose build --no-cache && docker compose up -d${NC}"
else
    echo -e "${YELLOW}Próximos pasos:${NC}"
    echo "  1. Edita .env con tus configuraciones reales"
    echo "  2. (Opcional) Inicia smtp4dev para emails de prueba (ver docs)"
    echo "  3. (Opcional) Inicia Ollama si no está corriendo:"
    echo "     ollama serve"
    echo "  4. Inicia el servidor:"
    echo -e "     ${GREEN}./start_chatbot.sh${NC}"
    echo ""
    echo -e "  Luego abre: ${CYAN}http://127.0.0.1:8000/chat/${NC}"
    echo -e "  Admin: ${CYAN}http://127.0.0.1:8000/admin/${NC}"
fi
echo ""
echo -e "${YELLOW}Documentación completa en README.md${NC}"