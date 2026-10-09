# Plan de ejecución paso a paso — real + simulado

> **Fecha**: 8-9 de octubre de 2026 (creado8/oct — actualizado9/oct tras el reinicio)
> **Objetivo**: chatbot Django (NLP spaCy + LLM Ollama) embebido en WordPress de
> `metododian.com`, con hosting definitivo en Raiola Networks.
> **Leyenda**: ✅ HECHO · ⏸️ BLOQUEADO (pasos **SIMULADOS** abajo, listos para
> ejecutar en cuanto se desbloqueie) · ❌ PENDIENTE DE ACCIÓN DEL USUARIO.

Documentación complementaria (ya en el repo):

- `docs/despliegue_wordpress.md` — guía del despliegue (túnel + fix CSRF + E2E).
- `docs/log_sesion_2026-10.md` — log cronológico de las sesiones 6-7/oct.
- Este documento — **estado global + pasos simulados** de todo lo pendiente.

---

## 0. Estado global (8/oct/2026)

| # | Elemento | Estado |
|---|---|---|
| 1 | Código en GitHub `Diansistemas/chatbot` (`ramapruebas` = `93d53b6`) | ✅ |
| 2 | Tests: **113 suite + 34 funcionales** (0 fallos) | ✅ |
| 3 | Widget E2E en local + túnel (Referer/Origin/CSP, token persistente) | ✅ |
| 4 | Fix CSRF para iframes (`csrf_exempt` + check `Origin`) | ✅ |
| 5 | Django + Ollama + túnel | ✅ **Restaurado 9/oct** (4ª restauración: huérfano 3900 eliminado, PID 20772, E2E 4/4) |
| 6 | Página WP `metododian.com/index.php/prueba-chatbot/` | ⏸️ Snippet **ROTO** (URL vieja) → **Bloque B** |
| 7 | *Setup Python App* en cPanel `ha1011` | ❌ No activado (4 jornadas: 6, 7×3, 8 oct) → **Bloque C** |
| 8 | Hosting definitivo | ⏸️ Sin decidir (3 vías) → **Bloque C/D/E** |
| 9 | Docker end-to-end | ⏸️ Docker no instalado → **Bloque F** |
| 10 | Página de prueba WP: dejar o borrar | ⏸️ Decisión del usuario → **Bloque G** |

**URL del túnel**: `https://clocks-gather-jenny-governing.trycloudflare.com`
(9/oct — la anterior murió con el reinicio). ⚠️ *Cambia en cada reinicio:
actualizar aquí, en el Apéndice A, en `.env` (3 líneas) y en el snippet de WP
(**Bloque B**).*

---

# BLOQUE A — ✅ HECHO (referencia rápida)

1. Diagnóstico del cPanel Raiola (3 vías, sin Python; disco 93 %).
2. Túnel Cloudflare + `.env` (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DOMINIOS_PERMITIDOS`).
3. Snippet `loader.js` multi-origen (origen deducido de `document.currentScript.src`).
4. Bug CSRF en iframes de terceros → `csrf_exempt` + red de seguridad `_origen_permitido()`.
5. E2E: conversación NLP → LLM → respuesta; token persistente `?conversacion=`; hostil → 403.
6. Integración de commits remotos + revalidación total (113 + 34).
7. Documentación: guía, logs, mensajes para Raiola (Apéndice C de `despliegue_wordpress.md`).

---

# BLOQUE B — ⏸️ PASO 5 SIMULADO: actualizar el snippet en WordPress

**Bloqueado por**: sesión de WordPress caducada (hace falta login).
**Cuando se desbloqueie, ejecutar exactamente estos pasos:**

1. **Acceder**: `https://metododian.com/wp-admin` → usuario y contraseña → *Acceder*.
2. **Abrir la página**: menú lateral **Páginas** → **Prueba ChatBot** → **Editar**
   (si no aparece en la lista: buscarla con el filtro, o ir a
   `https://metododian.com/wp-admin/edit.php?post_type=page`).
3. **Localizar el bloque** «HTML personalizado» que contiene:
   ```html
   <script src="https://coalition-taxes-sellers-change.trycloudflare.com/static/js/loader.js"></script>
   ```
   > ⚠️ Si la página sigue con `favorites-window-parts-allied…` (lo más probable),
   > reemplazar esa URL por la **actual** del túnel (Apéndice A — cómo obtenerla).
4. **Guardar**: botón **Actualizar** (arriba a la derecha).
5. **Caché**: si al recargar no cambia → **LiteSpeed Cache → Purge All (Borrar todo)**.
6. **Verificación** (checklist):
   - [ ] Abrir `https://metododian.com/index.php/prueba-chatbot/` en incógnito.
   - [ ] Aparece el **botón azul** del chat abajo a la derecha.
   - [ ] Enviar un mensaje → respuesta del chatbot (NLP + LLM).
   - [ ] **Recargar** la página → el iframe conserva la conversación (token en `?conversacion=`).
   - [ ] En DevTools → Network: el `POST /chat/` responde **200** (no 403).
   - [ ] (Opcional) `<meta>`/CSP: `frame-ancestors` incluye `https://metododian.com`.
7. **Documentar** en `docs/log_sesion_*.md` + commit/push (con aprobación).

---

# BLOQUE C — ⏸️ TRACK A SIMULADO: Raiola — activar Python en el hosting

**Bloqueado por**: el usuario aún no ha contactado con Raiola (4 días sin cambios).
**Cuando se desbloqueie, ejecutar estos pasos:**

### C.1 — Contactar (elige vía)

- **Teléfono**: **982 77 60 81** (24/7) · **Chat** en `raiolanetworks.com` ·
  **Área de clientes**: `raiolanetworks.com/clientes` · ticket desde cPanel.

**Mensaje listo para copiar/pegar o leer por teléfono:**

```
Asunto: ¿Setup Python App en mi plan actual? - cuenta diansis1 (ha1011)

Hola,

Soy cliente de alojamiento con cPanel y necesito desplegar una aplicación
Django en un subdominio de metododian.com. Mi panel no muestra la
herramienta "Setup Python App".

Datos de la cuenta:
  - Usuario de cPanel: diansis1
  - Servidor: ha1011.raiolanetworks.es (panel jupiter, cPanel 136.0.45)
  - Home: /home/diansis1

Comprobaciones realizadas (8 de octubre):
  - Sección "Software": solo PHP/Perl, Installatron, LiteSpeed Cache, X-Ray.
  - Búsqueda global del panel: 0 resultados para "Python".
  - Acceso directo /frontend/jupiter/software/pythonApp/index.html: error 404.
  - En vuestro centro de ayuda tenéis la guía "Despliegue de una aplicación
    Python en un hosting con cPanel", por eso pregunto.

Necesito Python 3.12 o superior (Django 6.1 lo exige) y HTTPS en un
subdominio. Preguntas:
  1. ¿Es posible habilitar "Setup Python App" en mi plan actual?
  2. Si no, ¿qué producto necesito (Hosting Python)? ¿Hay cambio de plan?
  3. Tengo SSH/Terminal, por si sirve para instalar venv + pip.

Muchas gracias.
```

### C.2 — ESCENARIO A1 (respuesta favorable): habilitan *Setup Python App*

1. Confirmar en cPanel: sección **Software → Setup Python App** visible.
2. **Liberar disco** (la cuenta está al 93 %; hacen falta ~2 GB):
   - Eliminar backups antiguos/correo innecesario; revisar `/home/diansis1`.
   - Presupuesto: venv ~1 GB + modelo spaCy ~630 MB + código ~x MB.
3. **Subdominio**: cPanel → **Dominios** → añadir `chat.metododian.com`
   (document root vacío/por defecto).
4. **Crear la aplicación**: *Setup Python App → Create Application*:
   - Application root: `/home/diansis1/chatbot` · dominio: `chat.metododian.com`
   - Python **3.12+** (ver disponibles; la guía de Raiola indica hasta 3.13)
   - WSGI: archivo generado por el panel (apuntando a `config.wsgi`)
5. **Subir el código** (por SSH — más fiable que el File Manager para ~630 MB):
   ```bash
   ssh diansis1@ha1011.raiolanetworks.es
   cd /home/diansis1
   git clone https://github.com/Diansistemas/chatbot.git chatbot   # rama ramapruebas
   # ... o subir tarball: tar.gz del repo + modelo entrenamiento/spacy/modelo/
   ```
6. **Dependencias**: en el venv de la aplicación:
   ```bash
   pip install -r requirements.txt
   ```
   (si no existe `requirements.txt`: generarlo con `pip freeze > requirements.txt` en local).
7. **`.env` de producción** (crear en `/home/diansis1/chatbot/.env`):
   ```ini
   DEBUG = False
   SECRET_KEY = <clave-nueva-aleatoria>
   ALLOWED_HOSTS = chat.metododian.com
   CSRF_TRUSTED_ORIGINS = https://chat.metododian.com
   DOMINIOS_PERMITIDOS = https://metododian.com
   OLLAMA_HOST = <ver paso 9>
   EMAIL_BACKEND = django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST = <SMTP real>          # el actual es 127.0.0.1:25 (no válido en prod)
   RESUMEN_EMAIL_DESTINATARIOS = admin@diansistemas.com
   ```
8. **Migraciones y estáticos** (SSH, dentro del entorno):
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```
   - ⚠️ Con `DEBUG=False` Django **no sirve `/static/`** → verificar quién lo sirve:
     si el panel hace alias al static root, bien; si no, instalar **WhiteNoise**
     (añadir a `MIDDLEWARE` + `STORAGES`) o configurar alias en el vhost.
     Prueba: `curl -I https://chat.metododian.com/static/js/loader.js` → debe ser **200**.
9. **Ollama en producción**: **no corre en hosting compartido**. Opciones:
   - a) Servidor/VPN del cliente con Ollama + `OLLAMA_HOST=<ip-o-tunel>` (requiere
     que la PC quede encendida — igual que el túnel actual), o
   - b) Instancia Ollama externa (VPS del propio Raiola, u otra), o
   - c) API de terceros (cambiar el cliente Ollama por HTTP a otro proveedor).
   Definir esta ANTES de dar por bueno el despliegue: sin Ollama el chat no responde.
10. **SSL**: cPanel → *SSL/TLS* → Let's Encrypt/AutoSSL para `chat.metododian.com`.
11. **Probar**: `https://chat.metododian.com/health` → 200; `/chat/` → 200.
12. **Actualizar el snippet en WP** con `https://chat.metododian.com/static/js/loader.js`
    (pasos del **Bloque B**).
13. **E2E completo** (Bloque B.6) + pruebas de seguridad (Referer hostil → 403).
14. **Commit/log** del despliegue definitivo (con aprobación).

### C.3 — ESCENARIO A2 (respuesta negativa): contratar *Hosting Python*

> Página: `raiolanetworks.com/hosting-python` — **desde 27,20 €/mes** (sin IVA):
> "Para crecer" 50 GB / 2 GB RAM / 150 % CPU · "Para correr" 64,90 € ·
> "Para almacenar" 76,00 €. SSH + PIP + Git, Python hasta 3.13, migración gratis.

1. Decisión del usuario (coste/plan) — **requiere aprobación explícita**.
2. Contratar desde el área de clientes (dominio nuevo o subdominio del actual).
3. Pedir la **migración gratis** si aplica (incluye hasta 10 apps).
4. A partir de ahí: mismos pasos **C.2 (3-14)** en el nuevo plan.
5. El WordPress **se queda** donde está; `chat.metododian.com` apunta al nuevo hosting
   (A-record o nameserver según indique Raiola).

### C.4 — ESCENARIO A3 (alternativa): VPS + Docker

1. Decisión del usuario (desde 9,95 €/mes VPS · 49,95 € administrado) — **aprobación explícita**.
2. Contratar VPS (Raiola, centro de datos Madrid).
3. Seguir **Bloque F** (Docker) dentro del VPS.

---

# BLOQUE D — ⏸️ SIMULADO: restauración tras cada reinicio del entorno

**Bloqueado por**: nada — ejecutar cuando los shells de fondo desaparezcan
(el patrón se repite: Django y cloudflared mueren con cada reinicio del entorno).

**Protocolo exacto (4 pasos):**

1. **Túnel** (URL nueva):
   ```powershell
   & "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000 > C:\Users\CEFYE\chat\cf_tunel.log 2>&1
   # esperar ~10 s y leer URL + confirmar "Registered tunnel connection":
   Select-String -Path C:\Users\CEFYE\chat\cf_tunel.log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com'
   ```
2. **`.env`**: reemplazar la URL del túnel anterior por la nueva en **3 líneas**
   (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DOMINIOS_PERMITIDOS`).
3. **Django** (verificar puerto libre ANTES — lección de huérfanos):
   ```powershell
   Get-NetTCPConnection -LocalPort 8000 -State Listen    # debe dar "nadie"
   . .\venv\Scripts\Activate.ps1; python manage.py runserver 8000   # en segundo plano
   ```
4. **Verificar**: `localhost:8000/health` → 200 · `<túnel>/health` → 200 ·
   batería E2E (Referer WP 200 / hostil 403 / `loader.js` 200 / `loader.css` 200).

⚠️ **Consecuencia**: cada restauración cambia la URL → el snippet de WP queda roto
hasta repetir el **Bloque B**. Es la razón principal para cerrar cuanto antes el
hosting definitivo (Bloque C).

---

# BLOQUE E — ⏸️ SIMULADO: despliegue end-to-end de producción (checklist)

**Bloqueado por**: decisión de hosting (Bloque C). **Ejecutar cuando exista dominio.**

1. [ ] Dominio/subdominio definitivo funcionando con HTTPS.
2. [ ] Código + modelo subidos; venv; `pip install -r requirements.txt`.
3. [ ] `.env` producción (`DEBUG=False`, hosts/origins nuevos, SMTP real, `DOMINIOS_PERMITIDOS=https://metododian.com`).
4. [ ] `migrate` + `collectstatic` + estáticos servidos (WhiteNoise o alias).
5. [ ] Ollama resoluble desde el hosting (paso C.2.9).
6. [ ] `/health` → 200 · `/chat/` → 200 · estáticos → 200.
7. [ ] Snippet de WP actualizado al dominio definitivo (**Bloque B**).
8. [ ] E2E completo + seguridad (hostil → 403, CSP correcta).
9. [ ] Prueba de correo (cierre de conversación → email al admin).
10. [ ] `.env` de desarrollo (túnel) documentado para volver si hace falta.
11. [ ] Log + commit/push final (con aprobación).
12. [ ] Retirar el túnel de la demo (dejar solo producción).

---

# BLOQUE F — ⏸️ SIMULADO: validación Docker (no instalado)

**Bloqueado por**: Docker Desktop no instalado en la máquina.

1. Instalar:
   ```powershell
   winget install --id Docker.DockerDesktop -e --accept-source-agreements --accept-package-agreements
   ```
2. Reiniciar sesión/PC → abrir Docker Desktop → esperar *Engine running*.
3. En la raíz del proyecto: `./docker_setup.sh` (build → setup → migrate).
4. Levantar: contenedor web en `WEB_PORT` (SQLite en contenedor, según `docs/dockerizacion.md`).
5. Verificar E2E contra `http://localhost:<WEB_PORT>` (health, chat, estáticos).
6. Documentar resultado en el log.

---

# BLOQUE G — ⏸️ DECISIONES DEL USUARIO (sin fecha)

| Decisión | Opciones | Cuándo |
|---|---|---|
| Página de prueba WP | Dejarla como demo · Borrarla | En cuanto el widget vuelva (Bloque B) |
| Hosting | A) preguntar · B) Hosting Python 27,20 €/mes · C) VPS | Cuando contactes con Raiola (Bloque C) |
| Ollama en producción | PC+tunel · VPS · API externa | Antes del paso E.5 |
| Log de hoy | Commit/push del plan + avances | Con aprobación |

---

## Apéndice A — URLs y datos vivos (actualizar siempre)

| Dato | Valor (8/oct/2026) |
|---|---|
| URL del túnel | `https://clocks-gather-jenny-governing.trycloudflare.com` (9/oct; **cambia siempre** en cada reinicio) |
| Página WP | `https://metododian.com/index.php/prueba-chatbot/` |
| Snippet en WP | `…/static/js/loader.js` de la URL del túnel **actual** |
| cPanel | `ha1011.raiolanetworks.es:2083` · usuario `diansis1` · cPanel 136.0.45 · disco 93 % |
| Soporte Raiola | 982 77 60 81 · chat · `raiolanetworks.com/clientes` |
| Git | `https://github.com/Diansistemas/chatbot` · rama `ramapruebas` (`93d53b6`) |
| Servicios locales | Django `:8000` · Ollama `:11434` (modelos `chatbot-*`, `llama3.2`) |
| Tests | 113 suite + 34 funcionales |

## Apéndice B — Comandos rápidos

```powershell
# Salud
Invoke-WebRequest http://localhost:8000/health -UseBasicParsing
Invoke-WebRequest https://<tunel>/health -UseBasicParsing

# Tests
python manage.py test            # suite (113)
.\pruebas\ejecutar_tests.ps1     # suite + funcional

# Git (copia raíz → Chatbot antes de commit)
Copy-Item <raiz>\docs\<fichero> <raiz>\Chatbot\docs\ -Force
git -C C:\Users\CEFYE\chat\Chatbot add <fichero>
git -C C:\Users\CEFYE\chat\Chatbot commit -F <msg.txt>
git -C C:\Users\CEFYE\chat\Chatbot push origin ramapruebas
```
