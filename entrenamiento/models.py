from django.db import models
from chat.models import Mensaje

# Servicios que ofrece DianSistemas
class Servicio(models.Model):

    # Nombre del servicio 
    nombre = models.CharField(max_length=100)

    # Descripcion del servicio
    descripcion = models.TextField()

    # Coste aproximado del servicio
    # Coste maximo de 99999999.99
    coste = models.DecimalField(max_digits=10, decimal_places=2)

    # Tiempo de serivicio aproximado en dias
    tiempo_aproximado = models.SmallIntegerField()
    
    # Traduccimos en español y comentario en la base de datos
    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

    def __str__(self):
        return (f"Nombre: {self.nombre} \n Descripcion: {self.descripcion} \n Coste: {self.coste} \n Tiempo: {self.tiempo_aproximado}")

# Como detectamos los servicios en el analisis.
# Es mas para debuggear que para otra cosa.
# TODO: Cambiar el metodo  para que pille la informacion de la base de datos y los añada como EtiquetasEtnidad
def detectar_servicio(analisis):

    entidad_servicio = analisis.analisis_entidad.filter(etiqueta__nombre="SERVICIO").first()
    if not entidad_servicio:
        return None
    
    return Servicio.objects.filter(nombre__icontains=entidad_servicio.texto_detectado).first()

# Etiquetas para las entidades de entrenamiento de spaCy
class EtiquetaEntidad(models.Model):    
    # Nombre de la etiqueta
    nombre = models.CharField(max_length=50, unique=True)

    #Que representa la etiqueta
    desripcion = models.TextField(blank=True, null=True)

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

# Entrenamiento del LLM
# Pares de mensaje de usuario + respuesta del bot
# Dividimos las conversaciones para que el llm los entienda mejor
class Par_Mensaje_Respuesta(models.Model):

    intencion = models.ForeignKey(Intencion, on_delete=models.PROTECT, related_name="intencion_par_mensaje_respuesta")

    mensaje_usuario = models.ForeignKey(Mensaje, on_delete=models.SET_NULL, null=True, related_name="mensaje_usuario_par_mensaje_resupuesta")
    texto_usuario = models.TextField(null=True, blank=True)
    mensaje_chatbot = models.ForeignKey(Mensaje, on_delete=models.SET_NULL, null=True, related_name="mensaje_chatbot_par_mensaje_resupuesta")
    texto_chatbot = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Par de Entranamiento"
        verbose_name_plural = "Pares de Entrenamiento"

    def save(self, *args, **kwargs):

        self.texto_usuario = self.mensaje_usuario.texto
        self.texto_chatbot = self.mensaje_chatbot.texto

        super().save(*args, **kwargs)

# Pares que queremos usar en nuestro Modelfile
class EjemploLLM(models.Model):

    # La conversacion 
    conversacion = models.ForeignKey(Par_Mensaje_Respuesta, on_delete=models.PROTECT)

    # El origen de la conversacion
    # Manual: Creada manualmente, ya sea desde administracion o con el chatbot
    # Chatbot: Conversacin del chatbot que vamos a usar de ejemplo
    origen_choices = [
        ("manual", "Manual"),
        ("chatbot", "Chatbot")
    ]

    origen = models.CharField(max_length=20, choices = origen_choices, default="chatbot")

    class Meta:
        verbose_name = "Ejemplo"
        verbose_name_plural = "Ejemplos"

# NLP
#

class EjemploNLP(models.Model):

    mensaje = models.ForeignKey(Mensaje, on_delete=models.SET_NULL, null=True, related_name="mensaje_ejemploNLP")
    texto = models.TextField(null=True, blank=True)

    origen_choices = [
        ("manual", "Manual"),
        ("chatbot", "Chatbot")
    ]

    origen = models.CharField(max_length=20, choices = origen_choices, default="chatbot")

    class Meta:
        verbose_name = "Par de Entranamiento"
        verbose_name_plural = "Pares de Entrenamiento"

    def save(self, *args, **kwargs):

        self.texto = self.mensaje.texto

        super().save(*args, **kwargs)

# El span de las etiquetas que hay en un ejemplo para la NLP
# Formato de spaCy: offset de caracteres
class SpanEntidad(models.Model):

    ejemplo = models.ForeignKey(EjemploNLP, on_delete=models.CASCADE, related_name="ejemplo_spansEntidad")
    etiqueta = models.ForeignKey(EtiquetaEntidad, on_delete=models.PROTECT, related_name="etiqueta_spanEntidad")
    inicio = models.PositiveSmallIntegerField()
    fin = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "Entidad anotada"
        verbose_name_plural = "Entidades anotadas"
        constraints = [
            models.CheckConstraint(check=models.Q(fin__gt=models.F("inicio")), name="fin_mayor_que_inicio"),
        ]

    def texto_detectado(self):
        return self.ejemplo.texto[self.inicio:self.fin]

    def __str__(self):
        return f"{self.etiqueta.nombre}: {self.texto_detectado()}"