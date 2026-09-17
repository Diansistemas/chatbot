from django.contrib import admin
from .models import Servicio, EtiquetaEntidad, Intencion, Par_Mensaje_Respuesta, EjemploLLM, EjemploNLP, SpanEntidad, promover_par_a_ejemplo

@admin.action(description="Promover a EjemploLLM")
def promover_a_ejemplo_llm(modeladmin, request, queryset):
    for par in queryset:
        promover_par_a_ejemplo(par, origen="chatbot")
        
@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):

    search_fields = ("nombre", "descripcion")
    list_filter = ("coste", "tiempo_aproximado")
    list_display = ("nombre", "descripcion", "tiempo_aproximado", "coste")

@admin.register(EtiquetaEntidad)
class EtiquetaEntidadAdmin(admin.ModelAdmin):

    search_fields = ("nombre", "descripcion")
    list_display = ("nombre", "descripcion")

@admin.register(Intencion)
class IntencionAdmin(admin.ModelAdmin):

    search_fields = ("nombre", "descripcion")
    list_filter = ("activa",)
    list_display = ("nombre", "descripcion", "activa")

@admin.register(Par_Mensaje_Respuesta)
class ParAdmin(admin.ModelAdmin):

    search_fields = ("texto_usuario", "texto_chatbot", "intencion")
    list_filter = ("intencion",)
    list_display = ("texto_usuario", "texto_chatbot", "intencion")
    actions = [promover_a_ejemplo_llm]

@admin.register(EjemploLLM)
class EjemploLLMAdmin(admin.ModelAdmin):

    search_fields = ("mensaje_respuesta", "origen")
    list_filter = ("origen",)
    list_display = ("mensaje_respuesta", "origen")

class SpanEntidadInline(admin.TabularInline):
    model = SpanEntidad
    extra = 1

@admin.register(EjemploNLP)
class EjemploNLPAdmin(admin.ModelAdmin):
    search_fields = ("texto", "intencion","origen")
    list_filter = ("intencion","origen",)
    list_display = ("texto", "intencion", "origen")
    inlines = [SpanEntidadInline]
