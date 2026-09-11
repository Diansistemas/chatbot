from django.db import models
from chat.models import Mensaje
from entrenamiento.models import Intencion, EtiquetaEntidad
from .nlp import get_nlp

#Analisis de cada mensaje
class Analisis(models.Model):

    mensaje = models.OneToOneField(Mensaje, on_delete = models.CASCADE, related_name="mensaje_detectado")
    intencion = models.ForeignKey(Intencion, on_delete = models.SET_NULL, null=True, blank=True, related_name="intencion_detectada")

    # Cuanta confianza tenemos en que el analisis es correcto
    confianza  = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Analisis de Mensaje"
        verbose_name_plural = "Analisis de Mensajes"


# Entidades y etiquetas detectadas en el analsis
class EntidadDetectada(models.Model):

    analisis = models.ForeignKey(Analisis, on_delete=models.CASCADE, related_name="entidades")

    etiqueta = models.ForeignKey(EtiquetaEntidad, on_delete=models.PROTECT, related_name="etiquetas_detectadas")

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
    analisis = Analisis.objects.create(mensaje=mensaje_recibido, intecion=intencion, confianza=confianza)

    # Buscamos y creamos las entidades
    entidades = []
    for entidad in doc.ents():
        etiqueta = EtiquetaEntidad.objects.get_or_create(nombre=entidad.label_)
        entidades.append(EntidadDetectada(analisis=analisis, etiqueta=etiqueta, texto_detectado=entidad.text))

    EntidadDetectada.objects.bulk_create(entidades)

    return analisis

