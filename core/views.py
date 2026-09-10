from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt
from django.conf import settings

def inicio(request):
    return render(
        request,
        "core/inicio.html",
    )

@xframe_options_exempt
def chat_widget_view(request):
    response = render(request, "core/chatbot.html")
    response["Content-Security-Policy"] = f"frame-ancestors {settings.DOMINIO_PERMITIDO}"
    return response