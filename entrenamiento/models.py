from django.db import models

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