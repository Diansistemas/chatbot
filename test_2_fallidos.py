import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from chat.models import Conversacion, Mensaje, Pedido, Servicio
from core.models import responder, procesar_mensaje, crear_pedido_si_completo

resultados = []

# --- Test 1: Auto-pedido en fallback con email ---
c = Conversacion.objects.create(dominio="test")
Mensaje.objects.create(conversacion=c, texto="quiero un presupuesto", remitente="usuario")
Mensaje.objects.create(conversacion=c, texto="el precio es 5000", remitente="chatbot")
Mensaje.objects.create(conversacion=c, texto="acepto", remitente="usuario")
for m in c.conversacion_mensajes.filter(remitente="usuario"):
    a = procesar_mensaje(m)
    if a.intencion.nombre == "compra":
        c.tenemosCompra = True
        c.save(update_fields=["tenemosCompra"])
m_email = Mensaje.objects.create(
    conversacion=c,
    texto="la empresa se llama Test SL, email test@test.com",
    remitente="usuario",
)
resp = responder(m_email)
c.refresh_from_db()
ok1 = c.conversacion_pedido.exists()
resultados.append(("Auto-pedido: En fallback con email", ok1, f"pedido={c.conversacion_pedido.exists()}"))

# --- Test 2: contactar_humano sin pedido pide datos ---
c2 = Conversacion.objects.create(dominio="test")
Mensaje.objects.create(conversacion=c2, texto="hola", remitente="usuario")
m2 = Mensaje.objects.create(conversacion=c2, texto="quiero hablar con un agente", remitente="usuario")
resp2 = responder(m2)
pide = "datos de contacto" in resp2.texto.lower()
resultados.append(("Contactar humano: Sin pedido -> pide datos", pide, resp2.texto[:120].replace("\n", " ")))

# --- Test 3: contactar_humano con pedido transfiere ---
c3 = Conversacion.objects.create(dominio="test")
Mensaje.objects.create(conversacion=c3, texto="quiero presupuesto", remitente="usuario")
Pedido.objects.create(
    conversacion=c3, nombre="Test", direccion="Dir",
    servicio=Servicio.objects.first(), presupuesto=1000, forma_contacto="test@test.com",
)
m3 = Mensaje.objects.create(conversacion=c3, texto="quiero hablar con un agente", remitente="usuario")
resp3 = responder(m3)
transfiere = "conect" in resp3.texto.lower() or "agente" in resp3.texto.lower()
resultados.append(("Contactar humano: Con pedido -> transfiere", transfiere, resp3.texto[:120].replace("\n", " ")))

print()
for nombre, ok, det in resultados:
    print(f"  [{'PASS' if ok else 'FAIL'}] {nombre}")
    print(f"         {det}")
pasados = sum(1 for _, ok, _ in resultados if ok)
print(f"\nTOTAL: {pasados}/{len(resultados)} pasados")
