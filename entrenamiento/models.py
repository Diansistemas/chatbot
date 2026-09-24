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

    def __str__(self):
        return f"{self.nombre}"
    
# Intencion de una conversacion
# Compra, Consulta u Otro
# Las que nos interesan son Compra, Consulta y Otro para llamar al modelo
# El resto es utility para nuestras funciones
class Intencion(models.Model): 
    # Nombre de la intencion
    nombre = models.CharField(max_length=50, unique=True)

    # Que representa esta intencion
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
# Dividimos las conversaciones para que el llm lo entienda mejor
class Par_Mensaje_Respuesta(models.Model):

    # Que intencion hemos detectao
    intencion = models.ForeignKey(Intencion, on_delete=models.PROTECT, related_name="intencion_par_mensaje_respuesta")

    # El mensaje del usuario
    # Si borramos el mensaje, el texto sobrevive
    mensaje_usuario = models.OneToOneField(Mensaje, on_delete=models.SET_NULL, null=True, related_name="mensaje_usuario_par_mensaje_resupuesta", limit_choices_to={"remitente": "usuario"})
    texto_usuario = models.TextField(null=True, blank=True)
    # El mensaje del chatbot
    # Si borramos el mensaje, el texto sobrevive
    mensaje_chatbot = models.OneToOneField(Mensaje, on_delete=models.SET_NULL, null=True, related_name="mensaje_chatbot_par_mensaje_resupuesta", limit_choices_to={"remitente": "chatbot"})
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

# Pares que queremos usar en nuestro Modelfile
class EjemploLLM(models.Model):

    # El ejemplo y la respuesta 
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

    def __str__(self):
        return f"{self.mensaje_respuesta}"

# NLP
# Sirve para la deteccion de intenciones y entidades en un mensaje
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

    def __str__(self):
        return f"{self.texto}"

# El span de las etiquetas que hay en un ejemplo para la NLP
# Formato de spaCy: Necesita saber donde empieza y acaba la etiqueta
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