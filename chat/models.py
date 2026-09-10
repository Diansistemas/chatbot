from django.db import models

class Conversacion(models.Model):

    # Fechas de inicio y fin de la conversacion
    # Permite la busqueda y filtro  de conversacion por linea de tiempo
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank = True)

    # Estado de la conversacion
    # Creamos la conversacion en cuanto iniciamos un chat
    # Nos sirve para distinguir entre conversaciones en curso o terminadas
    estado_choices = [
        ("abierta", "Abierta"),
        ("cerrada", "Cerrada")
    ]

    estado = models.CharField(max_length=20, choices=estado_choices, default='abierta')

    # Tipo de conversacion
    # Auto clasificado por el chatbot
    # Si el chatbot se queda en sin clasificar
    tipo_choices = [
        ("sin_clasificar", "Sin clasificar"),
        ("compra", "Compra"),
        ("consulta_tecnica", "Consulta técnica")
    ]
    tipo  = models.CharField(max_length=20, choices=tipo_choices, default="sin_clasificar")

    # Traduccimos en español y comentario en la base de datos
    class Meta:
        db_table_comment = "Tabla que almacena las conversaciones entre el usuario y el chatbot"
        verbose_name = "Conversacion"
        verbose_name_plural = "Conversaciones"

class Mensajes(models.Model):
    # Relacion con la conversacion
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name="mensajes")

    # Texto del mensaje
    texto = models.TextField()

    # Quien manda el mensaje
    # Si es el usuario o el chatbot
    remitente_choices = [
        ("usuario", "Usuario"),
        ("chatbot", "Chatbot")
    ]
    remitente = models.CharField(max_length=20, choices=remitente_choices)

    # Cuadno se manda el mensaje
    # Nos permite recrear la conversacion
    fecha_mensaje = models.DateTimeField(auto_now_add=True)

    # Traduccimos en español y comentario en la base de datos
    class Meta:
        db_table_comment = "Tabla que almacena las mensajes de una conversacion"
        verbose_name = "Mensaje"
        verbose_name_plural = "Mensajes"