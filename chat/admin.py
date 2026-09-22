from django.contrib import admin
from .models import Conversacion, Mensaje, Pedido, Servicio

@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):

    search_fields = ("fecha_inicio", "estado", "tipo")
    list_filter = ("estado", "tipo")
    list_display = ("__str__", "estado", "tipo", "fecha_inicio")
    ordering = ("-id",)

@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):

    search_fields = ("conversacion","texto", "remitente")
    list_filter = ("conversacion",)
    list_display = ("texto", "conversacion", "remitente", "fecha_mensaje")
    ordering = ("-conversacion", "fecha_mensaje")

@admin.register(Pedido)
class Pedido(admin.ModelAdmin):

    search_fields = ("nombre", "conversacion", "direccion")
    list_filter = ("conversacion",)

        
@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):

    search_fields = ("nombre", "descripcion")
    list_filter = ("coste", "tiempo_aproximado")
    list_display = ("nombre", "descripcion", "tiempo_aproximado", "coste")