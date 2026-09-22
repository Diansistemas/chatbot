from django.db import models
from chat.models import Mensaje

# Etiquetas para las entidades de entrenamiento de spaCy
class EtiquetaEntidad(models.Model):    
    # Nombre de la etiqueta
    nombre = models.CharField(max_length=50, unique=True)

    #Que representa la etiqueta
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Etiqueta de Entidad"
        verbose_name_plural = "Etiquetas de Entidades"

# Intencion de una conversacion.
# Compra, Consulta u Otro. Admitimos mas valores en caso de que, en el futuro, queramos ampliar
class Intencion(models.Model): 
    # Nombre de la intencion
    nombre = models.CharField(max_length=50, unique=True)

    # En caso de que queramos añadir mas utilidad a futuro, esto nos deja distinguir claramente entre intenciones
    descripcion = models.TextField(blank=True, null=True)

    # Si el chatbot va a usar esta intencion
    activa = models.BooleanField(default=False)

    class Meta:
        verbose_name =  "Intencion"
        verbose_name_plural = "Intenciones"

    def __str__(self):
        return self.nombre

# Entrenamiento del LLM
# Pares de mensaje de usuario + respuesta del bot
# Dividimos las conversaciones para que el llm los entienda mejor
class Par_Mensaje_Respuesta(models.Model):

    # Que intencion hemos detectao
    intencion = models.ForeignKey(Intencion, on_delete=models.PROTECT, related_name="intencion_par_mensaje_respuesta")

    # El mensaje del usuario
    # Si borramos el mensaje, el texto sobrevive
    mensaje_usuario = models.ForeignKey(Mensaje, on_delete=models.SET_NULL, null=True, related_name="mensaje_usuario_par_mensaje_resupuesta")
    texto_usuario = models.TextField(null=True, blank=True)
    # El mensaje del chatbot
    # Si borramos el mensaje, el texto sobrevive
    mensaje_chatbot = models.ForeignKey(Mensaje, on_delete=models.SET_NULL, null=True, related_name="mensaje_chatbot_par_mensaje_resupuesta")
    texto_chatbot = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Par LLM"
        verbose_name_plural = "Pares LLM"

    def save(self, *args, **kwargs):

        if self.mensaje_usuario_id:
            self.texto_usuario = self.mensaje_usuario.texto
        if self.mensaje_chatbot_id:
            self.texto_chatbot = self.mensaje_chatbot.texto

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.texto_usuario} | {self.texto_chatbot}"

# Creamos los pares desde una conversacion  
def generar_pares_desde_conversacion(conversacion):
    mensajes = list(conversacion.conversacion_mensajes.order_by("fecha_mensaje"))

    # Ignoramos el mensaje de introducción (hardcodeado, siempre el primero)
    mensajes = mensajes[1:]

    # Por si acaso el analisis ha fallado y no tenemos una intencion
    intencion_otro = Intencion.objects.get(nombre="otro")

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

# Pares que queremos usar en nuestro Modelfile
class EjemploLLM(models.Model):

    # La conversacion 
    mensaje_respuesta = models.ForeignKey(Par_Mensaje_Respuesta, on_delete=models.PROTECT, related_name="mensaje_respuesta_ejemploLLM")

    # El origen de la conversacion
    # Manual: Creada manualmente, ya sea desde administracion o con el chatbot
    # Chatbot: Conversacin del chatbot que vamos a usar de ejemplo
    origen_choices = [
        ("manual", "Manual"),
        ("chatbot", "Chatbot")
    ]

    origen = models.CharField(max_length=20, choices = origen_choices, default="chatbot")

    class Meta:
        verbose_name = "Ejemplo LLM"
        verbose_name_plural = "Ejemplos LLM"

# NLP
# Sirve para la deteccion de intenciones en un mensaje
class EjemploNLP(models.Model):

    # Que mensaje
    mensaje = models.ForeignKey(Mensaje, on_delete=models.SET_NULL, null=True, related_name="mensaje_ejemploNLP")
    # Que intencion si la hay
    intencion = models.ForeignKey(Intencion, on_delete=models.PROTECT, null=True, blank=True, related_name="intencion_ejemploNLP")
    # Que texto
    texto = models.TextField(null=True, blank=True)

    # De donde viene
    origen_choices = [
        ("manual", "Manual"),
        ("chatbot", "Chatbot")
    ]

    origen = models.CharField(max_length=20, choices = origen_choices, default="chatbot")

    class Meta:
        verbose_name = "Ejemplo NLP"
        verbose_name_plural = "Ejemplos NLP"

    def save(self, *args, **kwargs):
        if self.mensaje:
            self.texto = self.mensaje.texto
            
        super().save(*args, **kwargs)

# El span de las etiquetas que hay en un ejemplo para la NLP
# Formato de spaCy: offset de caracteres
class SpanEntidad(models.Model):

    # A que ejemplo pertenece
    ejemplo = models.ForeignKey(EjemploNLP, on_delete=models.CASCADE, related_name="ejemplo_spansEntidad")
    # Que etiqueta
    etiqueta = models.ForeignKey(EtiquetaEntidad, on_delete=models.PROTECT, related_name="etiqueta_spanEntidad")
    # Donde empieza y donde acaba
    inicio = models.PositiveSmallIntegerField()
    fin = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "Entidad anotada"
        verbose_name_plural = "Entidades anotadas"
        # Nada de que el texto acabe antes de empezar
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__gt=models.F("inicio")), name="fin_mayor_que_inicio"),
        ]

    def texto_detectado(self):
        return self.ejemplo.texto[self.inicio:self.fin]

    def __str__(self):
        return f"{self.etiqueta.nombre}: {self.texto_detectado()}"

# Promovemos un par de mensajes a un ejemplo
def promover_par_a_ejemplo(par, origen="chatbot"):
    return EjemploLLM.objects.create(
        mensaje_respuesta=par,
        origen=origen,
    )