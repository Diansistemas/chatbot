from django.conf import settings
from django.http import HttpResponseForbidden

class DominioPermitidoMixin:
    """Verifica el dominio y añade la cabecera CSP real al response."""

    def dispatch(self, request, *args, **kwargs):
        referer = request.META.get("HTTP_REFERER", "")
        if not referer.startswith(settings.DOMINIO_PERMITIDO):
            return HttpResponseForbidden("NO >:(")
        return super().dispatch(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        response["Content-Security-Policy"] = f"frame-ancestors {settings.DOMINIO_PERMITIDO}"
        return response