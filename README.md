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
- **Entrenamiento NLP mejorado** — Reentrenado con casos "instalar/error", "contactar_humano", "confirmacion" para corregir clasificación
- **Fallback LLM robusto** — Cadena de intentos: dominio específico → genérico → "otro" → llama3.2 (evita 404)
- **Bug fixes** — Arreglado "list index out of range" en `generar_pares_desde_conversacion`

## Funciones no implementadas

- **Docker** — Dockerizar el proyecto
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

## Tech Stack

- **Backend:** Python, Django
- **Database:** SQLite (producción: PostgreSQL recomendado)
- **Frontend:** Bootstrap 5, JavaScript vanilla (ES6)
- **NLP:** spaCy (textcat + tok2vec, vectors `es_core_news_lg`)
- **LLM:** Ollama, Llama 3.2 (modelos por intención: `chatbot-compra`, `chatbot-consulta`, `chatbot-otro`)
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