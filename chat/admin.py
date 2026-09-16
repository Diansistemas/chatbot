from django.contrib import admin
from .models import Conversacion, Mensaje, Pedido

@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):

    search_fields = ("fecha_inicio", "estado", "tipo")
    list_filter = ("estado", "tipo")

@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):

    search_fields = ("conversacion","texto", "remitente")
    list_filter = ("conversacion",)

@admin.register(Pedido)
class Pedido(admin.ModelAdmin):

    search_fields = ("nombre", "conversacion", "direccion")
    list_filter = ("conversacion",)