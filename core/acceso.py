import spacy
import requests
import re

from django.conf import settings
from functools import lru_cache

# Esquema de los nombres 
_ESQUEMA_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")

# Intenciones de cada modelo
INTENCIONES_VALIDAS = {"compra", "consulta", "otro"}
 
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


# Como nombramos al modelo
def nombre_modelo(intencion="otro", dominio=None):
 
    if dominio and intencion in INTENCIONES_VALIDAS:
        return f"chatbot-{dominio}-{intencion}"
 
    else:
        return f"chatbot-{intencion}"
 

# Como llamamos al ollama
def _llamar_ollama(modelo, mensajes):
    resp = requests.post(
        f"{settings.OLLAMA_HOST}/api/chat",
        json={"model": modelo, "messages": mensajes, "stream": False},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]
 
 
# Punto de acceso al llm llama
def llamar_llm(intencion, mensaje, historico, contexto, dominio=None):

    mensajes = historico + [{
        "role": "user",
        "content": f"{contexto}\n\n{mensaje}"
    }]
 
    modelo = nombre_modelo(intencion, dominio)
 
    try:
        return _llamar_ollama(modelo, mensajes)
    except requests.HTTPError:
        if not dominio:
            raise
        modelo_generico = nombre_modelo(intencion, None)
        return _llamar_ollama(modelo_generico, mensajes)

# Tratamiento de nombres del domino
def normalizar_dominio(host):
    
    if not host:
        return ""
 
    host = host.strip().lower()
    if host == "*":
        return ""

    # Quitamos "https://"
    host = _ESQUEMA_RE.sub("", host)
    #Quitamos cualquier subruta ("/algo")
    host = host.split("/")[0]

    # ALLOWED_HOSTS admite ".dominio.com" 
    if host.startswith("."):
        host = host[1:]
 
    # Quitamos el puerto
    if host.startswith("["):
        host = host.split("]")[0].lstrip("[")
    else:
        host = host.split(":")[0]
 
    if not host:
        return ""

    # Montamos el nombre real
    partes = host.split(".")
    if len(partes) >= 2:
        return partes[-2]
    return partes[0]
 

# Importar los nombres del ALLOWED HOST
def dominios_desde_settings(allowed_hosts):
    dominios = set()
    for host in allowed_hosts or []:
        base = normalizar_dominio(host)
        if base:
            dominios.add(base)
    return sorted(dominios)