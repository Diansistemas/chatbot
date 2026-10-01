# Chatbot

Chatbot con IA para uso comercial de Dian Sistemas

## Funciones implementadas

- **Estructura básica** — Estructura básica de la aplicación
- **Generación de NLP** — Generación de los modelos NLP a través de `manage.py`
- **Generación de LLMs** — Generación de los modelos LLM a través de `manage.py`
- **Almacenaje de datos básicos** — Creación de las entradas en la base de datos a través de `manage.py`
- **Chatbot** — Un chatbot funcional que ajusta el modelo usado dependiendo de la intención del usuario
- **Cierre de conversación** — Cierre manual y automático por inactividad (5 min, aviso a los 4 min)
- **Notificaciones automáticas** — Envío de resumen por correo al cerrar conversaciones de compra
- **Timer de inactividad frontend** — `static/js/inactividad.js`: reinicio en actividad, aviso a 4 min, cierre a 5 min, sincronizado con backend (410 Gone)
- **Checklist en email** — El cuerpo del correo empieza con ✅ datos completos / ❌ faltan datos / ⏳ sin pedido
- **Acceso directo al chat** — Permite abrir `/chat/` en navegador sin Referer (CSP `frame-ancestors` protege iframes)
- **Entrenamiento NLP (ronda 9)** — 597 ejemplos en `nlp.csv`; macro F1 0,782 / micro 0,852 (informes en `pruebas/informes/`)
- **Fallback LLM robusto** — Cadena de intentos: dominio específico → genérico → "otro" → llama3.2 (evita 404)
- **Bug fixes** — Arreglado "list index out of range" en `generar_pares_desde_conversacion`; tests remotos arreglados (creación de `Servicio` y aislamiento de `SPACY_DIR`)
- **Dockerización asistida** — `docker_setup.sh` (7 pasos) con `configurar_entorno.py`, un asistente que va pidiendo los datos (puerto, hosts, widget, email, modelo...) y escribe el `.env`
- **Suite de tests organizada** — Tests repartidos por funcionalidad en `pruebas/` (aplicacion, funcional, evaluacion, informes); 112 tests en verde

## Funciones no implementadas

- **Servidor** — Hosteo del widget en un servidor
- **Logger** — Mantener un log del funcionamiento de la aplicación

## Flujo de notificaciones

1. Se cierra una conversación (botón, bot, o inactividad 5 min)
2. Signal `post_save` en `Conversacion.estado="cerrada"`
3. `clasificar_conversacion()` → **modelo spaCy** (analiza solo mensajes del cliente)
4. Si **compra/confirmacion**: `crear_resumen()` → `enviar_resumen()` → email a admins
5. Si **no compra**: no hace nada
6. Guardas: anti-duplicado (`resumenes.exists()`), solo en transición `estado`, `try/except` (SMTP caído no rompe cierre)

## Estructura del proyecto

Este proyecto es una aplicación web de Django con la siguiente estructura:

- **Core** — Funcionalidad en torno al chatbot
    - **Mixins** — Ajustes de permiso web (`DominioPermitidoMixin`)
    - **Acceso** — Acceso a modelos (spaCy, Ollama, resúmenes)
    - **Views** — `ChatWidgetView` (GET/POST AJAX, cierre, inactividad)
    - **Static/JS** — `ajax_chat.js`, `inactividad.js`
- **Entrenamiento** — App centrada en el entrenamiento de los modelos
    - **Datos** — CSV con datos iniciales (`nlp.csv`, `intenciones.csv`, `etiquetas.csv`, `servicios.csv`, `llm.csv`)
    - **LLMs** — Modelfiles para Ollama (por intención y dominio)
    - **SpaCy** — Modelos NLP (`modelo/`, `modelo_anterior/`, `config.cfg`, `train/dev.spacy`)
    - **Management/Commands** — `cargar_nlp`, `generar_nlp`, `cargar_llm`, `cargar_servicios`, `cargar_intenciones`, `cargar_etiquetas`, `cargar_datos_iniciales`
- **Chat** — Gestión de chats (`Conversacion`, `Mensaje`, `Pedido`, `Servicio`)
- **Notificaciones** — Resúmenes y envío de correos (`Resumen`, `clasificar_conversacion`, `crear_resumen`, `enviar_resumen`, `signals.py`)
- **Docs** — Documentación adicional
- **Pruebas** (`pruebas/`) — Tests y evaluación organizados por funcionalidad
    - **aplicacion** — Suite Django: `tests.py`, `test_views.py`, `test_comprehensive.py`, `test_flujo.py` (23 tests de funcionamiento)
    - **funcional** — Tests standalone HTTP + NLP + LLM + cierre/email (`test_funcional.py`, `test_suite.py`)
    - **evaluacion** — Scripts de métricas: matrices de confusión, evaluación LLM, historial de rondas
    - **informes** — Informes de resultados de las rondas de entrenamiento
    - **ejecutar_tests.ps1** — Runner de la suite
- **Raíz** — Despliegue y configuración: `docker_setup.sh`, `configurar_entorno.py`, `install.sh`, `install.ps1`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `.gitattributes` (fuerza LF en `.sh`/Dockerfile/compose)

## Tech Stack

- **Backend:** Python, Django, gunicorn (Docker: gthread, 2 workers × 4 threads, timeout 300s)
- **Database:** SQLite (en Docker: volumen `/data/db.sqlite3`; producción: PostgreSQL recomendado)
- **Frontend:** Bootstrap 5, JavaScript vanilla (ES6)
- **NLP:** spaCy (textcat + tok2vec, vectors `es_core_news_lg`)
- **LLM:** Ollama, Llama 3.2 (modelos por intención: `chatbot-compra`, `chatbot-consulta`, `chatbot-otro`)
- **Docker:** Docker Compose (servicios `setup`, `web`, `ollama`, `ollama-init`, `db` opcional)
- **Email testing:** smtp4dev (SMTP 25, web UI puerto dinámico)

## Comandos útiles

```bash
# Cargar y generar datos NLP
python manage.py cargar_nlp --limpiar
python manage.py generar_nlp

# Entrenar modelo spaCy (usa config.cfg, train/dev.spacy)
python -m spacy train entrenamiento/spacy/config.cfg \
  --paths.train entrenamiento/spacy/train.spacy \
  --paths.dev entrenamiento/spacy/dev.spacy \
  --output entrenamiento/spacy/modelo

# Cargar LLMs en Ollama
python manage.py cargar_llm

# Servidor de desarrollo
python manage.py runserver 127.0.0.1:8000

# Tests (112)
python manage.py test
```

## SMTP local (smtp4dev)

```bash
# Ejecutar (puerto web cambia cada arranque)
.\entrenamiento\smtp4dev\Rnwood.Smtp4dev.Desktop.exe

# Ver correos en http://127.0.0.1:<puerto_web>
# SMTP en 127.0.0.1:25 (sin TLS)
# Config .env: EMAIL_HOST=127.0.0.1, EMAIL_PORT=25, EMAIL_USE_TLS=False
# RESUMEN_EMAIL_DESTINATARIOS=admin@diansistemas.com
```

## Tests

Suite de **112 tests** organizada por carpetas en `pruebas/`:

| Carpeta | Contenido |
|---------|-----------|
| `pruebas/aplicacion/` | Suite Django (`manage.py test`): `tests.py`, `test_views.py`, `test_comprehensive.py`, `test_flujo.py` |
| `pruebas/funcional/` | Tests standalone HTTP + NLP + LLM + cierre/email (requieren Ollama; `test_suite.py` necesita smtp4dev) |
| `pruebas/evaluacion/` | Scripts de métricas: matrices de confusión, evaluación NLP/LLM, historial de rondas |
| `pruebas/informes/` | Informes de resultados de las rondas de entrenamiento |

```powershell
# Todo (suite Django + funcional)
.\pruebas\ejecutar_tests.ps1

# Por partes
.\pruebas\ejecutar_tests.ps1 -SoloUnit    # solo la suite Django
.\pruebas\ejecutar_tests.ps1 -SoloFunc    # solo el funcional (necesita Ollama)

# O directamente
python manage.py test                     # 112 tests
```

## Instalación con Docker (Recomendado para producción)

El proyecto incluye `Dockerfile` y `docker-compose.yml` listos para usar. El contenedor `setup` ejecuta automáticamente migraciones, carga de datos, entrenamiento spaCy y creación de modelos Ollama al primer inicio.

### Instalación rápida con Docker

```bash
# 1. Clonar repositorio
git clone https://github.com/josecursoprogramacion-coder/Chatbot.git
cd Chatbot

# 2. Dockerizar: el asistente va pidiendo la configuración y escribe el .env
./docker_setup.sh                # Linux; en Windows: Git Bash

# 3. Verificar logs del setup (migraciones, datos, entrenamiento spaCy, modelos Ollama)
docker compose logs -f setup

# Una vez setup termine (Exit 0), la web estará disponible en el puerto
# configurado (8000 por defecto):
# http://localhost:<WEB_PORT>/chat/
# http://localhost:<WEB_PORT>/admin/
```

`docker_setup.sh` ejecuta 7 pasos:

1. **Configuración** — lanza el asistente `configurar_entorno.py` (si falta `.env`)
2. **Build** de la imagen `chatbot-app`
3. Arranque de **Ollama**
4. **Descarga del modelo** de Ollama (`llama3.2` por defecto)
5. **Bootstrap** (`setup.sh`): migraciones → carga de datos → entrenamiento spaCy → modelfiles
6. Servicio **web** (gunicorn)
7. **Verificación** (`docker compose ps`) y resumen con la URL final (puerto elegido)

Opciones: `--config` (reconfigurar el `.env` aunque ya exista), `--sin-config` (no lanzar el asistente).

### Asistente de configuración (`configurar_entorno.py`)

En lugar de editar `.env` a mano, el proyecto incluye un asistente interactivo que va pidiendo los datos y escribe el `.env` por ti (la plantilla comentada está en `.env.example`). Lo lanzan `docker_setup.sh`, `install.sh` e `install.ps1`, o directamente:

```bash
python configurar_entorno.py                 # interactivo (conserva lo que ya haya)
python configurar_entorno.py --fuerza        # reconfigurar aunque exista el .env
python configurar_entorno.py --defaults      # sin preguntar: valores por defecto
python configurar_entorno.py --salida X.env  # escribir otro fichero en vez de .env
```

Bloques de preguntas:

1. Servidor web (puerto)
2. Seguridad de Django (`SECRET_KEY`, `DEBUG`)
3. Hosts y orígenes (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`)
4. Widget embebido (`DOMINIOS_PERMITIDOS`)
5. Ollama (modelo para los resúmenes)
6. Email de resúmenes (SMTP real o consola)
7. Modelo spaCy (ruta a un modelo ya entrenado, o reentrenar en el primer arranque)

Para instalar **sin Docker** (venv, dependencias, datos y modelos), usar `./install.sh` (Linux/macOS) o `.\install.ps1` (Windows); ambos lanzan el mismo asistente.

> **Estado:** scripts verificados (sintaxis bash, YAML, asistente probado en sus 4 modos, suite 112/112). Falta la primera ejecución real con Docker instalado en el equipo de desarrollo.

### Servicios incluidos en docker-compose.yml

| Servicio | Descripción |
|----------|-------------|
| `setup` | Bootstrap: migraciones → carga datos → entrenamiento spaCy → modelos Ollama |
| `web` | Aplicación Django (gunicorn, 2 workers, 4 threads, timeout 300s; puerto `WEB_PORT`, 8000 por defecto) |
| `ollama` | Servidor Ollama para LLMs (con healthcheck) |
| `ollama-init` | Descarga inicial de `llama3.2` |
| `db` (profile: mysql) | MySQL 8.4 opcional (usa `--profile mysql`) |

### Comandos Docker útiles

```bash
# Ver logs en tiempo real
docker compose logs -f web

# Ver logs del setup (bootstrap)
docker compose logs -f setup

# Parar servicios
docker compose down

# Reiniciar solo la web
docker compose restart web

# Rebuild completo (cambio en requirements.txt, Dockerfile, etc.)
docker compose build --no-cache && docker compose up -d

# Re-dockerizar desde cero reconfigurando el .env con el asistente
./docker_setup.sh --config

# Ver estado de contenedores
docker compose ps

# Entrar al contenedor web
docker compose exec web bash

# Ver logs de Ollama
docker compose logs -f ollama

# Usar MySQL en lugar de SQLite (requiere variables en .env)
docker compose --profile mysql up -d
```

### Variables de entorno para Docker

El archivo `.env` (escrito por el asistente; plantilla comentada en `.env.example`) se pasa a todos los contenedores con `env_file` y también lo lee `config/settings.py`. Variables principales:

```bash
# --- Django ---
SECRET_KEY=...                        # la genera el asistente (no se muestra)
DEBUG=True                            # solo "True" activa el debug
ALLOWED_HOSTS=localhost,127.0.0.1     # sin esquema, separados por coma
CSRF_TRUSTED_ORIGINS=http://localhost:8000

# --- Widget ---
DOMINIOS_PERMITIDOS=http://localhost:8000   # esquema obligatorio (si no: 403)

# --- Servidor y Docker ---
WEB_PORT=8000                         # puerto publicado por docker-compose
SPACY_MODEL_HOST_PATH=                # ruta a un modelo ya entrenado en el host
                                      # (vacío = entrenar en el volumen spacy_model)
FORCE_TRAIN=0                         # 1 = reentrenar el NLP en el primer arranque

# --- Ollama ---
OLLAMA_HOST=http://localhost:11434    # compose lo sustituye por http://ollama:11434
OLLAMA_MODEL_RESUMEN=llama3.2         # modelo de resúmenes (bajado por ollama-init)

# --- Email de resúmenes ---
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend  # o smtp.EmailBackend
EMAIL_HOST=localhost
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=False
RESUMEN_EMAIL_DESTINATARIOS=

# Interno de compose (fijo en docker-compose.yml, no va en .env):
SQLITE_PATH=/data/db.sqlite3          # SQLite en volumen persistente

# Para MySQL (profile mysql):
DB_NAME=chatbot
DB_USER=chatbot
DB_PASSWORD=secreto
DB_ROOT_PASSWORD=rootsecreto
```

### Volúmenes persistentes

| Volumen | Contenido |
|---------|-----------|
| `app_data` | SQLite (`/data/db.sqlite3`) + marker `.data_loaded` |
| `spacy_model` | Modelo spaCy entrenado (`/app/entrenamiento/spacy/modelo`) |
| `ollama_data` | Modelos Ollama descargados (`/root/.ollama`) |
| `mysql_data` | Datos MySQL (solo con `--profile mysql`) |

### Forzar re-entrenamiento o recarga de datos

```bash
# Forzar re-importación de datos iniciales
docker compose run --rm -e FORCE_RELOAD=1 setup

# Forzar re-entrenamiento spaCy
docker compose run --rm -e FORCE_TRAIN=1 setup

# Ambos a la vez
docker compose run --rm -e FORCE_RELOAD=1 -e FORCE_TRAIN=1 setup
```

---

## Checklist producción (seguridad)

Antes de desplegar a producción, revisar:

- [ ] `DEBUG = False`
- [ ] `SECRET_KEY` rotada y fuera de `.env` (gestor de secretos)
- [ ] `ALLOWED_HOSTS = ['diansitemas.com', 'www.diansitemas.com']`
- [ ] Cookies seguras: `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `CSRF_COOKIE_HTTPONLY = True`
- [ ] HSTS: `SECURE_HSTS_SECONDS = 31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`, `SECURE_HSTS_PRELOAD = True`
- [ ] PostgreSQL en lugar de SQLite
- [ ] SMTP autenticado + TLS (`EMAIL_USE_TLS = True`)
- [ ] Rate limiting en `/chat/`
- [ ] Backups automatizados BD + test restore mensual
- [ ] Monitoring (Sentry, Prometheus/Grafana)

## Créditos

- Victor Herrero
- Adrian Salas
- José Alonso