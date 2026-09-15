from django.db import models
from chat.models import Conversacion

class Resumen(models.Model):

    # Relacion con la conversacion
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name="resumenes")

    # Texto del resumen
    texto = models.TextField()

    # Tipo de resumen
    tipo_choices = [
        ("sin_categoria", "Sin categoría"),
        ("consulta_tecnica", "Consulta técnica"),
        ("compra", "Compra")
    ]

    tipo = models.CharField(max_length=20, choices=tipo_choices, default="sin_categoria")    
    
    # Traduccimos en español y comentario en la base de datos
    class Meta:
        verbose_name = "Resumen"
        verbose_name_plural = "Resúmenes"                                                                                                                                                                                                                                                                                                                                                 