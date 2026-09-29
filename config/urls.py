"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
import requests
import time


def health_check(request):
    """Endpoint de salud para healthchecks de Docker/monitoreo."""
    return JsonResponse({"status": "ok", "django": "6.1.1"})


def list_models(request):
    """Endpoint compatible con OpenAI: lista los modelos disponibles en Ollama."""
    try:
        resp = requests.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=5)
        resp.raise_for_status()
        ollama_models = resp.json().get("models", [])
    except Exception:
        ollama_models = []

    # Formato OpenAI: {"object": "list", "data": [{"id": ..., "object": "model", ...}]}
    data = []
    now = int(time.time())
    for m in ollama_models:
        data.append({
            "id": m.get("name", "unknown"),
            "object": "model",
            "created": now,
            "owned_by": "ollama",
        })

    return JsonResponse({"object": "list", "data": data})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("core.urls")),
    path('health', health_check, name='health'),
    path('v1/models', list_models, name='v1_models'),
]
