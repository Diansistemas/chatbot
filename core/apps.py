import logging

from pathlib import Path

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)

# Django descubre este AppConfig porque core/apps.py define una unica subclase,
# aunque INSTALLED_APPS solo diga 'core'.
class CoreConfig(AppConfig):
    name = 'core'

    # ready() puede ejecutarse mas de una vez (repoblado del registry, tests):
    # el informe de arranque lo queremos ver UNA vez por proceso.
    _informado = False

    def ready(self):
        """Comprobaciones de configuracion al arrancar.

        Sin esto, un mal .env solo se descubria cuando un cliente enviaba el
        primer mensaje: el modelo seguia faltando tarde, y si OLLAMA_HOST no
        estaba la URL resultante era literalmente "None/api/chat".
        Aqui solo se comprueba y se loguea; NO se carga el modelo (costoso) ni
        se lanza excepcion, porque get_nlp() ya hace fallback al modelo base.
        """
        if CoreConfig._informado:
            return
        CoreConfig._informado = True

        base = getattr(settings, "SPACY_MODEL_BASE", "es_core_news_sm")
        ruta = getattr(settings, "SPACY_MODEL_PATH", None)

        if not ruta:
            logger.warning(
                "SPACY_MODEL_PATH sin definir; se usara el modelo spaCy base %s", base
            )
        elif not Path(ruta).exists():
            # entrenamiento/spacy/ esta en .gitignore: un clon limpio o un
            # despliegue sin reentrenar no trae el modelo.
            logger.error(
                "MODELO SPACY NO ENCONTRADO: %s. Falta entrenamiento/spacy/ (ignorada "
                "por git). El chat seguira funcionando pero con el modelo base %s, que "
                "NO conoce las intenciones propias. Generelo con `manage.py generar_nlp` "
                "y `python -m spacy train`, o copie la carpeta desde otro entorno.",
                ruta, base,
            )
        else:
            logger.info("Modelo spaCy propio disponible: %s", ruta)

        host = getattr(settings, "OLLAMA_HOST", "") or ""
        if not host:
            logger.error(
                "OLLAMA_HOST vacio: todas las llamadas al LLM fallaran y se caera "
                "al fallback de la cadena de candidatos."
            )
        elif not host.startswith(("http://", "https://")):
            logger.error(
                "OLLAMA_HOST no lleva esquema (http:// o https://): %r. La peticion a "
                "Ollama fallara en cada mensaje.",
                host,
            )
        else:
            logger.info("OLLAMA_HOST: %s", host)
