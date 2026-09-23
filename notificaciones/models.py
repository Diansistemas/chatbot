import logging

from django.db import models
from chat.models import Conversacion
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from chat.models import Mensaje
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
    
def enviar_resumen(resumen):
    destinatarios = getattr(settings, "RESUMEN_EMAIL_DESTINATARIOS", [])
    if not destinatarios:
        logger.warning("RESUMEN_EMAIL_DESTINATARIOS vacío; no se envía el resumen %s", resumen.pk)
        return False

    conversacion = resumen.conversacion
    asunto = f"[Chatbot] Nueva solicitud de compra - Conversación Nº{conversacion.pk}"
    cuerpo = (
        f"Conversación Nº{conversacion.pk}\n"
        f"Dominio: {conversacion.dominio or 'N/D'}\n"
        f"Inicio: {conversacion.fecha_inicio:%d/%m/%Y %H:%M}\n"
        f"Fin: {conversacion.fecha_fin:%d/%m/%Y %H:%M}\n\n"
        f"{resumen.texto}\n"
    )

    EmailMessage(subject=asunto, body=cuerpo, to=destinatarios).send(fail_silently=False)

    return True
