from django.shortcuts import render
from django.views.generic import ListView,TemplateView
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from chat.models import Mensaje, Conversacion
from .models import responder

class InicioView(TemplateView):
    template_name = 'core/inicio.html'

def build_chat_context(conversacion):
    context = {"conversacion" : conversacion}
    context["Content-Security-Policy"] = f"frame-ancestors {settings.DOMINIO_PERMITIDO}"
    return context

#View del chat
@method_decorator(xframe_options_exempt, name='dispatch')
class ChatWidgetView(ListView):
    model = Mensaje
    template_name = "core/chatbot.html"
    context_object_name = "mensajes"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.conversacion = Conversacion.objects.create()
        Mensaje.objects.create(conversacion = self.conversacion, texto = "Hola, soy el asistente virtual de Dian Sistemas ¿que necesitas?", remitente = "chatbot")
        Mensaje.objects.create(conversacion = self.conversacion, texto = "Hola, soy un usuario", remitente = "usuario")

    #Filtros para el mensaje
    def get_queryset(self):
        return Mensaje.objects.filter(conversacion = self.conversacion).order_by("fecha_mensaje")

    # Contexto del chat
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_chat_context(self.conversacion))
        return context