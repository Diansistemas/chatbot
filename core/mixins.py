from urllib.parse import urlparse
from django.conf import settings
from django.http import HttpResponseForbidden


class DominioPermitidoMixin:
    """Verifica el dominio (contra una lista de dominios permitidos) y añade la cabecera CSP real al response."""

    def dispatch(self, request, *args, **kwargs):
        referer = request.META.get("HTTP_REFERER", "")
        if not self._referer_permitido(referer):
            return HttpResponseForbidden("NO >:(")
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if not self._origen_permitido(request):
                return HttpResponseForbidden("NO >:(")
        return super().dispatch(request, *args, **kwargs)

    def _origen_permitido(self, request):
        # El header Origin acompana SIEMPRE a un POST (aunque el Referrer-Policy
        # oculte el Referer), asi que sirve de red de seguridad anti-CSRF cuando
        # la cookie CSRF no sobrevive en un iframe de terceros (widget embebido).
        origin = request.META.get("HTTP_ORIGIN", "")
        if not origin:
            # Sin Origin (clientes antiguos): seguimos protegidos por el Referer.
            return True
        origen = urlparse(origin)
        # El propio iframe del chat publica contra su mismo origen
        if origen.netloc == request.get_host():
            return True
        for dominio in settings.DOMINIOS_PERMITIDOS:
            permitido = urlparse(dominio)
            if origen.scheme == permitido.scheme and origen.netloc == permitido.netloc:
                return True
        return False

    def _referer_permitido(self, referer):
        #Sin Referer: es una visita directa (escribir la URL a mano no envia Referer).
        #La proteccion contra iframes de otros sitios la sigue dando la cabecera CSP
        #frame-ancestors que se monta en render_to_response.
        if not referer:
            return True
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