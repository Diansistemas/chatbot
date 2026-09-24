from django.db import models, transaction

from chat.models import Mensaje, Conversacion, Servicio
from entrenamiento.models import Intencion, EtiquetaEntidad, EjemploNLP, SpanEntidad, Par_Mensaje_Respuesta
from .acceso import get_nlp, llamar_llm

import logging
logger = logging.getLogger(__name__)

#Analisis de cada mensaje
class Analisis(models.Model):

    # Que mensaje
    mensaje = models.OneToOneField(Mensaje, on_delete = models.CASCADE, related_name="mensaje_analisis")

    # Que intecion hemos detectado
    intencion = models.ForeignKey(Intencion, on_delete = models.SET_NULL, null=True, blank=True, related_name="intencion_analisis")

    # Cuanta confianza tenemos en que el analisis es correcto
    confianza  = models.FloatField(null=True, blank=True)

    # Como detectamos los servicios en el analisis.
    # Es mas para debuggear que para otra cosa.
    # Existe como pillar el objeto "real", no la instancia del servicio
    def detectar_servicio(self):

        entidad_servicio = self.analisis_entidad.filter(etiqueta__nombre="SERVICIO").first()
        if not entidad_servicio:
            return None
    
        return Servicio.objects.filter(nombre__icontains=entidad_servicio.texto_detectado).first()
    
    class Meta:
        verbose_name = "Analisis de Mensaje"
        verbose_name_plural = "Analisis de Mensajes"

    def __str__(self):
        return f"Analisis: {self.mensaje}"

# Entidades y etiquetas detectadas en el analsis
class EntidadDetectada(models.Model):

    # A que analisis pertenece
    analisis = models.ForeignKey(Analisis, on_delete=models.CASCADE, related_name="analisis_entidad")

    # Que etiqueta hemos detectado
    etiqueta = models.ForeignKey(EtiquetaEntidad, on_delete=models.PROTECT, related_name="etiqueta_entidad")

    # Que texto tiene esta etiqueta
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

# Creamos los pares desde una conversacion
# Lo mantenemos en core porque es funcionalidad interna del chatbot para comunicar conversacion y entrenamiento
def generar_pares_desde_conversacion(conversacion):
    mensajes = list(conversacion.conversacion_mensajes.order_by("fecha_mensaje"))

    # Ignoramos el mensaje de introducción (hardcodeado, siempre el primero)
    mensajes = mensajes[1:]

    # Por si acaso el analisis ha fallado y no tenemos una intencion
    intencion_otro = Intencion.objects.get(nombre="otro")

    # Que par de mensaje
    pares = []
    for i in range(0, len(mensajes), 2):
        mensaje_usuario = mensajes[i]
        mensaje_chatbot = mensajes[i + 1]

        analisis = getattr(mensaje_usuario, "mensaje_analisis", None)
        intencion = analisis.intencion if (analisis and analisis.intencion) else intencion_otro

        pares.append(Par_Mensaje_Respuesta(
            intencion=intencion,
            mensaje_usuario=mensaje_usuario,
            texto_usuario=mensaje_usuario.texto,
            mensaje_chatbot=mensaje_chatbot,
            texto_chatbot=mensaje_chatbot.texto,
        ))

    return Par_Mensaje_Respuesta.objects.bulk_create(pares)

# Cerramos una conversacion y guardamos los mensajes en pares
# Cambiamos el estado y poco mas
# TODO: Llamarla cuando una conversacione este inactiva
def cerrar_conversacion(conversacion):

    conversacion.estado = "cerrada"
    conversacion.fecha_fin = conversacion.conversacion_mensajes.order_by("-fecha_mensaje").first().fecha_mensaje
    conversacion.save()
    generar_pares_desde_conversacion(conversacion)

# Donde comprobamos que estamos cerrando una conversacion
# Solo lo llamamos si detectamos que el usuario quiere cerrar conversacion
# TODO: Confirmamos que quiere cerrar y si detecta que si, cerramos
# TODO: Logica interna del chatbot para cerrar conversaciones
def confirmamos_cierre(conversacion):
    cerrar_conversacion(conversacion)

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
        intencion = Intencion.objects.filter(nombre=nombre_intencion, activa=True).first()
        if intencion is None:
            logger.warning("Intención '%s' no existe o no está activa. Pipeline: %s",
                           nombre_intencion, nlp.pipe_names)
    else:
        logger.warning("doc.cats vacío. Pipeline cargado: %s", nlp.pipe_names)

    # Si no hemos podido detectar nada, usamos "otro"
    if intencion is None:
        intencion = Intencion.objects.filter(nombre="otro").first()

    analisis = Analisis.objects.create(mensaje=mensaje_recibido, intencion=intencion, confianza=confianza)

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

# Como "respondemos", en concreto lo combinamos con acceso para decidir a que instancia del llm llamamos
def generar_respuesta_llm(mensaje, analisis, servicio): 

    # A que conversacion estamos respondiendo
    conversacion = mensaje.conversacion

    # De que estamos hablando
    if analisis.intencion:    
        intencion = analisis.intencion.nombre

    # Si no sabemos, vamos a un modelo generico
    else:
        intencion = "otro"

    # De que servicio estamos hablando
    contexto = str(servicio)

    # Generamos el historico excluyendo el mensaje que genera la respuesta
    historico = [
        {"role": "user" if mensaje.remitente == "usuario" else "assistant", "content": mensaje.texto}
        for mensaje in conversacion.conversacion_mensajes.exclude(pk=mensaje.pk).order_by("fecha_mensaje")
    ]

    # Llamamos al modelo
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
    analisis = procesar_mensaje(mensaje)
    nombre = analisis.intencion.nombre if analisis.intencion.nombre else "otro"

    if nombre == "compra":
        mensaje.conversacion.tenemosCompra = True
        mensaje.conversacion.save(update_fields=["tenemosCompra"])

    elif nombre == "cerrar":
        respuesta = guardar_respuesta_bot(mensaje, "¡Gracias por contactar con nosotros! Hasta pronto.")
        confirmamos_cierre(mensaje.conversacion)   # cerramos DESPUÉS de guardar la respuesta
        return respuesta

    else:
        servicio = analisis.detectar_servicio()
        texto_respuesta = generar_respuesta_llm(mensaje, analisis, servicio) or "Ha habido un error"
        return guardar_respuesta_bot(mensaje, texto_respuesta)

# Promovemos nuestros mensajes a ejemplos
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

    # Guardamos los datos
    SpanEntidad.objects.bulk_create(spans)
    return ejemplo
