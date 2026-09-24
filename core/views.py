import logging
from datetime import timedelta

from django.views.generic import ListView,TemplateView
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from chat.models import Mensaje, Conversacion
from .models import responder, guardar_respuesta_bot
from .mixins import DominioPermitidoMixin
from django.http import JsonResponse
from django.utils import timezone

logger = logging.getLogger(__name__)

# Tiempo que estamos esperando a que el llm generare una respuesta
# En segundos
TIMEOUT_RESPUESTA_BOT = 300

class InicioView(TemplateView):
    template_name = 'core/inicio.html'

class PruebaView(TemplateView):
    template_name = 'core/subdominio.html'

#View del chat (Listview de mensajes con el decorador de que tiene permitido enbeberse en un iframe)
#Además dispone de un Mixin para comprobar si esta dentro de los dominios permitidos antes de mostrar
@method_decorator(xframe_options_exempt, name='dispatch')
class ChatWidgetView(DominioPermitidoMixin, ListView):
    model = Mensaje
    template_name = "core/chatbot.html"
    context_object_name = "mensajes"

    #Método que se lanza al iniciar la vista.
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        #Si se llega a esta vista por el método POST filtra por el token de la sesión para recuperar la conversación que había.
        if request.method == "POST":
            token = request.POST.get("conversacion")
            self.conversacion = Conversacion.objects.filter(token=token).first() if token else None
            return
  
        token_recibido = request.GET.get("conversacion")
        self.conversacion = None
        if token_recibido:
            self.conversacion = Conversacion.objects.filter(token=token_recibido, estado="abierta").first()

# Comprobamos si estamos esperando a que el bot responde
# Si se pasa del tiempo, mensaje de error
    def _esperando_bot(self):
        if self.conversacion is None:
            return False

        ultimo = self.conversacion.conversacion_mensajes.order_by('-pk').first()
        if ultimo is None or ultimo.remitente != "usuario":
            return False

        limite = timezone.now() - timedelta(seconds=TIMEOUT_RESPUESTA_BOT)
        if ultimo.fecha_mensaje < limite:
            guardar_respuesta_bot(ultimo, "Ha habido un error")
            return False

        return True

    #Método que se encarga del filtro de objetos que aparecen en la vista
    def get_queryset(self):
        #Filtra que los mensajes sean todos de la conversación adecuada y los ordena por la fecha
        if self.conversacion is None:
            return Mensaje.objects.none()
        return Mensaje.objects.filter(conversacion=self.conversacion).order_by("fecha_mensaje")

    #Método para añadir contexto adicional al template
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        #En este caso le pasamos la conversación
        context["conversacion"] = self.conversacion
        #Si el bot está respondiendo, el template bloquea el formulario y muestra el "escribiendo"
        context["esperando_bot"] = self._esperando_bot()
        #Id del último mensaje para Ajax, si no hay conversacion nadaa
        if self.conversacion:
            ultimo = self.conversacion.conversacion_mensajes.order_by('-pk').first()
            context["ultimo_mensaje_id"] = ultimo.pk
        else:
            context["ultimo_mensaje_id"] = 0
        return context

    #Método que procesa los datos recibidos por la template.
    def post(self, request, *args, **kwargs):
        #Recogemos la acción del template
        accion = request.POST.get("accion")

        #Si la acción es el usuario, comprueba que input de texto no este vacío
        #Ademas si es el primer mensaje de la conversación general el mensaje de bienvenida del bot
        #Y finalmente crea el mensaje en funcion al texto escrito en el input y reenvia esos datos al template como json.
        #Si el bot aún no ha respondido al mensaje anterior se rechaza (409).
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
            else:
                #Bloqueamos la fila de la conversación para que dos peticiones simultáneas
                with transaction.atomic():
                    Conversacion.objects.select_for_update().get(pk=self.conversacion.pk)
                    if self._esperando_bot():
                        return JsonResponse(
                            {"error": "El asistente todavía está respondiendo", "esperando": True},
                            status=409,
                        )
                    mensaje_usuario = Mensaje.objects.create(
                        conversacion=self.conversacion, texto=texto, remitente="usuario"
                    )

            return JsonResponse({
                "mensaje_id": mensaje_usuario.pk,
                "conversacion": str(self.conversacion.token),
                "hora_usuario": timezone.localtime(mensaje_usuario.fecha_mensaje).strftime("%H:%M"),
                "bienvenida": bienvenida,
            })

        #Si la acción es la del bot comprueba primero si la conversación ya existe
        #Encuentra el mensaje del usuario que debe responder y llama al metodo responder con el mensaje del usuario como parámetro.
        #Finalmente se envia a la template el dato del mensaje con la hora de creación del mismo.
        elif accion == "bot":
            if self.conversacion is None:
                return JsonResponse({"error": "Conversación no encontrada"}, status=400)

            try:
                mensaje_usuario = Mensaje.objects.get(
                    pk=request.POST.get("mensaje_id"),
                    conversacion=self.conversacion,
                    remitente="usuario",
                )
            except (Mensaje.DoesNotExist, ValueError):
                return JsonResponse({"error": "Mensaje no encontrado"}, status=404)

            #Solo se responde al último mensaje y si todavía no tiene respuesta
            ultimo = self.conversacion.conversacion_mensajes.order_by('-pk').first()
            if ultimo.pk != mensaje_usuario.pk:
                return JsonResponse({"error": "Este mensaje ya tiene respuesta"}, status=409)

            #Si algo falla al generar la respuesta guardamos igualmente un mensaje de error del bot,
            #así el mensaje del usuario nunca se queda sin respuesta.
            try:
                mensaje_bot = responder(mensaje_usuario)
            except Exception:
                logger.exception("Error generando la respuesta del bot")
                mensaje_bot = guardar_respuesta_bot(mensaje_usuario, "Hemos tenido un error")

            return JsonResponse({
                "mensaje_id": mensaje_bot.pk,
                "bot": mensaje_bot.texto,
                "hora_bot": timezone.localtime(mensaje_bot.fecha_mensaje).strftime("%H:%M"),
            })

        # Comprobamos si ha recargado la pagina durante la conversacion del bot
        # Si lo hace, tratamos el error
        elif accion == "estado":
            if self.conversacion is None:
                return JsonResponse({"error": "Conversación no encontrada"}, status=400)

            esperando = self._esperando_bot()

            try:
                desde_id = int(request.POST.get("desde_id") or 0)
            except ValueError:
                desde_id = 0

            nuevos = self.conversacion.conversacion_mensajes.filter(
                pk__gt=desde_id, remitente="chatbot"
            ).order_by("pk")

            return JsonResponse({
                "esperando": esperando,
                "mensajes": [
                    {
                        "id": m.pk,
                        "texto": m.texto,
                        "hora": timezone.localtime(m.fecha_mensaje).strftime("%H:%M"),
                    }
                    for m in nuevos
                ],
            })

        #Esto ocurre cuando la acción no es ni usuario ni bot ni estado.
        return JsonResponse({"error": "Acción no válida"}, status=400)