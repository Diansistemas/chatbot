from django.contrib import admin, messages
from .models import Conversacion, Mensaje, Pedido, Servicio
from notificaciones.models import Resumen, generar_resumen

def generar_y_guardar_resumen(conversacion):
    if Resumen.objects.filter(conversacion=conversacion).exists():
        return

    texto = generar_resumen(conversacion)
    Resumen.objects.create(conversacion=conversacion, texto=texto)

@admin.action(description="Generar resumen")
def generar_resumen_action(modeladmin, request, queryset):
    for conversacion in queryset:
        generar_y_guardar_resumen(conversacion)
    
@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):

    search_fields = ("fecha_inicio", "estado")
    list_filter = ("estado", "tenemosCompra")
    list_display = ("__str__", "estado", "fecha_inicio", "tenemosCompra")
    ordering = ("-id",)
    actions = [generar_resumen_action]

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