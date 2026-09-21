from django.shortcuts import render
from django.views.generic import ListView,TemplateView
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator
from chat.models import Mensaje, Conversacion
from .models import responder
from .mixins import DominioPermitidoMixin
from django.http import JsonResponse
from django.utils import timezone

class InicioView(TemplateView):
    template_name = 'core/inicio.html'

class PruebaView(TemplateView):
    template_name = 'core/subdominio.html'

#View del chat
@method_decorator(xframe_options_exempt, name='dispatch')
class ChatWidgetView(DominioPermitidoMixin, ListView):
    model = Mensaje
    template_name = "core/chatbot.html"
    context_object_name = "mensajes"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        if request.method == "POST":
            self.conversacion = Conversacion.objects.get(token=request.POST.get("conversacion"))
            return
  
        token_recibido = request.GET.get("conversacion")
        conversacion = None
        if token_recibido:
            conversacion = Conversacion.objects.filter(token=token_recibido, estado="abierta").first()

        if conversacion:
            self.conversacion = conversacion
        else:
            self.conversacion = Conversacion.objects.create()
            Mensaje.objects.create(
                conversacion=self.conversacion,
                texto="Hola, soy el asistente virtual de Dian Sistemas ¿que necesitas?",
                remitente="chatbot",
            )

    #Filtros para el mensaje
    def get_queryset(self):
        return Mensaje.objects.filter(conversacion = self.conversacion).order_by("fecha_mensaje")

    # Contexto del chat
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["conversacion"] = self.conversacion
        return context

    def post(self, request, *args, **kwargs):
        accion = request.POST.get("accion")

        # PASO 1 — crea el mensaje del usuario y devuelve su hora al instante
        if accion == "usuario":
            texto = request.POST.get("texto", "").strip()
            if not texto:
                return JsonResponse({"error": "Mensaje vacío"}, status=400)

            mensaje_usuario = Mensaje.objects.create(
                conversacion=self.conversacion, texto=texto, remitente="usuario"
            )
            return JsonResponse({
                "mensaje_id": mensaje_usuario.pk,
                "hora_usuario": timezone.localtime(mensaje_usuario.fecha_mensaje).strftime("%H:%M"),
            })

        # PASO 2 — genera la respuesta del bot para ese mensaje
        elif accion == "bot":
            mensaje_id = request.POST.get("mensaje_id")
            mensaje_usuario = Mensaje.objects.get(pk=mensaje_id, conversacion=self.conversacion)
            mensaje_bot = responder(mensaje_usuario)  # se queda "pensando" lo que tarde el LLM

            return JsonResponse({
                "bot": mensaje_bot.texto,
                "hora_bot": timezone.localtime(mensaje_bot.fecha_mensaje).strftime("%H:%M"),
            })

        return JsonResponse({"error": "Acción no válida"}, status=400)