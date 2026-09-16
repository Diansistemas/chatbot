from django.shortcuts import render
from django.views.generic import ListView,TemplateView
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator
from chat.models import Mensaje, Conversacion
from .models import responder
from .mixins import DominioPermitidoMixin
from django.http import JsonResponse

class InicioView(TemplateView):
    template_name = 'core/inicio.html'

#View del chat
@method_decorator(xframe_options_exempt, name='dispatch')
class ChatWidgetView(DominioPermitidoMixin, ListView):
    model = Mensaje
    template_name = "core/chatbot.html"
    context_object_name = "mensajes"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if request.method == "POST":
            self.conversacion = Conversacion.objects.get(pk=request.POST.get("conversacion"))
        else:
            self.conversacion = Conversacion.objects.create()
            Mensaje.objects.create(conversacion=self.conversacion, texto="Hola, soy el asistente virtual de Dian Sistemas ¿que necesitas?", remitente="chatbot")

    #Filtros para el mensaje
    def get_queryset(self):
        return Mensaje.objects.filter(conversacion = self.conversacion).order_by("fecha_mensaje")

    # Contexto del chat
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["conversacion"] = self.conversacion
        return context

    # NUEVO — atiende el POST del AJAX en la misma URL
    def post(self, request, *args, **kwargs):
        texto = request.POST.get("texto", "").strip()
        if not texto:
            return JsonResponse({"error": "Mensaje vacío"}, status=400)

        mensaje_usuario = Mensaje.objects.create(
            conversacion=self.conversacion, texto=texto, remitente="usuario"
        )
        mensaje_bot = responder(mensaje_usuario)  # se queda "pensando" lo que tarde el LLM

        return JsonResponse({"bot": mensaje_bot.texto})