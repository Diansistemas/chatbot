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
        return context

    #Método que procesa los datos recibidos por la template.
    def post(self, request, *args, **kwargs):
        #Recogemos la acción del template
        accion = request.POST.get("accion")

        #Si la acción es el usuario, comprueba que input de texto no este vacío
        #Ademas si es el primer mensaje de la conversación general el mensaje de bienvenida del bot
        #Y finalmente crea el mensaje en funcion al texto escrito en el input y reenvia esos datos al template como json.
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

        #Si la acción es la del bot comprueba primero si la conversación ya existe
        #Encuentra el mensaje del usuario que debe responder y llama al metodo responder con el mensaje del usuario como parámetro.
        #Finalmente se envia a la template el dato del mensaje con la hora de creación del mismo.
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

        #Esto ocurre cuando la acción no es ni usuario ni bot.
        return JsonResponse({"error": "Acción no válida"}, status=400)