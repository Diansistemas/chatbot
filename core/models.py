from django.db import models, transaction
from chat.models import Mensaje, Conversacion

from entrenamiento.models import Intencion, EtiquetaEntidad, EjemploNLP, SpanEntidad, generar_pares_desde_conversacion
from chat.models import detectar_servicio
from .acceso import get_nlp, llamar_llm


#Analisis de cada mensaje
class Analisis(models.Model):

    # Que mensaje
    mensaje = models.OneToOneField(Mensaje, on_delete = models.CASCADE, related_name="mensaje_analisis")
    # Que intecion hemos detectado
    intencion = models.ForeignKey(Intencion, on_delete = models.SET_NULL, null=True, blank=True, related_name="intencion_analisis")

    # Cuanta confianza tenemos en que el analisis es correcto
    confianza  = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Analisis de Mensaje"
        verbose_name_plural = "Analisis de Mensajes"

    def __str__(self):
        return f"Analisis: {self.mensaje}"

# Entidades y etiquetas detectadas en el analsis
class EntidadDetectada(models.Model):

    # Que analis
    analisis = models.ForeignKey(Analisis, on_delete=models.CASCADE, related_name="analisis_entidad")

    # Que etiqueta
    etiqueta = models.ForeignKey(EtiquetaEntidad, on_delete=models.PROTECT, related_name="etiqueta_entidad")

    # Que texto
    texto_detectado = models.TextField()

    # Donde empieza la etiqueta
    inicio = models.PositiveSmallIntegerField()

    # Donde acaba la etiqueta
    fin = models.PositiveSmallIntegerField()
    
    class Meta:
        verbose_name = "Entidad Detectada"
        verbose_name_plural = "Entidades Detectadas"

    def __str__(self):
        return f"Entidad {self.etiqueta.nombre}: {self.texto_detectado}"

# Procesa un mensaje que el chat bot acaba de recibir
def procesar_mensaje(mensaje_recibido):

    # Pillamos los modelos y el mensaje recibido
    nlp = get_nlp()
    doc = nlp(mensaje_recibido.texto)

    # Intencion y confianza 
    intencion = None
    confianza = None

    # spaCt doc para guardar los datos
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

# Como "respondemos", en concreto a que instancia del llm llamamos
def generar_respuesta_llm(mensaje, analisis, servicio): 

    # A que conversacion estamos respondiend
    conversacion = mensaje.conversacion

    # Que estamos tratando
    if analisis.intencion:    
        intencion = analisis.intencion.nombre

    # Si no sabemos, vamos a un modelo generico
    else:
        intencion = "otro"

    # De que servicio estamos hablando
    contexto = str(servicio)

    # Generamos el historico excluyendo el mensaje que genera al respuesta
    historico = [
        {"role": "user" if mensaje.remitente == "usuario" else "assistant", "content": mensaje.texto}
        for mensaje in conversacion.conversacion_mensajes.exclude(pk=mensaje.pk).order_by("fecha_mensaje")
    ]

    # Llamamos la modelo
    texto = llamar_llm(intencion, mensaje.texto, historico, contexto)
    return texto.strip() 

# Solo permitimos una respuesta por mensaje
def guardar_respuesta_bot(mensaje_usuario, texto):

    conversacion = mensaje_usuario.conversacion

    with transaction.atomic():
        Conversacion.objects.select_for_update().get(pk=conversacion.pk)

        ultimo = conversacion.ultimoMensaje()
        if ultimo.pk != mensaje_usuario.pk:
            return ultimo

        return Mensaje.objects.create(
            conversacion=conversacion,
            texto=texto,
            remitente="chatbot"
        )
    
# Funcion a llamar para generar una respuesta
def responder(mensaje):

    # Generemos el analisis del mensaje
    analisis = procesar_mensaje(mensaje)

    # Que servicio esta consultando
    servicio = detectar_servicio(analisis)

    # Generamos el texto
    texto_respuesta= generar_respuesta_llm(mensaje, analisis, servicio)

    # Si generar texto falla creamos un mensaje de error
    if not texto_respuesta:
        texto_respuesta = "Ha habido un error"

    return guardar_respuesta_bot(mensaje, texto_respuesta)

# Promovemos nuestros mensaje a ejemplos
def promover_analisis_a_ejemplo(analisis, origen="chatbot"):

    # El nuevo ejemplo
    ejemplo = EjemploNLP.objects.create(
        mensaje=analisis.mensaje,
        intencion=analisis.intencion,
        origen=origen,
    )

    # Las etiquetas
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