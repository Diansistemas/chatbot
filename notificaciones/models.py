import logging

from django.db import models
from chat.models import Conversacion
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from chat.models import Mensaje, Pedido
from core.acceso import generar_resumen_llm


logger = logging.getLogger(__name__)

# Transcripcion de una conversacion
def transcripcion(conversacion):
    lineas = []
    for m in conversacion.conversacion_mensajes.order_by("fecha_mensaje"):
        quien = "Cliente" if m.remitente == "usuario" else "Asistente"
        lineas.append(f"{quien}: {m.texto}")
    return "\n".join(lineas)


# Generamso el texto de un resumen
def generar_resumen(conversacion):
    texto_transcripcion = transcripcion(conversacion)
    try:
        texto = generar_resumen_llm(texto_transcripcion)
    except Exception:
        logger.exception("Fallo al generar el resumen de la conversación %s", conversacion.pk)
        texto = ""

    # Si el LLM falla, escribimos un mensaje de error
    if not texto:
        texto = "(No se pudo generar el resumen automático. Transcripción completa:)\n\n" + texto_transcripcion

    return texto


def clasificar_conversacion(conversacion):
    """
    Clasifica la conversación antes de generar el resumen.
    Detecta si hay intención de compra basándose en palabras clave
    de la transcripción.
    Retorna True si es compra, False en otro caso.
    """
    texto = transcripcion(conversacion).lower()
    palabras_clave = [
        "compra", "presupuesto", "pedido", "servicio", "precio",
        "coste", "costo", "tarifa", "cuota", "reserva", "contratar",
        "cotización", "información sobre", "quiero", "necesito",
        "me gustaría", "disponible", "paquete"
    ]
    score = sum(1 for p in palabras_clave if p in texto)
    return score > 0


def crear_resumen(conversacion):
    texto = generar_resumen(conversacion)  # llamada lenta al LLM, fuera de cualquier transacción
    return Resumen.objects.create(conversacion=conversacion, texto=texto)  # escritura rápida

# Resumen para mandar por correo
class Resumen(models.Model):

    # Relacion con la conversacion
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name="resumenes")

    # Texto del resumen
    texto = models.TextField(blank=True, null=True)

    # Tipo de resumen
    tipo_choices = [
        ("sin_categoria", "Sin categoría"),
        ("consulta_tecnica", "Consulta técnica"),
        ("compra", "Compra")
    ]

    tipo = models.CharField(max_length=20, choices=tipo_choices, default="sin_categoria")    
    
    # Traduccimos en español
    class Meta:
        verbose_name = "Resumen"
        verbose_name_plural = "Resúmenes"

    def __str__(self):
        return f"Resumen Nº{self.pk}"
    
def _comprobar_datos_pedido(conversacion):
    """
    Verifica si el pedido asociado tiene los datos mínimos completos.
    Devuelve un diccionario con el estado de cada campo.
    """
    try:
        pedido = conversacion.conversacion_pedido.first()
    except Pedido.DoesNotExist:
        pedido = None

    if not pedido:
        return {
            "tiene_pedido": False,
            "nombre": False,
            "direccion": False,
            "servicio": False,
            "presupuesto": False,
            "forma_contacto": False,
        }

    return {
        "tiene_pedido": True,
        "nombre": bool(pedido.nombre),
        "direccion": bool(pedido.direccion),
        "servicio": bool(pedido.servicio),
        "presupuesto": bool(pedido.presupuesto),
        "forma_contacto": bool(pedido.forma_contacto),
    }

# Checklist de datos al principio del correo
def _construir_cuerpo_email(conversacion, resumen):
    """
    Construye el cuerpo del email con la checklist de datos AL PRINCIPIO,
    antes que el resumen LLM.
    """
    estado_datos = _comprobar_datos_pedido(conversacion)

    # --- CHECKLIST AL PRINCIPIO ---
    cuerpo = ""
    if estado_datos["tiene_pedido"]:
        if all(estado_datos.values()):
            cuerpo += "✅ Todos los datos del pedido están completos.\n\n"
        else:
            faltantes = [k for k, v in estado_datos.items() if k != "tiene_pedido" and not v]
            cuerpo += f"❌ Faltan datos: {', '.join(faltantes)}.\n\n"
    else:
        cuerpo += "⏳ No hay datos de pedido registrados aún.\n\n"

    # --- RESTO DEL CUERPO ---
    cuerpo += (
        "╔══════════════════════════════════════════════════════╗\n"
        "║     RESUMEN DE CONVERSACIÓN - CHATBOT DIANSISTEMAS  ║\n"
        "╚═════════════════════════════════════════════════════╝\n\n"
        f"📋 Conversación Nº: {conversacion.pk}\n"
        f"🌐 Dominio: {conversacion.dominio or 'N/D'}\n"
        f"📆 Inicio: {conversacion.fecha_inicio:%d/%m/%Y %H:%M}\n"
        f"📆 Fin: {conversacion.fecha_fin:%d/%m/%Y %H:%M}\n"
        f"🏷️ Tipo: {resumen.tipo}\n\n"
        "──────────────────────────────────────────────────────────\n"
        "📝 RESUMEN DEL LLM:\n"
        "──────────────────────────────────────────────────────────\n\n"
        f"{resumen.texto}\n\n"
        "──────────────────────────────────────────────────────────\n"
        "📦 DATOS DEL PEDIDO (si existen):\n"
        "──────────────────────────────────────────────────────────\n"
    )

    try:
        pedido = conversacion.conversacion_pedido.first()
    except Pedido.DoesNotExist:
        pedido = None

    if pedido:
        cuerpo += (
            f"   • Nombre: {pedido.nombre}\n"
            f"   • Dirección: {pedido.direccion}\n"
            f"   • Servicio: {pedido.servicio}\n"
            f"   • Presupuesto: €{pedido.presupuesto}\n"
            f"   • Contacto: {pedido.forma_contacto}\n"
        )
    else:
        cuerpo += "   • No hay datos de pedido registrados aún.\n"

    cuerpo += "──────────────────────────────────────────────────────────\n"
    "⚠️ CHECKLIST DE DATOS (final):\n"
    "──────────────────────────────────────────────────────────\n"
    
    if pedido:
        campos_faltantes = []
        if not pedido.nombre:
            campos_faltantes.append("nombre")
        if not pedido.direccion:
            campos_faltantes.append("dirección")
        if not pedido.servicio:
            campos_faltantes.append("servicio")
        if not pedido.presupuesto:
            campos_faltantes.append("presupuesto")
        if not pedido.forma_contacto:
            campos_faltantes.append("forma de contacto")

        if campos_faltantes:
            cuerpo += f"   ❌ Faltan: {', '.join(campos_faltantes)}\n"
        else:
            cuerpo += "   ✅ Todos los datos completos.\n"
    else:
        cuerpo += "   ⏳ Aún no se ha iniciado el proceso de pedido.\n"

    cuerpo += "──────────────────────────────────────────────────────────\n"
    cuerpo +="💡 SIGUIENTE PASO RECOMENDADO:\n"
    cuerpo +="──────────────────────────────────────────────────────────\n"
    

    cuerpo += "   → Contactar al cliente para confirmar los detalles del pedido.\n"

    return cuerpo


def enviar_resumen(resumen):
    """
    Envía el resumen de una conversación por correo al administrador.
    Usa _construir_cuerpo_email que incluye la checklist al principio.
    """
    destinatarios = getattr(settings, "RESUMEN_EMAIL_DESTINATARIOS", [])
    if not destinatarios:
        logger.warning("RESUMEN_EMAIL_DESTINATARIOS vacío; no se envía el resumen %s", resumen.pk)
        return False

    conversacion = resumen.conversacion

    # Asunto con encoding UTF-8 correcto
    asunto = f"[Chatbot] Compra - Conversación Nº{conversacion.pk}"

    cuerpo = _construir_cuerpo_email(conversacion, resumen)

    try:
        email = EmailMessage(
            subject=asunto,
            body=cuerpo,
            from_email=settings.EMAIL_HOST_USER,
            to=destinatarios,
        )
        email.send(fail_silently=False)
        logger.info("Resumen %s enviado exitosamente a %s", resumen.pk, destinatarios)
        return True
    except Exception:
        logger.exception("Error al enviar el resumen %s", resumen.pk)
        return False