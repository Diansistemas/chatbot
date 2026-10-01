"""Test funcional completo de la aplicación.

Fases:
  1) Endpoints HTTP basicos (sin LLM)
  2) Conversacion real via HTTP: usuario -> NLP -> LLM -> respuesta
  3) Cierre por intencion "cerrar" -> pares -> resumen (LLM) -> email (consola)
  4) Bateria NLP directa (sin LLM): intenciones + entidades
  5) Limpieza y verificacion de que la BD vuelve a su estado inicial
"""
import os
import sys
import time
import traceback
from pathlib import Path

import django

# Raiz del proyecto: pruebas/funcional/ -> chat/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db.models import Max  # noqa: E402
from django.test import Client  # noqa: E402

from chat.models import Conversacion, Mensaje  # noqa: E402
from core.models import Analisis, procesar_mensaje  # noqa: E402
from entrenamiento.models import Par_Mensaje_Respuesta  # noqa: E402
from notificaciones.models import Resumen  # noqa: E402

OK = 0
FALLOS = []
CREADAS = []  # pks de conversaciones creadas por el test (para limpieza)


def check(nombre, cond, detalle=""):
    global OK
    if cond:
        OK += 1
        print(f"  [OK]    {nombre}" + (f"  -> {detalle}" if detalle else ""))
    else:
        FALLOS.append(nombre)
        print(f"  [FALLO] {nombre}" + (f"  -> {detalle}" if detalle else ""))


def get(c, path, **kw):
    kw.setdefault("SERVER_NAME", "localhost")
    return c.get(path, **kw)


def post(c, path, data=None, **kw):
    kw.setdefault("SERVER_NAME", "localhost")
    return c.post(path, data or {}, **kw)


def contar():
    return {
        "conversaciones": Conversacion.objects.count(),
        "mensajes": Mensaje.objects.count(),
        "analisis": Analisis.objects.count(),
        "pares": Par_Mensaje_Respuesta.objects.count(),
        "resumenes": Resumen.objects.count(),
    }


def fase1(c):
    print("\n=== FASE 1: endpoints HTTP (sin LLM) ===")

    r = get(c, "/")
    check("GET / (inicio)", r.status_code == 200, f"{r.status_code}")

    r = get(c, "/health")
    ok_health = r.status_code == 200 and r.json().get("status") == "ok"
    check("GET /health", ok_health, f"{r.status_code} {r.content[:60]!r}")

    r = get(c, "/v1/models")
    modelos = [m["id"] for m in r.json().get("data", [])] if r.status_code == 200 else []
    check("GET /v1/models (formato OpenAI)", r.status_code == 200 and modelos,
          f"{len(modelos)} modelos; llama3.2={'llama3.2:latest' in modelos}")

    r = get(c, "/chat/")
    check("GET /chat/ (widget sin conversacion)", r.status_code == 200, f"{r.status_code}")

    r = get(c, "/chat/?conversacion=00000000-0000-0000-0000-000000000000")
    check("GET /chat/ token inexistente", r.status_code == 200, f"{r.status_code}")

    r = get(c, "/admin/")
    check("GET /admin/ redirige a login", r.status_code in (301, 302), f"{r.status_code}")

    r = get(c, "/chat/", HTTP_REFERER="https://evil.com/roba")
    check("Referer ajeno rechazado (403)", r.status_code == 403, f"{r.status_code}")

    r = post(c, "/chat/", {"accion": "usuario", "texto": "   "})
    check("Mensaje vacio -> 400", r.status_code == 400, f"{r.status_code}")

    r = post(c, "/chat/", {"accion": "inventada"})
    check("Accion invalida -> 400", r.status_code == 400, f"{r.status_code}")

    r = post(c, "/chat/", {"accion": "bot", "mensaje_id": "999999"})
    check("bot sin conversacion -> 400", r.status_code == 400, f"{r.status_code}")


def flujo_completo(c):
    print("\n=== FASE 2: conversacion real (HTTP -> NLP -> LLM) ===")

    # --- primer mensaje: crea conversacion + bienvenida
    t0 = time.time()
    r = post(c, "/chat/", {"accion": "usuario", "texto": "Quiero contratar el plan basico por 30 euros"})
    datos = r.json() if r.status_code == 200 else {}
    check("Primer mensaje crea conversacion", r.status_code == 200 and datos.get("bienvenida"),
          f"{r.status_code}; token={datos.get('conversacion', '-')[:8]}...")
    token = datos.get("conversacion")
    mid1 = datos.get("mensaje_id")
    if not token:
        raise RuntimeError("No se creo la conversacion; abortando fases 2-3")

    # --- respuesta del bot (NLP + LLM compra)
    t0 = time.time()
    r = post(c, "/chat/", {"accion": "bot", "mensaje_id": mid1, "conversacion": token})
    d = r.json() if r.status_code == 200 else {}
    t_compra = time.time() - t0
    texto1 = d.get("bot", "")
    check("Bot responde al mensaje de compra", r.status_code == 200 and len(texto1) > 10,
          f"{r.status_code} en {t_compra:.1f}s")

    conv = Conversacion.objects.get(token=token)
    CREADAS.append(conv.pk)
    check("Flag tenemosCompra activado", conv.tenemosCompra is True, str(conv.tenemosCompra))

    a1 = Mensaje.objects.get(pk=mid1).mensaje_analisis
    ents1 = [f"{e.etiqueta.nombre}:{e.texto_detectado}" for e in a1.analisis_entidad.all()]
    check("Analisis NLP: intencion=compra",
          a1.intencion and a1.intencion.nombre == "compra",
          f"{a1.intencion.nombre if a1.intencion else '-'} conf={a1.confianza:.2f} ents={ents1}")

    print(f"    USUARIO: Quiero contratar el plan basico por 30 euros")
    print(f"    BOT    : {texto1[:110]}")

    # --- 409: doble respuesta al mismo mensaje
    r = post(c, "/chat/", {"accion": "bot", "mensaje_id": mid1, "conversacion": token})
    check("Doble respuesta al mismo mensaje -> 409", r.status_code == 409, f"{r.status_code}")

    # --- 404: mensaje inexistente
    r = post(c, "/chat/", {"accion": "bot", "mensaje_id": "999999", "conversacion": token})
    check("Mensaje inexistente -> 404", r.status_code == 404, f"{r.status_code}")

    # --- segundo mensaje: consulta tecnica
    r = post(c, "/chat/", {"accion": "usuario", "texto": "Cuanto tarda la revision general", "conversacion": token})
    mid2 = r.json().get("mensaje_id") if r.status_code == 200 else None
    check("Segundo mensaje aceptado", r.status_code == 200 and mid2, f"{r.status_code}")

    t0 = time.time()
    r = post(c, "/chat/", {"accion": "bot", "mensaje_id": mid2, "conversacion": token})
    d = r.json() if r.status_code == 200 else {}
    t_consulta = time.time() - t0
    texto2 = d.get("bot", "")
    check("Bot responde a la consulta", r.status_code == 200 and len(texto2) > 10,
          f"{r.status_code} en {t_consulta:.1f}s")

    a2 = Mensaje.objects.get(pk=mid2).mensaje_analisis
    ents2 = [f"{e.etiqueta.nombre}:{e.texto_detectado}" for e in a2.analisis_entidad.all()]
    check("Analisis NLP: intencion=consulta_tecnica",
          a2.intencion and a2.intencion.nombre == "consulta_tecnica",
          f"{a2.intencion.nombre if a2.intencion else '-'} conf={a2.confianza:.2f} ents={ents2}")

    print(f"    USUARIO: Cuanto tarda la revision general")
    print(f"    BOT    : {texto2[:110]}")

    # --- polling estado
    r = post(c, "/chat/", {"accion": "estado", "desde_id": 0, "conversacion": token})
    d = r.json() if r.status_code == 200 else {}
    check("Polling estado devuelve mensajes del bot",
          r.status_code == 200 and len(d.get("mensajes", [])) >= 2,
          f"{len(d.get('mensajes', []))} mensajes; esperando={d.get('esperando')}")
    check("Estado: conversacion abierta", d.get("cerrada") is False, str(d.get("cerrada")))

    return token, conv


def fase3_cierre(c, token, conv):
    print("\n=== FASE 3: cierre por intencion + resumen + email ===")

    r = post(c, "/chat/", {"accion": "usuario", "texto": "Hasta luego que tengas buen dia", "conversacion": token})
    mid3 = r.json().get("mensaje_id") if r.status_code == 200 else None
    check("Mensaje de despedida aceptado", r.status_code == 200 and mid3, f"{r.status_code}")

    t0 = time.time()
    r = post(c, "/chat/", {"accion": "bot", "mensaje_id": mid3, "conversacion": token})
    d = r.json() if r.status_code == 200 else {}
    t_cierre = time.time() - t0
    check("Bot cierra la conversacion", r.status_code == 200 and d.get("cerrada") is True,
          f"{r.status_code} en {t_cierre:.1f}s; cerrada={d.get('cerrada')}")
    print(f"    BOT (cierre): {d.get('bot', '')[:110]}")

    conv.refresh_from_db()
    check("Estado en BD = cerrada", conv.estado == "cerrada", conv.estado)
    check("fecha_fin registrada", conv.fecha_fin is not None, str(conv.fecha_fin))

    pares = Par_Mensaje_Respuesta.objects.filter(mensaje_chatbot__conversacion=conv)
    check("Pares mensaje-respuesta generados en el cierre", pares.count() == 3,
          f"{pares.count()} pares")

    resumen = Resumen.objects.filter(conversacion=conv).first()
    check("Resumen de compra generado (LLM)", resumen is not None,
          f"pk={resumen.pk if resumen else '-'}")
    if resumen:
        print(f"    RESUMEN (120 chars): {resumen.texto[:120].replace(chr(10), ' | ')}...")

    # --- tras cerrar: mensajes nuevos rechazados
    r = post(c, "/chat/", {"accion": "usuario", "texto": "hola?", "conversacion": token})
    check("Mensaje a conversacion cerrada -> 410", r.status_code == 410, f"{r.status_code}")

    r = post(c, "/chat/", {"accion": "cerrar", "conversacion": token})
    check("Cierre manual sobre ya cerrada -> ok", r.status_code == 200, f"{r.status_code}")


def fase4_nlp():
    print("\n=== FASE 4: bateria NLP directa (sin LLM) ===")
    tmp = Conversacion.objects.create()
    CREADAS.append(tmp.pk)

    textos = [
        "Hola buenos dias, tiene algun turno libre",          # chitchat -> otro
        "Quiero el plan premium por 99 euros",                # compra
        "Mi pagina web no carga y da error 500",              # consulta_tecnica
        "Confirmo el presupuesto de 200 euros",               # confirmacion
        "Nos vemos, adios",                                   # cerrar
        "Habla conmigo una persona por favor",                # contactar_humano
        "Necesito un operador tecnico ya",                    # solicitar_agente
        "Me duele la cabeza desde ayer",                     # OOD -> otro (no cerrar)
        "Ponme musica rock",                                  # OOD -> otro
        "Quiero devolver el dinero que pague",                # reclamacion -> otro
    ]
    for texto in textos:
        m = Mensaje.objects.create(conversacion=tmp, texto=texto, remitente="usuario")
        a = procesar_mensaje(m)
        ents = [f"{e.etiqueta.nombre}:{e.texto_detectado}" for e in a.analisis_entidad.all()]
        nombre = a.intencion.nombre if a.intencion else "-"
        print(f"    {texto[:46]!r:50} -> {nombre:17} ({a.confianza:.2f})  {', '.join(ents) or 'sin ents'}")


def fase5_limpieza(base, base_max_par, base_max_resumen):
    print("\n=== FASE 5: limpieza y estado de la BD ===")
    for pk in CREADAS:
        Conversacion.objects.filter(pk=pk).delete()

    # Por si algun objeto quedo huérfano (FK no cascada)
    if base_max_par:
        Par_Mensaje_Respuesta.objects.filter(pk__gt=base_max_par).delete()
    if base_max_resumen:
        Resumen.objects.filter(pk__gt=base_max_resumen).delete()

    fin = contar()
    for clave in base:
        check(f"BD restaurada: {clave}", fin[clave] == base[clave],
              f"inicio={base[clave]} fin={fin[clave]}")


def main():
    print("=" * 70)
    print("TEST FUNCIONAL DE LA APLICACION")
    print("=" * 70)
    base = contar()
    base_max_par = Par_Mensaje_Respuesta.objects.aggregate(m=Max("pk"))["m"] or 0
    base_max_resumen = Resumen.objects.aggregate(m=Max("pk"))["m"] or 0
    print(f"Estado inicial BD: {base}")

    c = Client()
    t_total = time.time()

    fase1(c)

    token = conv = None
    try:
        token, conv = flujo_completo(c)
        fase3_cierre(c, token, conv)
    except Exception:
        FALLOS.append("flujo_completo/fase3 (excepcion)")
        traceback.print_exc()

    try:
        fase4_nlp()
    except Exception:
        FALLOS.append("fase4 (excepcion)")
        traceback.print_exc()

    fase5_limpieza(base, base_max_par, base_max_resumen)

    print("\n" + "=" * 70)
    print(f"RESULTADO: {OK} OK / {len(FALLOS)} FALLOS  ({time.time() - t_total:.0f}s totales)")
    if FALLOS:
        for f in FALLOS:
            print(f"  FALLO: {f}")
    print("=" * 70)
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
