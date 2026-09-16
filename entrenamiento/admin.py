from django.contrib import admin
from .models import Servicio, EtiquetaEntidad, Intencion, Par_Mensaje_Respuesta, Ejemplo

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):

    search_fields = ("nombre", "descripcion", "coste", "tiempo_aproximado")

@admin.register(EtiquetaEntidad)
class EtiquetaEntidadAdmin(admin.ModelAdmin):

    search_fields = ("nombre", "descripcion")

@admin.register(Intencion)
class IntencionAdmin(admin.ModelAdmin):

    search_fields = ("nombre", "descripcion", "activa")
    list_filter = ("activa",)

@admin.register(Par_Mensaje_Respuesta)
class ParAdmin(admin.ModelAdmin):

    search_fields = ("intencion", "texto_usuario", "texto_chatbot")
    list_filter = ("intencion",)

@admin.register(Ejemplo)
class EjemploAdmin(admin.ModelAdmin):

    search_fields = ("conversacion", "origen")
    list_filter = ("origen",)