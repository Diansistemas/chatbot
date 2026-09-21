import logging

from django.db import models
from chat.models import Conversacion
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from chat.models import Mensaje
from core.acceso import generar_resumen_llm


logger = logging.getLogger(__name__)

# Resumen para mandar por correo
class Resumen(models.Model):

    # Relacion con la conversacion
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name="resumenes")

    # Texto del resumen
    texto = models.TextField()

    # Tipo de resumen
    tipo_choices = [
        ("sin_categoria", "Sin categoría"),
        ("consulta_tecnica", "Consulta técnica"),
        ("compra", "Compra")
    ]

    tipo = models.CharField(max_length=20, choices=tipo_choices, default="sin_categoria")    
    
    # Traduccimos en español y comentario en la base de datos
    class Meta:
        verbose_name = "Resumen"
        verbose_name_plural = "Resúmenes"                                                                                                                                                                                                                                                                                                                                                 

def transcripcion(conversacion):
    lineas = []
    for m in conversacion.conversacion_mensajes.order_by("fecha_mensaje"):
        quien = "Cliente" if m.remitente == "usuario" else "Asistente"
        lineas.append(f"{quien}: {m.texto}")
    return "\n".join(lineas)


def generar_resumen(conversacion):
    transcripcion = transcripcion(conversacion)
    try:
        texto = generar_resumen_llm(transcripcion)
    except Exception:
        logger.exception("Fallo al generar el resumen de la conversación %s", conversacion.pk)
        texto = ""

    # If the LLM fails, we still send the transcript so the lead isn't lost
    if not texto:
        texto = "(No se pudo generar el resumen automático. Transcripción completa:)\n\n" + transcripcion

    return Resumen.objects.create(conversacion=conversacion, texto=texto, tipo="compra")

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

    resumen.enviado = True
    resumen.fecha_envio = timezone.now()
    resumen.save(update_fields=["enviado", "fecha_envio"])
    return True
