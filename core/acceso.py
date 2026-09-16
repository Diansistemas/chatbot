from functools import lru_cache
import spacy
from django.conf import settings
import requests

# Punto de aceso al modelo de spaCy, de momentos solo cargamos 1 modelo
# Si en algun momento cargamos mas de uno, hay que cambiar el max_size y cargarlos todos
@lru_cache(maxsize=1)
def get_nlp():

    # Miramos si tenemos modelo propio
    ruta_modelo = getattr(settings, "SPACY_MODEL_PATH", None)

    # Si lo tenemos, lo añadimos
    if ruta_modelo:
        return spacy.load(ruta_modelo)

    # Si no, cargamos el base
    else:
        base_model = getattr(settings, "SPACY_MODEL_BASE", "es_core_news_sm")
        return spacy.load(base_model)

# Que tipo de chat estamos usando
MAPA_MODELO = {
    "compra": "chatbot-compra",
    "consulta": "chatbot-consulta",
    "otro": "chatbot-otro",
}

# Punto de acceso a llama
def llamar_llm(intencion, mensaje, historico, contexto):
    modelo = MAPA_MODELO.get(intencion, MAPA_MODELO["otro"])
    mensajes = historico + [{
        "role": "user",
        "content": f"{contexto}\n\n{mensaje}"
    }]
    resp = requests.post(
        f"{settings.OLLAMA_HOST}/api/chat",
        json={"model": modelo, "messages": mensajes, "stream": False},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]