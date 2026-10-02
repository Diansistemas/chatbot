<# 
.SYNOPSIS
    Instalador automático del Chatbot DianSistemas para Windows
.DESCRIPTION
    Clona el repositorio, crea entorno virtual, instala dependencias,
    configura la base de datos y prepara el proyecto para ejecutarse.
.NOTES
    Requiere: Git, Python 3.10+, Ollama instalado y corriendo
#>

param(
    [string]$RepoUrl = "https://github.com/josecursoprogramacion-coder/Chatbot.git",
    [string]$TargetDir = ".\Chatbot",
    [string]$PythonVersion = "3.10",
    [switch]$SkipNlpTrain,
    [switch]$SkipLlmLoad,
    [switch]$DevMode,
    [switch]$UseDocker
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  INSTALADOR CHATBOT DIANSISTEMAS (Windows)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar prerrequisitos
Write-Host "[1/8] Verificando prerrequisitos..." -ForegroundColor Yellow

$errors = @()

# Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    $errors += "Git no está instalado. Instálalo desde https://git-scm.com/"
} else {
    Write-Host "  ✓ Git: $(git --version)" -ForegroundColor Green
}

# Python
$pythonExe = "python"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python3"
}
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $errors += "Python $PythonVersion+ no está instalado. Instálalo desde https://python.org/"
} else {
    $version = & $pythonExe --version 2>&1
    Write-Host "  ✓ Python: $version" -ForegroundColor Green
}

# Ollama (opcional pero recomendado)
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "  ✓ Ollama: $(ollama --version)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Ollama no encontrado (necesario para LLM). Instálalo desde https://ollama.ai/" -ForegroundColor Yellow
}

if ($errors.Count -gt 0) {
    Write-Host "`nERRORES:" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}

# Clonar repositorio
Write-Host "`n[2/8] Clonando repositorio..." -ForegroundColor Yellow
if (Test-Path $TargetDir) {
    Write-Host "  Directorio $TargetDir ya existe. Actualizando..." -ForegroundColor Yellow
    Set-Location $TargetDir
    git pull origin main
} else {
    git clone $RepoUrl $TargetDir
    Set-Location $TargetDir
}
Write-Host "  ✓ Repositorio en: $(Get-Location)" -ForegroundColor Green

# Crear entorno virtual
Write-Host "`n[3/8] Creando entorno virtual..." -ForegroundColor Yellow
$venvDir = "venv"
if (-not (Test-Path $venvDir)) {
    & $pythonExe -m venv $venvDir
    Write-Host "  ✓ Entorno virtual creado" -ForegroundColor Green
} else {
    Write-Host "  Entorno virtual ya existe" -ForegroundColor Yellow
}

# Activar entorno virtual e instalar dependencias
Write-Host "`n[4/8] Instalando dependencias Python..." -ForegroundColor Yellow
$pip = ".\venv\Scripts\pip.exe"
& $pip install --upgrade pip -q
& $pip install -r requirements.txt
Write-Host "  ✓ Dependencias instaladas" -ForegroundColor Green

# Configurar .env con el asistente (va pidiendo los datos para configurarse)
Write-Host "`n[5/8] Configurando variables de entorno (asistente interactivo)..." -ForegroundColor Yellow
if (Test-Path "configurar_entorno.py") {
    & $pythonExe configurar_entorno.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  X Configuracion cancelada." -ForegroundColor Red
        exit 1
    }
    Write-Host "  + .env configurado con el asistente" -ForegroundColor Green
} elseif (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    # Respaldo: copia de la plantilla si no esta el asistente
    Copy-Item ".env.example" ".env"
    Write-Host "  + .env creado desde .env.example (editalo a mano)" -ForegroundColor Yellow
} else {
    Write-Host "  .env ya existe" -ForegroundColor Yellow
}

# Migraciones y base de datos
Write-Host "`n[6/8] Configurando base de datos..." -ForegroundColor Yellow
$python = ".\venv\Scripts\python.exe"
& $python manage.py migrate
Write-Host "  ✓ Migraciones aplicadas" -ForegroundColor Green

# Cargar datos iniciales
Write-Host "`n[7/8] Cargando datos iniciales..." -ForegroundColor Yellow
& $python manage.py cargar_datos_iniciales
Write-Host "  ✓ Datos iniciales cargados" -ForegroundColor Green

# Entrenar modelo NLP (opcional, tarda ~10 min)
if (-not $SkipNlpTrain) {
    Write-Host "`n[8/8] Entrenando modelo NLP (esto tarda ~10 min)..." -ForegroundColor Yellow
    & $python manage.py cargar_nlp --limpiar
    & $python manage.py generar_nlp
    & $python -m spacy train ".\entrenamiento\spacy\config.cfg" --paths.train ".\entrenamiento\spacy\train.spacy" --paths.dev ".\entrenamiento\spacy\dev.spacy" --output ".\entrenamiento\spacy\modelo"
    Write-Host "  ✓ Modelo NLP entrenado" -ForegroundColor Green
} else {
    Write-Host "`n[8/8] Saltando entrenamiento NLP (usa --SkipNlpTrain para omitir)" -ForegroundColor Yellow
}

# Cargar modelos LLM en Ollama (opcional)
if (-not $SkipLlmLoad -and (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "`nCargando modelos LLM en Ollama..." -ForegroundColor Yellow
    & $python manage.py cargar_llm
    Write-Host "  ✓ Modelos LLM cargados" -ForegroundColor Green
}

# Opción Docker: Build y levantar con docker-compose
if ($UseDocker) {
    Write-Host "`n[Docker] Construyendo imagen y levantando contenedores..." -ForegroundColor Yellow
    
    # Puerto configurado en .env por el asistente (por defecto 8000)
    $webPort = "8000"
    if (Test-Path ".env") {
        $m = Select-String -Path ".env" -Pattern '^WEB_PORT=(.+)' | Select-Object -First 1
        if ($m) { $webPort = $m.Matches[0].Groups[1].Value.Trim() }
    }
    
    # Verificar Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "  ⚠ Docker no está instalado. Saltando opción Docker." -ForegroundColor Yellow
    } elseif (-not (Get-Command docker-compose -ErrorAction SilentlyContinue) -and (-not (docker compose version -ErrorAction SilentlyContinue))) {
        Write-Host "  ⚠ docker-compose no está disponible. Saltando opción Docker." -ForegroundColor Yellow
    } else {
        # Usar docker compose (v2) o docker-compose (v1)
        $dc = if (docker compose version -ErrorAction SilentlyContinue) { "docker compose" } else { "docker-compose" }
        
        Write-Host "  [1/3] Construyendo imagen..." -ForegroundColor Yellow
        & $dc build
        
        Write-Host "  [2/3] Levantando servicios (setup + web + ollama)..." -ForegroundColor Yellow
        & $dc up -d
        
        Write-Host "  [3/3] Esperando a que setup termine..." -ForegroundColor Yellow
        # Esperar a que setup termine (máx 5 min)
        $timeout = 300
        $start = Get-Date
        while (((Get-Date) - $start).TotalSeconds -lt $timeout) {
            $status = & $dc ps --format "table {{.Service}}\t{{.Status}}" | Where-Object { $_ -match "setup" }
            if ($status -and $status -match "Exited \(0\)") {
                Write-Host "  ✓ Setup completado exitosamente" -ForegroundColor Green
                break
            } elseif ($status -and $status -match "Exited \([1-9]\)") {
                Write-Host "  ✗ Setup falló. Revisa logs con: $dc logs setup" -ForegroundColor Red
                break
            }
            Start-Sleep -Seconds 5
        }
        
        Write-Host "  ✓ Docker levantado. Web en http://localhost:$webPort" -ForegroundColor Green
        Write-Host "  Ver logs: $dc logs -f web" -ForegroundColor Gray
    }
}

# Crear script de inicio rápido
Write-Host "`nCreando scripts de inicio..." -ForegroundColor Yellow

@"
@echo off
echo Iniciando Chatbot DianSistemas...
call venv\Scripts\activate
python manage.py runserver 127.0.0.1:8000
"@ | Out-File -Encoding ASCII "start_chatbot.bat"

@"
#!/bin/bash
echo "Iniciando Chatbot DianSistemas..."
source venv/bin/activate
python manage.py runserver 127.0.0.1:8000
"@ | Out-File -Encoding UTF8 "start_chatbot.sh"

Write-Host "  ✓ Scripts creados: start_chatbot.bat / start_chatbot.sh" -ForegroundColor Green

# Resumen final
Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "  INSTALACIÓN COMPLETADA" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
if ($UseDocker) {
    Write-Host "Docker levantado. Servicios:" -ForegroundColor Yellow
    Write-Host "  - Web: http://localhost:$webPort" -ForegroundColor White
    Write-Host "  - Admin: http://localhost:$webPort/admin/" -ForegroundColor White
    Write-Host "  - Ollama: http://localhost:11434" -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "Comandos útiles:" -ForegroundColor Yellow
    Write-Host "  Ver logs:    docker compose logs -f web" -ForegroundColor Gray
    Write-Host "  Parar:       docker compose down" -ForegroundColor Gray
    Write-Host "  Reiniciar:   docker compose restart web" -ForegroundColor Gray
    Write-Host "  Rebuild:     docker compose build --no-cache && docker compose up -d" -ForegroundColor Gray
} else {
    Write-Host "Próximos pasos:" -ForegroundColor Yellow
    Write-Host "  1. Edita .env con tus configuraciones reales" -ForegroundColor White
    Write-Host "  2. (Opcional) Inicia smtp4dev para emails de prueba:" -ForegroundColor White
    Write-Host "     .\entrenamiento\smtp4dev\Rnwood.Smtp4dev.Desktop.exe" -ForegroundColor Gray
    Write-Host "  3. (Opcional) Inicia Ollama si no está corriendo:" -ForegroundColor White
    Write-Host "     ollama serve" -ForegroundColor Gray
    Write-Host "  4. Inicia el servidor:" -ForegroundColor White
    Write-Host "     .\start_chatbot.bat" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Luego abre: http://127.0.0.1:8000/chat/" -ForegroundColor Cyan
    Write-Host "  Admin: http://127.0.0.1:8000/admin/" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "Documentación completa en README.md" -ForegroundColor Yellow