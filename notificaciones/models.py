import logging

from django.db import models
from chat.models import Conversacion
from django.conf import settings
from django.core.mail import EmailMessage

from core.acceso import generar_resumen_llm


logger = logging.getLogger(__name__)


# Generamos el texto de un resumen
def generar_resumen(conversacion):
    texto_transcripcion = conversacion.transcripcion()
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
    texto = conversacion.transcripcion().lower()
    palabras_clave = [
        "compra", "presupuesto", "pedido", "servicio", "precio",
        "coste", "costo", "tarifa", "cuota", "reserva", "contratar",
        "cotización", "información sobre", "quiero", "necesito",
        "me gustaría", "disponible", "paquete"
    ]
    score = sum(1 for p in palabras_clave if p in texto)
    return score > 0


# Creamos el objeto resumen
def crear_resumen(conversacion):
    texto = generar_resumen(conversacion)
    return Resumen.objects.create(conversacion=conversacion, texto=texto)

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

    
    # Enviar el resumen por correo
    # Devuelve True si sae ha mandado bien
    def enviar_resumen(self):

        # A quien se lo mandamos
        destinatarios = getattr(settings, "RESUMEN_EMAIL_DESTINATARIOS", [])
        if not destinatarios:
            logger.warning("RESUMEN_EMAIL_DESTINATARIOS vacío; no se envía el resumen %s", self.pk)
            return False

        # Que mandamos
        conversacion = self.conversacion
        asunto = f"[Chatbot] Nueva solicitud de compra - Conversación Nº{conversacion.pk}"
        cuerpo = (
            f"Conversación Nº{conversacion.pk}\n"
            f"Dominio: {conversacion.dominio or 'N/D'}\n"
            f"Inicio: {conversacion.fecha_inicio:%d/%m/%Y %H:%M}\n"
            f"Fin: {conversacion.fecha_fin:%d/%m/%Y %H:%M}\n\n"
            f"{self.texto}\n"
        )

        # Mandamos el mensaje
        EmailMessage(subject=asunto, body=cuerpo, to=destinatarios).send(fail_silently=False)

        return True
    
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
