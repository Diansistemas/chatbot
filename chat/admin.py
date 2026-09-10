from django.contrib import admin
from .models import Conversacion, Mensajes

@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):

    search_fields = ("fecha_inicio", "fecha_fin", "estado", "tipo")
    list_filter = ("estado", "tipo")

@admin.register(Mensajes)
class MensajesAdmin(admin.ModelAdmin):

    search_fields = ("conversacion", "remitente")
    list_filter = ("conversacion")