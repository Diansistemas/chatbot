from django.db import models
from chat.models import Conversacion

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

# Etiquetas para las entidades de entrenamiento de la IA
class EtiquetaEntidad(models.Model):    
    # Nombre de la etiqueta
    nombre = models.CharField(max_length=50, unique=True)

    #Que representa la etiqueta
    desripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Etiqueta de Entidad"
        verbose_name_plural = "Etiquetas de Entidades"

# Equivalente a labels, nos sirve para distinguir entre una consulta tecnica o una compra
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

# Ejemplos de conversaciones para entrenar al chatbot
class Ejemplo(models.Model):

    # La conversacion 
    conversacion = models.ForeignKey(Conversacion, on_delete=models.PROTECT)

    # El origen de la conversacion
    # Manual: Creada manualmente, ya sea desde administracion o con el chatbot
    # Chatbot: Conversacin del chatbot que vamos a usar de ejemplo
    origen_choices = [
        ("manual", "Manual"),
        ("chatbot", "Chatbot")
    ]

    origen = models.CharField(max_length=20, choices = origen_choices, default="chatbot")

    class Meta:
        verboses_name = "Ejemplo"
        verbose_name_plural = "Ejemplos"