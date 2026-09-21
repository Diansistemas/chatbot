import uuid

from django.db import models
from django.utils import timezone
from datetime import timedelta

# Cada conversacion
class Conversacion(models.Model):

    # Token de sesión
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

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

    # Si es una conversacion activa o no
    estado = models.CharField(max_length=20, choices=estado_choices, default='abierta')

    # A que dominio pertenece
    # Dependiendo de como lidiemos con varios dominios y su entrenamiento puede resultar irrelevante
    dominio = models.CharField(max_length=100, blank=True, default="")

    # Tipo de conversacion
    # Auto clasificado por el chatbot
    # Si el chatbot se queda en sin clasificar
    tipo_choices = [
        ("sin_clasificar", "Sin clasificar"),
        ("compra", "Compra"),
        ("consulta_tecnica", "Consulta técnica")
    ]
    tipo  = models.CharField(max_length=20, choices=tipo_choices, default="sin_clasificar")

    # Comprobamos que esta inactiva
    # El timeout esta en minutos
    def estaInactiva(self, timeout=30):
        # Pillamos el mensaje mas reciente
        ultimo_mensaje = self.conversacion_mensajes.order_by('-fecha_mensaje').first()

        # Calcmalos cuando estaria la conversacion en tiemout
        tiempo_limite = timezone.now() - timedelta(minutes=timeout)

        # Si ha pasado, devolvemos TRUE
        if ultimo_mensaje.fecha_mensaje < tiempo_limite:
            return True
        else:
            return False

    class Meta:
        verbose_name = "Conversacion"
        verbose_name_plural = "Conversaciones"

    def __str__(self):
        return f"Conversacion Nº{self.pk}"

# Mensajjes de cada conversacion
class Mensaje(models.Model):
    # Relacion con la conversacion
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name="conversacion_mensajes")

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

    class Meta:
        verbose_name = "Mensaje"
        verbose_name_plural = "Mensajes"

    def __str__(self):
        return f"{self.texto}"

# De momento no lo usmaos
# En principio existe solo para asegurarnos de que una compra tiene todos los datos necesarios
class Pedido(models.Model):

    # Relacion con la conversacion
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name="conversacion_pedido")

    # Datos minimos de un pedido
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=100)
    # Quizas un textField en vez de una foreignkey 
    #servicio = models.ForeignKey(Servicio)
    # Presupuesto?
    # Metodo de contacto?

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def checkCampos(self):
        mensaje = ""
        if not self.nombre:
            mensaje = mensaje + "Falta nombre \n"

        if not self.direccion:
            mensaje = mensaje + "Falta dirección \n"

        if mensaje == "":
            return True

        else:
            return (False,mensaje)