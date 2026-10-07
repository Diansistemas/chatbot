# Log de sesiones — 6 y 7 de octubre de 2026

> Sesión de trabajo sobre el despliegue del widget en WordPress.
> Rama: `ramapruebas` (remoto: `https://github.com/Diansistemas/chatbot`).
> Protocolo: **permiso explícito del usuario para cada paso** y documentación de cada uno.

---

## Sesión — 6 de octubre de 2026

### Paso 0 — Diagnóstico tras el reinicio (solo lectura)

| Elemento | Estado |
|---|---|
| Django `:8000` | ❌ Caído (cancelado con el reinicio de sesión) |
| Túnel Cloudflare | ❌ Detenido — URL anterior `favorites-window-parts-allied…` muerta |
| Ollama `:11434` | ✅ Activo |
| Repo `Chatbot` | ✅ `ramapruebas` sincronizada con `origin` = `Diansistemas/chatbot` (`0a32fe4`) |
| Página WP | ⚠️ Snippet apunta al túnel muerto → widget roto |

📌 Observación: la raíz `C:\Users\CEFYE\chat` pasó a ser repo git también (no se toca).

### Paso 1 — Arrancar Django (aprobado)

- `python manage.py runserver 8000` en segundo plano (`sh_10ff1f857001eYo8N7eB4zRl95`).
- Verificación: `GET /health` → **200** `{"status":"ok","django":"6.1.1"}`.

### Paso 2 — Arrancar túnel (aprobado)

- `cloudflared tunnel --url http://localhost:8000` (`sh_10ff39963001rKW4UOb8eekwu0`).
- **URL nueva**: `https://infrared-drawn-infections-became.trycloudflare.com`.

### Paso 3 — Actualizar `.env` + reiniciar Django (aprobado)

- Sustituida la URL del túnel en **3 líneas**: `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DOMINIOS_PERMITIDOS`.
- Reinicio (matar PIDs viejos — primero quedó un proceso, se mató también el segundo `PID 18008`).
- Verificación: `localhost/health` → 200 y `<túnel>/health` → 200 (`sh_10ff818640017Djo7ypNn8kahJ`).

### Paso 4 — Verificación E2E vía túnel (aprobado): **4 OK / 0 FALLOS**

| Prueba | Resultado |
|---|---|
| `GET /chat/` con `Referer: https://metododian.com/` | ✅ 200 |
| `GET /chat/` con `Referer: https://evil.example/` | ✅ **403** |
| `GET /static/js/loader.js` | ✅ 200 |
| `GET /static/css/loader.css` | ✅ 200 |
| CSP `frame-ancestors` | ✅ incluye `metododian.com` + URL del túnel |

### Paso 5 — Snippet en WordPress (parcial / bloqueado)

- Decisión del usuario: "hazlo tú" → abierta pestaña `wp-admin`.
- ⛔ **WordPress pide iniciar sesión** (caducó tras 4 días) → paso **pendiente**.
- Cambio previsto: `<script src>` → URL nueva del túnel.

### Paso 6 — Comprobación *Setup Python App* en cPanel (aprobado)

Sesión de cPanel válida, cPanel **136.0.45**:

| # | Comprobación | Resultado |
|---|---|---|
| 1 | Escaneo del documento completo (289.004 chars, **102 herramientas**) | ❌ 0 coincidencias de "python" |
| 2 | URL directa con token: `/cpsess…/software/pythonApp/index.html` | ❌ **HTTP 404** |

**Conclusión**: Raiola aún no ha habilitado la herramienta → sigue pendiente enviar el
mensaje del Apéndice C de `docs/despliegue_wordpress.md`.

---

## Sesión — 7 de octubre de 2026

### Reinicio de la sesión

- Ambos shells de fondo (Django y cloudflared) **cancelados** → servicios caídos.
- Fecha nueva: 7/oct/2026.

### Paso 6b — Repetir comprobación *Setup Python App* (pedido: "vuelve a comprobar")

- Primera tentativa: ⛔ sesión de cPanel **caducada** → el usuario se loguea de nuevo
  (`cpsess8749990576`).
- Con sesión nueva:

| # | Comprobación | Resultado |
|---|---|---|
| 1 | Documento completo (289.219 chars, 102 herramientas) | ❌ 0 coincidencias de "python" |
| 2 | URL directa con token nuevo | ❌ **HTTP 404** |
| — | Dashboard restaurado tras la prueba | ✅ |

**Conclusión**: **sigue sin estar** — respuesta de Raiola pendiente.

### Paso 7 — Restaurar servicios (aprobado: "arranca ambos" + `.env`)

1. Túnel nuevo: `https://bright-windsor-targeted-linda.trycloudflare.com`
   (`sh_1151b9c87001gmvoz4BQGUjjVV`) — registro QUIC OK.
2. `.env` actualizado (3 líneas): `infrared…` → `bright-windsor…`.
3. Django arrancado → pero `<túnel>/health` fallaba y `curl` devolvió **HTTP 400**.

#### ⚠️ Incidencia: proceso huérfano con `.env` viejo

- El volcado del error 400 mostraba `ALLOWED_HOSTS = […, 'infrared-…']` (URL antigua).
- Diagnóstico: **2 PIDs** escuchando en :8000 — `21384` (08:39:14, huérfano del arranque
  anterior, con la configuración vieja) y `17612` (el nuevo).
- El huérfano retenía el puerto y respondía él → `DisallowedHost` 400.
- **Solución**: matar ambos PIDs → verificar puerto libre → arrancar Django limpio
  (`sh_1151eb945001weEX3p4AcJjT7I`).
- Verificación final: `localhost/health` → **200** y `<túnel>/health` → **200**.

📌 **Lección aprendida**: antes de arrancar Django, comprobar que **nadie escucha en
:8000** (`Get-NetTCPConnection -LocalPort 8000 -State Listen`); el StatReloader puede
dejar procesos huérfanos tras cancelar un shell.

### Paso 8 — Este log

- Creado `docs/log_sesion_2026-10.md`.

---

## Continuación — 7 de octubre (pasos 9-14)

### Paso 9 — Verificación E2E con la URL `bright-windsor…` (aprobado)

- Batería completa: **4 OK / 0 FALLOS** (Referer WP 200, hostil 403, loader.js/css 200)
  y CSP `frame-ancestors` correcta.

### Paso 10 — Commit + push del log (aprobado)

- `b0f8ad2` "Docs: log de sesiones 6-7 octubre…" → `0a32fe4..b0f8ad2` en
  `https://github.com/Diansistemas/chatbot`; `ramapruebas` sincronizada.

### Paso 11 — 3ª comprobación de *Setup Python App* (pedido: "comprueba cpanel")

- La sesión había caducado de nuevo → re-login del usuario (`cpsess4064864084`).
- Resultado: dashboard 289.228 chars / 102 herramientas → **0 coincidencias** "python";
  URL directa con token nuevo → **HTTP 404**. Dashboard restaurado.
- **Sigue sin estar** habilitada la herramienta.

### Paso 12 — 2ª caída de servicios del día (detectada por "comprueba")

- Django `:8000` caído, `cloudflared` detenido y DNS `bright-windsor…` ya no resolvía
  (túnel muerto). Causa: **reinicio del entorno entre mensajes** (los shells de fondo
  desaparecen — patrón repetido).
- Además: **3ª caducidad** de la sesión de cPanel en el mismo día.

### Paso 13 — Restauración (aprobada)

1. Túnel nuevo: `https://favor-telecharger-complicated-excitement.trycloudflare.com`
   (conexión QUIC registrada).
2. `.env` actualizado: `bright-windsor…` → `favor-telecharger…` (3 líneas).
3. Puerto 8000 verificado **libre** antes de arrancar (lección aplicada) → Django limpio,
   **1 solo listener** (PID 11804, sin huérfanos).
4. Verificación: `localhost/health` → **200** y `<túnel>/health` → **200**.

### Paso 14 — E2E con la URL `favor-telecharger…` (aprobado)

- Batería: **4 OK / 0 FALLOS** + CSP correcta con la URL nueva.
- ⚠️ El snippet de WordPress **sigue** apuntando a `favorites-window-parts-allied`
  (paso 5 pendiente: requiere login en WP — el usuario lo pospuso).

---

## Estado al cierre de este log

| Elemento | Estado |
|---|---|
| Django `:8000` | ✅ Activo (PID limpio, `.env` nuevo) |
| Túnel | ✅ `https://favor-telecharger-complicated-excitement.trycloudflare.com` (reincorporado tras la 2ª caída) |
| `.env` | ✅ 3 líneas con la URL actual |
| Snippet en WP | ❌ **Obsoleto** — sigue con `favorites-window-parts-allied` → widget roto; requiere login en WP (paso 5 pendiente) |
| cPanel *Setup Python App* | ❌ No habilitado (7/oct) — mensaje a Raiola pendiente |
| Página de prueba WP | Decidir: mantener como demo o eliminar |

### Pendientes

- [ ] Paso 5: iniciar sesión en WordPress y actualizar el snippet a `favor-telecharger…`
- [x] Verificación E2E con URL nueva — **hecha 2 veces** (7/oct: pasos 9 y 14, 4/4 ambas)
- [ ] Enviar el mensaje a Raiola (Apéndice C de `docs/despliegue_wordpress.md`)
- [x] Commit + push de este log (`b0f8ad2` + actualización de continuidad)
- [ ] Cambios históricos: `docs/despliegue_wordpress.md` (ya pushado en `0a32fe4`)
