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
            token = request.POST.get("conversacion")
            self.conversacion = Conversacion.objects.filter(token=token).first() if token else None
            return

        token_recibido = request.GET.get("conversacion")
        self.conversacion = None
        if token_recibido:
            self.conversacion = Conversacion.objects.filter(token=token_recibido, estado="abierta").first()
        # Si no hay token válido, self.conversacion se queda en None — NO se crea nada todavía

    def get_queryset(self):
        if self.conversacion is None:
            return Mensaje.objects.none()
        return Mensaje.objects.filter(conversacion=self.conversacion).order_by("fecha_mensaje")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["conversacion"] = self.conversacion
        return context

    def post(self, request, *args, **kwargs):
        accion = request.POST.get("accion")

        if accion == "usuario":
            texto = request.POST.get("texto", "").strip()
            if not texto:
                return JsonResponse({"error": "Mensaje vacío"}, status=400)

            bienvenida = None
            if self.conversacion is None:
                self.conversacion = Conversacion.objects.create()
                mensaje_bienvenida = Mensaje.objects.create(
                    conversacion=self.conversacion,
                    texto="Hola, soy el asistente virtual de Dian Sistemas ¿que necesitas?",
                    remitente="chatbot",
                )
                bienvenida = {
                    "texto": mensaje_bienvenida.texto,
                    "hora": timezone.localtime(mensaje_bienvenida.fecha_mensaje).strftime("%H:%M"),
                }

            mensaje_usuario = Mensaje.objects.create(
                conversacion=self.conversacion, texto=texto, remitente="usuario"
            )
            return JsonResponse({
                "mensaje_id": mensaje_usuario.pk,
                "conversacion": str(self.conversacion.token),
                "hora_usuario": timezone.localtime(mensaje_usuario.fecha_mensaje).strftime("%H:%M"),
                "bienvenida": bienvenida,
            })

        elif accion == "bot":
            if self.conversacion is None:
                return JsonResponse({"error": "Conversación no encontrada"}, status=400)
            mensaje_id = request.POST.get("mensaje_id")
            mensaje_usuario = Mensaje.objects.get(pk=mensaje_id, conversacion=self.conversacion)
            mensaje_bot = responder(mensaje_usuario)
            return JsonResponse({
                "bot": mensaje_bot.texto,
                "hora_bot": timezone.localtime(mensaje_bot.fecha_mensaje).strftime("%H:%M"),
            })

        return JsonResponse({"error": "Acción no válida"}, status=400)