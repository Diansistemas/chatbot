from django.contrib import admin

from .models import Analisis, EntidadDetectada
from .models import promover_analisis_a_ejemplo

@admin.action(description="Promover a EjemploNLP")
def promover_a_ejemplo_nlp(modeladmin, request, queryset):
    for analisis in queryset:
        promover_analisis_a_ejemplo(analisis, origen="chatbot")

@admin.register(Analisis)
class AnalisisAdmin(admin.ModelAdmin):

    search_fields = ("mensaje", "intencion")
    list_filter = ("intencion",)
    actions = [promover_a_ejemplo_nlp]
@admin.register(EntidadDetectada)
class EntidadDetectadaAdmin(admin.ModelAdmin):

    search_fields = ("analisis", "etiqueta")
    list_filter = ("analisis", "etiqueta")