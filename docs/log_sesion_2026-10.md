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

## Sesión — 8 de octubre de 2026

### Paso 15 — 4ª comprobación de *Setup Python App* (pedido: "revisa")

- Sesión fresca de cPanel (`cpsess5218875777`, recién logueada por el usuario).
- Dashboard: **289.007 chars / 102 herramientas** → **0 coincidencias** "python";
  URL directa con token nuevo → **HTTP 404**. Dashboard restaurado.
- **Sin cambios**:4ª jornada comprobando (6, 7×3, 8 oct).
- El usuario decide: **por ahora no contacta con Raiola**.

### Paso 16 — Restauración de servicios (3ª del ciclo) (aprobada)

1. Túnel nuevo: `https://coalition-taxes-sellers-change.trycloudflare.com` (registrado).
2. `.env`: `favor-telecharger…` → `coalition-taxes…` (3 líneas).
3. Puerto8000 verificado libre → Django limpio.
4. Salud: `localhost/health` → **200** y `<túnel>/health` → **200**.

### Paso 17 — E2E con la URL nueva (aprobada)

- Batería: **4 OK / 0 FALLOS** (Referer WP 200, hostil 403, loader.js/css 200)
  + CSP `frame-ancestors` con la URL nueva.

### Paso 18 — Plan maestro de ejecución (pedido: "documenta paso a paso y simula…")

- Creado `docs/plan_ejecucion_paso_a_paso.md`: plan con leyenda ✅ HECHO / ⏸️ SIMULADO:
  - **Bloque B**: snippet en WordPress (7 pasos + checklist) — bloqueado por login WP.
  - **Bloque C**: Raiola — mensaje listo +3 escenarios (A1 habilitan Python con14 pasos,
    A2 contratar Hosting Python desde27,20 €/mes, A3 VPS).
  - **Bloque D**: protocolo de restauración tras cada reinicio (4 pasos).
  - **Bloque E**: checklist de producción end-to-end (11 puntos).
  - **Bloque F**: Docker (instalación + `docker_setup.sh`).
  - **Bloque G**: decisiones del usuario.
- ⏳ Pendiente de commit en ese momento.

---

## Sesión — 9 de octubre de 2026

### Paso 19 — Reinicio del entorno

- Shells de fondo cancelados: **Django y túnel caídos** (patrón diario).
  Ollama previsiblemente activo (se verifica al restaurar).
- El snippet de WP ya apuntaba a una URL muerta → widget sigue roto.

### Paso 20 — Actualización de la documentación (pedido repetido: "documenta… y simula…")

- Log actualizado con8-9/oct (este apartado).
- Plan maestro actualizado al estado real del9/oct (servicios caídos → Bloque D listo).
- Ambos ficheros: pendientes de commit/push (con aprobación).

---

## Estado al cierre de este log

| Elemento | Estado |
|---|---|
| Django `:8000` | ❌ Caído (reinicio 9/oct) — restauración: **Bloque D** del plan |
| Túnel | ❌ Detenido — URL `coalition-taxes…` muerta; nueva URL al restaurar |
| `.env` | ✅ 3 líneas con la última URL usada (se re-edita en cada restauración) |
| Snippet en WP | ❌ **Obsoleto** — sigue con `favorites-window-parts-allied` → widget roto; requiere login en WP (paso 5 pendiente) |
| cPanel *Setup Python App* | ❌ No habilitado (8/oct,4ª comprobación) — mensaje a Raiola pendiente |
| Página de prueba WP | Decidir: mantener como demo o eliminar |

### Pendientes

- [ ] Paso 5: iniciar sesión en WordPress y sustituir el snippet por la **URL actual del túnel** (Apéndice A del plan → Bloque B)
- [x] Verificación E2E con URL nueva — **hecha 3 veces** (7/oct ×2 y 8/oct, 4/4 en todas)
- [ ] Enviar el mensaje a Raiola (texto en el **Bloque C** del plan) — sin cambios tras la 4ª comprobación (8/oct)
- [x] Commit + push de este log (`b0f8ad2` + `93d53b6`)
- [ ] Commit + push del plan maestro `plan_ejecucion_paso_a_paso.md` + esta actualización (con aprobación)
- [ ] Restaurar servicios caídos (protocolo del **Bloque D**) cuando el usuario lo pida
- [ ] Cambios históricos: `docs/despliegue_wordpress.md` (ya pushado en `0a32fe4`)
