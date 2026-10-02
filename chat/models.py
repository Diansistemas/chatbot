import uuid

from django.db import models
from django.utils import timezone
from datetime import timedelta


# Servicios que ofrece DianSistemas
class Servicio(models.Model):

    # Nombre del servicio 
    nombre = models.CharField(max_length=100, unique=True)

    # Descripcion del servicio
    descripcion = models.TextField()

    # Coste aproximado del servicio
    # Coste maximo de 99999999.99
    coste = models.DecimalField(max_digits=10, decimal_places=2)

    # Tiempo de serivicio aproximado en dias
    tiempo_aproximado = models.PositiveSmallIntegerField()
    
    # Traduccimos en español
    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

    def __str__(self):
        return (f"Nombre: {self.nombre} \n Descripcion: {self.descripcion} \n Coste: {self.coste} € \n Tiempo: {self.tiempo_aproximado}")

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
    dominio = models.CharField(max_length=100, blank=True, null=True, default="")

    # Tipo de conversacion
    # Auto clasificado por el chatbot
    tenemosCompra  = models.BooleanField(default=False)

    # Comprobamos que esta inactiva
    # El timeout esta en minutos
    def estaInactiva(self, timeout=30):
        # Pillamos el mensaje mas reciente
        ultimo_mensaje = self.conversacion_mensajes.order_by('-fecha_mensaje').first()

        # Sin mensajes no hay inactividad que calcular
        if ultimo_mensaje is None:
            return False

        # Calculamos cuando estaria la conversacion en timeout
        tiempo_limite = timezone.now() - timedelta(minutes=timeout)

        # Si ha pasado, devolvemos TRUE
        if ultimo_mensaje.fecha_mensaje < tiempo_limite:
            return True
        else:
            return False

    # Cerramos la conversacion (por inactividad o manualmente)
    def cerrar(self):
        # Si ya estaba cerrada no tocamos nada (no queremos pisar fecha_fin)
        if self.estado == "cerrada":
            return
        self.estado = "cerrada"
        self.fecha_fin = timezone.now()
        self.save(update_fields=["estado", "fecha_fin"])

    # Pescamos el ultimo mensaje
    # TODO: Deberiamos eliminar cada instancia de este metodo y sustituirlo por la linea
    def ultimoMensaje(self):
        return self.conversacion_mensajes.order_by('-pk').first()

    # Comprobamos si hemos respondido al usuario
    def esperandoRespuesta(self):
        ultimo = self.conversacion_mensajes.order_by('-pk').first()
        if ultimo is not None and ultimo.remitente == "usuario":
            return True
        else:
            return False

    # Transcripcion de una conversacion
    def transcripcion(self):
        lineas = []
        for m in self.conversacion_mensajes.order_by("fecha_mensaje"):
            remitente = "Cliente" if m.remitente == "usuario" else "Asistente"
            lineas.append(f"{remitente}: {m.texto}")
        return "\n".join(lineas)
        
    class Meta:
        verbose_name = "Conversacion"
        verbose_name_plural = "Conversaciones"

    def __str__(self):
        return f"Conversacion Nº{self.pk}"

# Mensajes de cada conversacion
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

# Pedidos hechos en una conversacion
# En principio existe solo para asegurarnos de que una compra tiene todos los datos necesarios
class Pedido(models.Model):

    # Relacion con la conversacion
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name="conversacion_pedido")

    # Datos minimos de un pedido
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=100)
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name= "servicio_pedido")
    presupuesto = models.DecimalField(max_digits=10, decimal_places=2)
    forma_contacto = models.CharField(max_length=100)

    # Comprobamos que tenemos los datos minimos para realizar un pedido
    def checkCampos(self):

        DATOS_MINIMOS = {
            "nombre": "Falta nombre",
            "direccion": "Falta dirección",
            "servicio": "Falta servicio",
            "presupuesto": "Falta presupuesto",
            "forma_contacto": "Falta un método de contacto",
        }

        mensaje = ""

        for campo, error in DATOS_MINIMOS.items():
            if not getattr(self, campo, None):
                mensaje = mensaje + error + "\n"

        if "método de contacto" not in mensaje:
            return (True,mensaje)
        else:
            return (False,mensaje)
        
    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self):
        return f"Pedido Nº{self.pk}"