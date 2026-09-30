# Dockerización - Chatbot DianSistemas

Guía completa para desplegar el chatbot usando Docker y Docker Compose.

---

## Arquitectura de contenedores

```
┌─────────────────────────────────────────────────────────────┐
│                        docker-compose.yml                     │
├─────────────┬─────────────┬──────────────┬──────────────────┤
│   setup     │    web      │   ollama     │   ollama-init    │
│ (bootstrap) │  (Django)   │  (LLM server)│  (pull llama3.2) │
├─────────────┼─────────────┼──────────────┼──────────────────┤
│ - migrate   │  gunicorn   │  REST API    │  pull llama3.2   │
│ - load data │  2 workers  │  healthcheck │  (una sola vez)  │
│ - train NLP │  4 threads  │  GPU opcional│                  │
│ - gen models│  timeout 300│              │                  │
└─────────────┴─────────────┴──────────────┴──────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌─────────┐
│app_data │ │spacy_mdl│  (volúmenes persistentes)
│SQLite   │ │ model   │
└─────────┘ └─────────┘
```

---

## Inicio rápido

```bash
# 1. Clonar y entrar
git clone https://github.com/josecursoprogramacion-coder/Chatbot.git
cd Chatbot

# 2. Configurar entorno
cp .env.example .env
# Edita .env con tus valores

# 3. Levantar todo (build + setup + web + ollama)
docker compose up -d

# 4. Ver logs del setup (bootstrap)
docker compose logs -f setup

# 5. Una vez setup termine (Exit 0):
# http://localhost:8000/chat/
# http://localhost:8000/admin/
```

---

## Servicios en docker-compose.yml

### `setup` (One-shot bootstrap)
- **Entrypoint**: `./setup.sh`
- **Ejecuta**: migraciones → carga datos → genera NLP → entrena spaCy → genera modelfiles → crea modelos Ollama
- **Idempotente**: usa markers `/data/.data_loaded` y modelo existente
- **Depende de**: `ollama` (healthy), `ollama-init` (completed), `db` (healthy)

### `web` (Aplicación Django)
- **Comando**: `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --worker-class gthread --workers 2 --threads 4 --timeout 300`
- **Puerto**: `8000:8000`
- **Dependencia**: `setup` completado exitosamente
- **Variables**: `RUN_COLLECTSTATIC=1`

### `ollama` (Servidor LLM)
- **Imagen**: `ollama/ollama:latest`
- **Volumen**: `ollama_data:/root/.ollama`
- **Healthcheck**: `ollama list` cada 10s
- **GPU opcional**: descomentar sección `deploy` en compose

### `ollama-init` (Inicialización)
- **Ejecuta**: `ollama pull llama3.2` una sola vez
- **Depende de**: `ollama` healthy

### `db` (MySQL opcional - profile)
- **Imagen**: `mysql:8.4`
- **Activa con**: `docker compose --profile mysql up -d`
- **Variables**: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_ROOT_PASSWORD`

---

## Variables de entorno para Docker

El archivo `.env` se pasa a **todos** los contenedores:

```bash
# .env
# Django
SECRET_KEY=tu-clave-secreta
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,tudominio.com

# Ollama (usa nombre del servicio en Docker)
OLLAMA_HOST=http://ollama:11434

# Base de datos SQLite (default)
SQLITE_PATH=/data/db.sqlite3

# MySQL (solo con --profile mysql)
DB_NAME=chatbot
DB_USER=chatbot
DB_PASSWORD=tu_password_seguro
DB_ROOT_PASSWORD=root_password_seguro

# Email
EMAIL_HOST=smtp.tu_proveedor.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_email
EMAIL_HOST_PASSWORD=tu_password
RESUMEN_EMAIL_DESTINATARIOS=admin@diansistemas.com

# Dominios permitidos (para iframe)
DOMINIOS_PERMITIDOS=https://tudominio.com, http://localhost:8000
```

---

## Volúmenes persistentes

| Volumen | Montaje | Contenido |
|---------|---------|-----------|
| `app_data` | `/data` | SQLite (`db.sqlite3`), marker `.data_loaded` |
| `spacy_model` | `/app/entrenamiento/spacy/modelo` | Modelo spaCy entrenado |
| `ollama_data` | `/root/.ollama` | Modelos Ollama descargados |
| `mysql_data` | `/var/lib/mysql` | Datos MySQL (profile mysql) |

---

## Comandos útiles

### Gestión básica

```bash
# Ver estado
docker compose ps

# Logs en tiempo real (web)
docker compose logs -f web

# Logs del setup (bootstrap)
docker compose logs -f setup

# Logs de Ollama
docker compose logs -f ollama

# Parar todo
docker compose down

# Parar y borrar volúmenes (¡CUIDADO: borra datos!)
docker compose down -v
```

### Reinicio y rebuild

```bash
# Reiniciar solo la web
docker compose restart web

# Rebuild completo (cambio en Dockerfile, requirements.txt)
docker compose build --no-cache && docker compose up -d

# Rebuild solo setup
docker compose build setup && docker compose up -d setup
```

### Forzar re-ejecución del setup

```bash
# Forzar re-carga de datos iniciales
docker compose run --rm -e FORCE_RELOAD=1 setup

# Forzar re-entrenamiento spaCy
docker compose run --rm -e FORCE_TRAIN=1 setup

# Ambos a la vez
docker compose run --rm -e FORCE_RELOAD=1 -e FORCE_TRAIN=1 setup
```

### Entrar a contenedores

```bash
# Shell en web
docker compose exec web bash

# Shell en ollama
docker compose exec ollama bash

# Python manage.py dentro del contenedor
docker compose exec web python manage.py shell
```

### Usar MySQL en lugar de SQLite

```bash
# Requiere variables en .env: DB_NAME, DB_USER, DB_PASSWORD, DB_ROOT_PASSWORD
docker compose --profile mysql up -d
```

---

## Flujo de primer arranque (detalle)

```
1. docker compose up -d
   │
   ├─► ollama (inicia) ──► healthcheck OK
   │
   ├─► ollama-init ──► pull llama3.2 ──► Exit 0
   │
   ├─► setup (espera ollama healthy + ollama-init done)
   │    │
   │    ├─► python manage.py migrate
   │    ├─► python manage.py cargar_datos_iniciales
   │    ├─► python manage.py generar_nlp
   │    ├─► python -m spacy train ... (5-15 min)
   │    ├─► python manage.py generar_modelfiles
   │    ├─► python manage.py generar_modelfiles --crear
   │    └─► Exit 0
   │
   └─► web (espera setup Exit 0)
        └─► gunicorn en puerto 8000
```

**Tiempo estimado primer arranque**: 5-15 minutos (entrenamiento spaCy).

---

## Monitoreo y logs

### Verificar estado

```bash
# Estado de servicios
docker compose ps

# Ver salud de ollama
docker compose exec ollama ollama list

# Ver modelos disponibles
docker compose exec ollama ollama list | grep chatbot
```

### Logs importantes

```bash
# Ver qué hizo el setup
docker compose logs setup

# Ver errores de la web
docker compose logs web | grep -i error

# Ver consultas a Ollama
docker compose logs ollama | grep -i "POST /api/chat"
```

---

## Solución de problemas

| Problema | Diagnóstico | Solución |
|----------|-------------|----------|
| Setup nunca termina | `docker compose logs setup` | Revisa errores de migración/NLP |
| Setup falla (Exit 1) | `docker compose logs setup` | Fix error → `docker compose restart setup` |
| Web no inicia | `docker compose logs web` | Verifica que setup terminó Exit 0 |
| Ollama unhealthy | `docker compose logs ollama` | `docker compose restart ollama` |
| Puerto 8000 ocupado | `docker compose ps` | Cambia puerto en compose: `"8080:8000"` |
| Modelo spaCy no carga | `docker compose logs web` | Verifica `SPACY_MODEL_PATH` en `.env` |
| Sin modelos chatbot | `docker compose logs setup` | `docker compose run --rm -e FORCE_TRAIN=1 setup` |

### Ver logs de un servicio específico

```bash
# Últimas 100 líneas
docker compose logs --tail=100 web

# Seguir logs
docker compose logs -f web

# Con timestamps
docker compose logs -t web
```

---

## Producción - Consideraciones adicionales

### Seguridad

```yaml
# docker-compose.prod.yml (overlay)
services:
  web:
    environment:
      DEBUG: "False"
      SECURE_SSL_REDIRECT: "True"
      SESSION_COOKIE_SECURE: "True"
      CSRF_COOKIE_SECURE: "True"
    # Usar secrets de Docker Swarm/K8s para SECRET_KEY
```

### Reverse Proxy (Nginx/Traefik)

```nginx
# Nginx config
server {
    listen 80;
    server_name tudominio.com;
    
    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support si usas channels
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts para LLM
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

### Backup automático

```bash
# Backup SQLite
docker compose exec web cp /data/db.sqlite3 /data/db.sqlite3.backup.$(date +%F)

# O script cron en host:
# 0 2 * * * docker compose exec -T web cp /data/db.sqlite3 /data/backups/db_$(date +\%F).sqlite3
```

### Recursos recomendados

| Componente | CPU | RAM |
|------------|-----|-----|
| web (gunicorn 2w/4t) | 2 vCPU | 2 GB |
| ollama (llama3.2) | 2 vCPU | 4-8 GB |
| setup (entrenamiento) | 2 vCPU | 4 GB |

> **GPU para Ollama**: Descomenta sección `deploy` en `docker-compose.yml` y usa `nvidia/cuda` base image.

---

## Referencias

- 📖 [Instrucciones instalación](../instrucciones_instalacion.md)
- 🧠 [Configuración entrenamiento](configuracion_entrenamiento.md)
- 📋 [README principal](../README.md)
- 🐳 [Docker Compose reference](https://docs.docker.com/compose/)
- 🤖 [Ollama docs](https://github.com/ollama/ollama)