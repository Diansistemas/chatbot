from django.contrib import admin

from .models import Analisis, EntidadDetectada

@admin.register(Analisis)
class AnalisisAdmin(admin.ModelAdmin):

    search_fields = ("mensaje", "intencion")
    list_filter = ("intencion",)

@admin.register(EntidadDetectada)
class EntidadDetectadaAdmin(admin.ModelAdmin):

    search_fields = ("analisis", "etiqueta")
    list_filter = ("analisis", "etiqueta")
