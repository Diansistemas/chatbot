from django.db import models
from chat.models import Mensaje
from entrenamiento.models import Intencion, EtiquetaEntidad, detectar_servicio, EjemploNLP, SpanEntidad, generar_pares_desde_conversacion
from .acceso import get_nlp, llamar_llm

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

    inicio = models.PositiveSmallIntegerField()
    fin = models.PositiveSmallIntegerField()
    
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
        entidades.append(EntidadDetectada(
            analisis=analisis,
            etiqueta=etiqueta,
            texto_detectado=entidad.text,
            inicio=entidad.start_char,
            fin=entidad.end_char,
        ))

    EntidadDetectada.objects.bulk_create(entidades)

    return analisis

def generar_respuesta_llm(mensaje, analisis, servicio): 

    conversacion = mensaje.conversacion

    if analisis.intencion:    
        intencion = analisis.intencion.nombre

    else:
        intencion = "otro"

    contexto = str(servicio)

    # Generamos el historico excluyendo el mensaje que genera al respuesta
    historico = [
        {"role": "user" if mensaje.remitente == "usuario" else "assistant", "content": mensaje.texto}
        for mensaje in conversacion.conversacion_mensajes.exclude(pk=mensaje.pk).order_by("fecha_mensaje")
    ]

    texto = llamar_llm(intencion, mensaje.texto, historico, contexto)
    return texto.strip() 
    
# Funcion a llamar para generar una respuesta
def responder(mensaje):

    analisis = procesar_mensaje(mensaje)
    conversacion = mensaje.conversacion

    # Que servicio esta consultando
    servicio = detectar_servicio(analisis)

    # Generamos el texto
    texto_respuesta= generar_respuesta_llm(mensaje, analisis, servicio)

    # Si generar texto falla creamos un mensaje de error
    if not texto_respuesta:
        texto_respuesta="Ha habido un error, ¿puedes intentarlo de nuevo?"

    return Mensaje.objects.create(
        conversacion=conversacion,
        texto=texto_respuesta,
        remitente="chatbot"
    )

def promover_analisis_a_ejemplo(analisis, origen="chatbot"):
    ejemplo = EjemploNLP.objects.create(
        mensaje=analisis.mensaje,
        intencion=analisis.intencion,
        origen=origen,
    )  # texto se rellena solo en el save()

    spans = [
        SpanEntidad(
            ejemplo=ejemplo,
            etiqueta=entidad.etiqueta,
            inicio=entidad.inicio,
            fin=entidad.fin,
        )
        for entidad in analisis.analisis_entidad.all()
    ]
    SpanEntidad.objects.bulk_create(spans)
    return ejemplo

# Cerramos una conversacion y guardamos los mensajes en pares
def cerrar_conversacion(conversacion):

    conversacion.estado = "cerrada"
    conversacion.fecha_fin = conversacion.conversacion_mensajes.order_by("-fecha_mensaje").first().fecha_mensaje
    conversacion.save()
    generar_pares_desde_conversacion(conversacion)