from urllib.parse import urlparse
from django.conf import settings
from django.http import HttpResponseForbidden


class DominioPermitidoMixin:
    """Verifica el dominio (contra una lista de dominios permitidos) y añade la cabecera CSP real al response."""

    def dispatch(self, request, *args, **kwargs):
        referer = request.META.get("HTTP_REFERER", "")
        if not self._referer_permitido(referer):
            return HttpResponseForbidden("NO >:(")
        return super().dispatch(request, *args, **kwargs)

    def _referer_permitido(self, referer):
        if not referer:
            return False
        referer_parsed = urlparse(referer)
        for dominio in settings.DOMINIOS_PERMITIDOS:
            permitido = urlparse(dominio)
            if referer_parsed.scheme == permitido.scheme and referer_parsed.netloc == permitido.netloc:
                return True
        return False

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        response["Content-Security-Policy"] = f"frame-ancestors {' '.join(settings.DOMINIOS_PERMITIDOS)}"
        return response