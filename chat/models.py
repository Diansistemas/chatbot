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
    
    # Traduccimos en español y comentario en la base de datos
    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

    def __str__(self):
        return (f"Nombre: {self.nombre} \n Descripcion: {self.descripcion} \n Coste: {self.coste} \n Tiempo: {self.tiempo_aproximado}")

# Como detectamos los servicios en el analisis.
# Es mas para debuggear que para otra cosa.
# Existe como pillar el objeto "real", no la instancia del servicio
def detectar_servicio(analisis):

    entidad_servicio = analisis.analisis_entidad.filter(etiqueta__nombre="SERVICIO").first()
    if not entidad_servicio:
        return None
    
    return Servicio.objects.filter(nombre__icontains=entidad_servicio.texto_detectado).first()

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

        # Calculamos cuando estaria la conversacion en timeout
        tiempo_limite = timezone.now() - timedelta(minutes=timeout)
 
        # Si ha pasado, devolvemos TRUE
        if ultimo_mensaje.fecha_mensaje < tiempo_limite:
            return True
        else:
            return False

    def ultimoMensaje(self):
        return self.conversacion_mensajes.order_by('-pk').first()

    # Comprobamos si hemos respondido al usuario
    def esperandoRespuesta(self):
        ultimo = self.conversacion_mensajes.order_by('-pk').first()
        return ultimo is not None and ultimo.remitente == "usuario"
        
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
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name= "servicio_pedido")
    presupuesto = models.DecimalField(max_digits=10, decimal_places=2)
    forma_contacto = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    # Comprobamos que tenemos los dataos minimos para realizar un pedido
    def checkCampos(self):
        mensaje = ""
        if not self.nombre:
            mensaje = mensaje + "Falta nombre \n"

        if not self.direccion:
            mensaje = mensaje + "Falta dirección \n"

        if not self.servicio:
            mensaje = mensaje + "Falta servicio \n"

        if not self.presupuesto:
            mensaje = mensaje + "Falta presupuesto \n"

        if not self.forma_contacto:
            mensaje = mensaje + "Falta un metodo de contacto \n"

        if mensaje == "":
            return (True,mensaje)
        else:
            return (False,mensaje)

    def __str__(self):
        return f"Pedido Nº{self.pk}"