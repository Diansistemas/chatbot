from django.db import models
from chat.models import Mensaje
from entrenamiento.models import Intencion, EtiquetaEntidad, Respuesta, Servicio
from .acceso import get_nlp, llamar_llm
from django.conf import settings
import random

#Analisis de cada mensaje
class Analisis(models.Model):

    mensaje = models.OneToOneField(Mensaje, on_delete = models.CASCADE, related_name="mensaje_analisis")
    intencion = models.ForeignKey(Intencion, on_delete = models.SET_NULL, null=True, blank=True, related_name="intencion_analisis")

    # Cuanta confianza tenemos en que el analisis es correcto
    confianza  = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Analisis de Mensaje"
        verbose_name_plural = "Analisis de Mensajes"


# Entidades y etiquetas detectadas en el analsis
class EntidadDetectada(models.Model):

    analisis = models.ForeignKey(Analisis, on_delete=models.CASCADE, related_name="analisis_entidad")

    etiqueta = models.ForeignKey(EtiquetaEntidad, on_delete=models.PROTECT, related_name="etiqueta_entidad")

    texto_detectado = models.TextField()
    
    class Meta:
        verbose_name = "Entidad Detectada"
        verbose_name_plural = "Entidades Detectadas"

# Procesa un mensaje que el chat bot acaba de recibir
def procesar_mensaje(mensaje_recibido):

    # Pillamos los modelos y el mensaje recibido
    nlp = get_nlp()
    doc = nlp(mensaje_recibido.texto)

    # Intencion y confianza 
    intencion = None
    confianza = None

    if doc.cats:
        nombre_intencion = max(doc.cats, key=doc.cats.get)
        confianza = doc.cats[nombre_intencion]
        intencion = Intencion.objects.filter(nombre = nombre_intencion, activa=True).first()

    # Creamos el analisis
    analisis = Analisis.objects.create(mensaje=mensaje_recibido, intencion=intencion, confianza=confianza)

    # Buscamos y creamos las entidades
    entidades = []
    for entidad in doc.ents:
        etiqueta, _ = EtiquetaEntidad.objects.get_or_create(nombre=entidad.label_)
        entidades.append(EntidadDetectada(analisis=analisis, etiqueta=etiqueta, texto_detectado=entidad.text))

    EntidadDetectada.objects.bulk_create(entidades)

    return analisis

# Respuestas predefinidas del nlm
def generar_respuesta_nlm(analisis):

    conversacion = analisis.mensaje.conversacion

    if not analisis.intencion:
        return"Lo siento, no te he entendido bien. ¿Puedes reformular tu mensaje?"
  
    else:
        respuestas = list(Respuesta.objects.filter(intencion=analisis.intencion))

        if not respuestas:
            return "No hay respuestas para tu consulta"

    plantilla =  random.choice(respuestas)

    return plantilla.texto


# Respuestas generadas del llm
from .acceso import get_nlp, llamar_llm

def generar_respuesta_llm(mensaje, analisis, servicio):
    conversacion = mensaje.conversacion
    intencion = analisis.intencion.nombre
    contexto = str(servicio)

    # Generamos el historico excluyendo el mensaje que genera al respuesta
    historico = [
        {"role": "user" if mensaje.remitente == "usuario" else "assistant", "content": mensaje.texto}
        for mensaje in conversacion.mensajes.exclude(pk=mensaje.pk).order_by("fecha_mensaje")
    ]

    try:
        texto = llamar_llm(intencion, mensaje.texto, historico, contexto)
        return texto.strip() or None
    except Exception:
        return None

# Funcion a llamar para generar una respuesta
def responder(mensaje):
    analisis = procesar_mensaje(mensaje)
    conversacion = analisis.mensaje.conversacion

    servicio = None

    # Generemos en el llm
    texto_respuesta = generar_respuesta_llm(mensaje, analisis, servicio)

    # Si falla, mensaje de error por defecto
    if not texto_respuesta:
        texto_respuesta = ""

    # 
    return Mensaje.objects.create(
        conversacion=conversacion,
        texto=texto_respuesta,
        remitente="chatbot"
    )
