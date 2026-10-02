# Despliegue del widget en WordPress — documentación paso a paso

> Fecha: 2 de octubre de 2026
> Estado: **prueba end-to-end completada con éxito** (vía túnel temporal);
> despliegue definitivo pendiente de respuesta de Raiola Networks.
> Rama: `ramapruebas` — commit `8e9b5df`.

---

## Resumen en una línea

El chatbot Django (con NLP spaCy y LLM Ollama) está **embebido y funcionando**
en una página de WordPress (`metododian.com`) a través de un túnel temporal de
Cloudflare, con validación completa de seguridad (Referer/Origin/CSP) y
persistencia de conversación.

---

## Paso 0 — Contexto y requisitos

- WordPress del cliente: `https://metododian.com` (WP 7.1.2 + LiteSpeed Cache).
- Hosting del WordPress: **Raiola Networks**, cPanel *jupiter* en
  `ha1011.raiolanetworks.es:2083` (usuario `diansis1`, home `/home/diansis1`).
- El chatbot corre en local: `http://localhost:8000` + Ollama en `localhost:11434`.
- Requisito de seguridad del widget: el chat solo puede embeberse (iframe) en
  los dominios de `DOMINIOS_PERMITIDOS`, comprobado por cabecera `Referer`
  (+ `Origin` en POST) y por CSP `frame-ancestors`.

---

## Paso 1 — Diagnóstico del hosting: ¿corre Django ahí?

Se comprobó **tres veces de forma independiente** si el cPanel dispone de la
herramienta *"Setup Python App"* (necesaria para ejecutar Django en hosting
compartido con Passenger):

| # | Comprobación | Resultado |
|---|---|---|
| 1 | Dashboard completo: 102 enlaces, todos los grupos (Email, Archivos, Bases de datos, Dominios, Métrica, Seguridad, Software, Avanzado, Preferencias, Applications) | ❌ Ninguna herramienta Python |
| 2 | Acceso directo `/frontend/jupiter/software/pythonApp/index.html` y `/software/index.html` | ❌ Error 404 |
| 3 | Buscador global del panel (catálogo de 160.900 caracteres dentro de `CP-HEADER`) | ❌ Cero menciones a "python", "setup" o "passenger" |

Además, el grupo **Applications** del dashboard es solo *Installatron*
(CMS: WordPress, PrestaShop, Joomla...), no apps Python.

**Sí tiene**: Terminal (SSH), Acceso SSH, Control de versión de Git,
Dominios, SSL/TLS, Administrador de archivos.

**Conclusión**: en este servidor/plan no se puede ejecutar Django.
Raiola documenta la herramienta en su guía oficial
(`raiolanetworks.com/ayuda/despliegue-aplicacion-python-hosting-python-cpanel/`),
así que queda pendiente pedir que la activen (Track A).

⚠️ **Dato a vigilar**: el disco de la cuenta está al **93 % (46,56 / 50 GB)**.
Cualquier despliegue en el mismo hosting exige liberar ~2 GB
(entorno virtual ~1 GB + modelo spaCy ~630 MB).

---

## Paso 2 — Decisión: Track A + Track D

| Track | Descripción | Coste | Estado |
|---|---|---|---|
| **A** | Pedir a Raiola que habilite *Setup Python App* → todo en el mismo hosting | 0 € | ⏳ Pendiente de respuesta (mensaje redactado, ver Apéndice C) |
| **D** | Túnel gratuito de Cloudflare desde el PC local → prueba real ya | 0 € | ✅ Completado (este documento) |
| B (reserva) | VPS con Docker (`docker_setup.sh`) si Raiola dice que no | ~5-10 €/mes | No elegido aún |

---

## Paso 3 — Túnel de Cloudflare (exponer localhost con HTTPS)

1. Instalar cloudflared:
   ```
   winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
   ```
   Binario: `C:\Program Files (x86)\cloudflared\cloudflared.exe` (v2026.9.3).
   Nota: los shells abiertos antes de instalar no ven el PATH nuevo → usar
   siempre la ruta completa.

2. Arrancar el túnel (segundo plano):
   ```
   & "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000 > C:\Users\CEFYE\chat\cf_tunel.log 2>&1
   ```

3. Leer la URL asignada en el log (aleatoria en cada arranque):
   ```
   Select-String -Path C:\Users\CEFYE\chat\cf_tunel.log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com'
   ```
   URL de la sesión: **`https://favorites-window-parts-allied.trycloudflare.com`**

> ⚠️ **La URL es temporal**: cambia si se reinicia el túnel y sólo vive
> mientras el PC esté encendido. Si cambia hay que actualizar `.env`
> (ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS / DOMINIOS_PERMITIDOS) y el snippet
> de WordPress.

---

## Paso 4 — Configuración de `.env`

Añadir/ajustar en la raíz del proyecto (`.env` está en `.gitignore`):

```ini
DEBUG = True

# Prueba del widget via tunel Cloudflare (dominio aleatorio, cambia si se reinicia)
ALLOWED_HOSTS=favorites-window-parts-allied.trycloudflare.com
CSRF_TRUSTED_ORIGINS=https://favorites-window-parts-allied.trycloudflare.com

# Origenes que pueden embeber/consultar el widget (Referer + CSP frame-ancestors)
DOMINIOS_PERMITIDOS=https://diansitemas.com, http://localhost:8000, https://metododian.com, https://favorites-window-parts-allied.trycloudflare.com
```

Reiniciar Django para que aplique:

```powershell
. .\venv\Scripts\Activate.ps1
python manage.py runserver 8000
```

---

## Paso 5 — Verificación HTTP a través del túnel

Batería de comandos (PowerShell `Invoke-WebRequest`):

| Prueba | Esperado | Resultado |
|---|---|---|
| `GET /health` | 200 `{"status":"ok"}` | ✅ 200 |
| `GET /chat/` sin Referer | 200 + CSP `frame-ancestors ... https://metododian.com ...` | ✅ 200 |
| `GET /chat/` con `Referer: https://metododian.com/` | 200 | ✅ 200 |
| `GET /chat/` con `Referer: https://evil.example/` | 403 | ✅ 403 |
| `GET /static/js/loader.js` | 200 | ✅ 200 |
| `GET /static/css/loader.css` | 200 | ✅ 200 |

---

## Paso 6 — Snippet en WordPress

1. `https://metododian.com/wp-admin` → **Páginas** → **Añadir nueva**.
2. Añadir bloque **HTML personalizado** y pegar:
   ```html
   <script src="https://favorites-window-parts-allied.trycloudflare.com/static/js/loader.js"></script>
   ```
3. **Publicar**. Si no aparece: **LiteSpeed Cache → Purge All** y recargar.
4. Página creada en esta prueba:
   **`https://metododian.com/index.php/prueba-chatbot/`**

El `loader.js` deduce el origen del chatbot de la URL del propio
`<script src>` (override opcional con `data-url`, fallback
`http://localhost:8000`), así que el snippet sirve para cualquier dominio
sin cambios.

---

## Paso 7 — Prueba end-to-end (resultado)

- ✅ Botón del chat visible abajo a la derecha en la página de WordPress.
- ✅ Iframe `https://<tunel>/chat/` carga con CSP correcta.
- ✅ Conversación real: usuario → NLP (`intencion=otro`, confianza 1.00)
  → LLM Ollama (`OLLAMA OK modelo=chatbot-otro`) → respuesta renderizada.
- ✅ **Persistencia**: al recargar la página, `localStorage` conserva el token
  y el iframe recarga con `?conversacion=<uuid>` (misma conversación).
- ✅ Seguridad: Referer hostil rechazado con 403.

---

## Paso 8 — Bug encontrado y corregido: CSRF en iframe de terceros

### Síntoma

El envío de mensajes devolvía `403` y el widget mostraba
*"Ha habido un error, inténtalo de nuevo."*.

### Diagnóstico

1. Red del navegador: `POST https://<tunel>/chat/ → 403`.
2. Log del servidor:
   ```
   Forbidden (CSRF cookie not set.): /chat/
   "POST /chat/ HTTP/1.1" 403
   ```
3. Dentro del iframe: `document.cookie` = **vacío** → el navegador bloqueó la
   cookie `csrftoken` por ser de un **tercer origen** (el iframe es de otro
   dominio que la página que lo embebe).

El JS sí enviaba el token (`X-CSRFToken` desde el campo oculto
`csrfmiddlewaretoken`), pero Django exige además la cookie para la doble
comparación → rechazo.

### Solución (commit `8e9b5df`)

1. **`core/views.py`** — `@method_decorator(csrf_exempt, name='dispatch')`
   en `ChatWidgetView`. El widget es público (sin sesiones que secuestrar) y
   la cookie CSRF es imposible en un iframe de terceros.
2. **`core/mixins.py`** — red de seguridad equivalente: en métodos no
   seguros (POST...) se valida la cabecera **`Origin`** (los navegadores la
   envían SIEMPRE en un POST, aunque el `Referrer-Policy` oculte el
   `Referer`) contra el host propio + `DOMINIOS_PERMITIDOS`. Sin `Origin`
   (clientes antiguos) se deja pasar y manda la comprobación de `Referer`.

Los tests existentes no se ven afectados: `test_csrf_protection` sólo exige
que `CsrfViewMiddleware` siga en `MIDDLEWARE`, y `test_comprehensive`,
`test_views` y el funcional siguen en verde.

---

## Paso 9 — Integración de commits remotos y revalidación

Mientras se trabajaba, el remoto recibió 2 commits:

- `8e5b282` — NLP: clasificar en minúsculas (la mayúscula inicial ya no cambia
  la intención).
- `c4f9cef` — merge de ambos historiales.

Archivos tocados por el remoto: `core/acceso.py`, `core/models.py`,
`notificaciones/models.py`, `pruebas/aplicacion/tests.py`,
`pruebas/evaluacion/verificar_nlp.py` — **cero solape** con los cambios
locales.

Protocolo aplicado (el de siempre):

1. `git pull --rebase origin ramapruebas` → rebase limpio.
2. Copiar los 5 archivos remotos al árbol de ejecución y verificar igualdad
   byte a byte de **todos** los tracked (`git ls-files` + `Get-FileHash`) →
   0 diferencias.
3. Revalidación completa:

   | Suite | Resultado |
   |---|---|
   | `python manage.py test` | **113 tests OK** (112 previos + 1 del remoto) |
   | `pruebas/ejecutar_tests.ps1` → funcional | **34 OK / 0 FALLOS** (67 s) |
   | Exit code | **EXIT=0** |

   Bonus comprobado: `Paso a saludar` y `paso a saludar` ahora clasifican
   igual (`otro`).

4. `git push origin ramapruebas` → `c4f9cef..8e9b5df`.

---

## Paso 10 — Commit final

```
8e9b5df Widget embebible multi-origen + fix CSRF para iframes de terceros
```

Contenido: `static/js/loader.js` (origen deducido del `<script src>`),
`core/views.py` (`csrf_exempt`), `core/mixins.py` (check de `Origin` en POST).

---

## Pendientes

- [ ] **Track A**: enviar el mensaje a Raiola (Apéndice C) y esperar respuesta.
- [ ] Si Raiola habilita *Setup Python App*: subdominio `chat.metododian.com`,
      liberar disco (~2 GB), subir código + modelo spaCy (630 MB), `migrate`,
      y `DOMINIOS_PERMITIDOS=https://metododian.com`.
- [ ] Si Raiola dice que no: valorar VPS + Docker (`docker_setup.sh`).
- [ ] **Ollama en producción**: no corre en hosting compartido → prever
      `OLLAMA_HOST` externo (VPS, o túnel al PC como el actual).
- [ ] Sustituir el snippet de prueba por el definitivo cuando exista dominio.
- [ ] Validación Docker end-to-end (Docker no instalado en la máquina).
- [ ] Decidir destino de la página de prueba de WordPress (dejar o borrar).

---

## Apéndice A — Comandos de la sesión

```powershell
# Arrancar el chatbot
cd C:\Users\CEFYE\chat
. .\venv\Scripts\Activate.ps1
python manage.py runserver 8000

# Arrancar el túnel (la URL cambia en cada arranque)
& "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000 > C:\Users\CEFYE\chat\cf_tunel.log 2>&1
Select-String -Path C:\Users\CEFYE\chat\cf_tunel.log -Pattern 'trycloudflare\.com'

# Verificación rápida
Invoke-WebRequest https://<tunel>/health -UseBasicParsing
Invoke-WebRequest https://<tunel>/chat/  -UseBasicParsing

# Tests
. .\venv\Scripts\Activate.ps1
python manage.py test          # suite (113)
.\pruebas\ejecutar_tests.ps1   # suite + funcional
```

## Apéndice B — Archivos tocados en esta fase

| Archivo | Cambio |
|---|---|
| `static/js/loader.js` | Origen deducido de `document.currentScript.src` (override `data-url`, fallback localhost) |
| `core/views.py` | `csrf_exempt` en `ChatWidgetView` (+ comentario explicativo) |
| `core/mixins.py` | `_origen_permitido()` + validación `Origin` en métodos no seguros |
| `.env` | `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DOMINIOS_PERMITIDOS` (gitignored) |
| `docs/despliegue_wordpress.md` | Este documento |

## Apéndice C — Mensaje pendiente para Raiola

**Asunto:** `No aparece "Setup Python App" en mi cPanel - despliegue de aplicación Django`

```
Hola,

Soy cliente de alojamiento con cPanel y necesito desplegar una aplicación 
Django en un subdominio, pero no encuentro la herramienta "Setup Python App" 
en mi panel.

Datos de la cuenta:
  - Usuario de cPanel: diansis1
  - Servidor: ha1011.raiolanetworks.es (panel jupiter)
  - Home: /home/diansis1

Comprobaciones realizadas:
  - En la sección "Software" solo aparecen: PHP/Perl, Installatron, 
    LiteSpeed Cache, X-Ray y similares. No hay "Setup Python App".
  - Búsqueda global del panel: sin resultados para "Python".
  - Acceso directo a /frontend/jupiter/software/pythonApp/index.html: error 404.

En vuestra guía "Despliegue de una aplicación Python en un hosting con 
cPanel" se indica que esta herramienta está disponible en los hostings cPanel, 
por lo que no sé si está deshabilitada en mi cuenta/servidor o si simplemente 
no dispongo de ella en mi plan.

Necesitaría:
  1. Python 3.12 o superior (Django 6.1 lo exige).
  2. Ejecutar la app bajo un subdominio con HTTPS.

¿Podríais confirmarme si es posible habilitar "Setup Python App" en mi cuenta, 
o en caso de no estar disponible, indicarme la alternativa recomendada para 
desplegar una aplicación Django en mi plan? También sé que tengo acceso 
SSH/Terminal por si sirve de algo.

Muchas gracias por vuestra ayuda.
```

Teléfono de soporte (24/7): **982 77 60 81** — Área de clientes:
`raiolanetworks.com/clientes`
