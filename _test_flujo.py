"""Flujo completo: conversacion -> cierre -> resumen -> email -> smtp4dev."""
import os
import traceback

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from chat.models import Conversacion, Mensaje  # noqa: E402
from core.models import responder  # noqa: E402
from notificaciones.models import crear_resumen  # noqa: E402

BIENVENIDA = "Hola, soy el asistente virtual de Dian Sistemas ¿que necesitas?"

# 1. Creamos conversacion y enviamos mensajes
conv = Conversacion.objects.create()
Mensaje.objects.create(conversacion=conv, texto=BIENVENIDA, remitente="chatbot")

MENSAJES = [
    "Quiero contratar la revision general",
    "Cuanto tarda la revision general",
    "Ya he terminado, gracias",
]

for texto in MENSAJES:
    mensaje = Mensaje.objects.create(conversacion=conv, texto=texto, remitente="usuario")
    try:
        respuesta = responder(mensaje)
        print(f"USUARIO : {texto}")
        print(f"BOT     : {respuesta.texto[:80] if respuesta else 'NONE'}...")
    except Exception:
        print(f"USUARIO : {texto}")
        traceback.print_exc()
    print("---")

conv.refresh_from_db()
print(f"Estado conversacion: {conv.estado}")
print(f"tenemosCompra: {conv.tenemosCompra}")

# 2. Creamos y enviamos el resumen (en produccion lo hace el signal al_cerrar_conversacion; aqui lo llamamos a mano)
print("\n=== GENERANDO RESUMEN ===")
try:
    resumen = crear_resumen(conv)
    print(f"Resumen creado: pk={resumen.pk}, tipo={resumen.tipo}")
    print(f"Texto (primeros 200 chars): {resumen.texto[:200]}...")

    print("\n=== ENVIANDO EMAIL ===")
    enviado = resumen.enviar_resumen()
    print(f"enviar_resumen() -> {enviado}")
except Exception:
    traceback.print_exc()
