import spacy
import requests
import re

from django.conf import settings
from functools import lru_cache

# Esquema de los nombres 
_ESQUEMA_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")

# Intenciones de cada modelo
# Meter manualmente intenciones que consideremos oportunas con cada modelo
# TODO: Comprobar que solo lo llamamos para los modelos de llm y no para detectar intenciones reales
INTENCIONES_VALIDAS = {"compra", "consulta_tecnica", "otro"}

# Mapeo de intención NLP -> nombre de modelo Ollama
MODELO_POR_INTENCION = {
    "compra": "compra",
    "consulta_tecnica": "consulta",  # El modelo se llama "consulta"
    "otro": "otro",
}
 
# Punto de aceso al modelo de spaCy
# TODO: Limipiar cache antes de entrenar
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
    # Mapear intención NLP a nombre de modelo Ollama
    modelo_base = MODELO_POR_INTENCION.get(intencion, intencion)
    
    if dominio and intencion in INTENCIONES_VALIDAS:
        return f"chatbot-{dominio}-{modelo_base}"
    
    return f"chatbot-{modelo_base}"
 

# Como llamamos al ollama
def _llamar_ollama_llm(modelo, mensajes):
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

    # Intentos en orden: dominio específico -> genérico -> fallback "otro"
    intentos = []
    if dominio and intencion in INTENCIONES_VALIDAS:
        intentos.append(nombre_modelo(intencion, dominio))
    if intencion in INTENCIONES_VALIDAS:
        intentos.append(nombre_modelo(intencion, None))
    # Fallback final al modelo "otro" si la intención no tiene modelo dedicado
    if "otro" not in [m.split("-")[-1].split(":")[0] for m in intentos]:
        intentos.append(nombre_modelo("otro", None))
    # Último recurso: modelo base llama3.2
    intentos.append("llama3.2")

    for modelo in intentos:
        try:
            return _llamar_ollama_llm(modelo, mensajes)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                continue  # Modelo no existe, probar siguiente
            raise  # Otro error HTTP, relanzar
        except Exception:
            continue  # Timeout, connection error, etc. -> probar siguiente

    raise RuntimeError(f"Ningun modelo LLM disponible para intencion '{intencion}'")

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

# Como tratamos los resumenes

PROMPT_RESUMEN_COMPRA = (
    "Eres un asistente interno de DianSistemas. Vas a recibir la transcripción de una "
    "conversación entre un cliente y un chatbot de ventas. Redacta un resumen breve "
    "(máximo 120 palabras) en español para el equipo comercial, con este formato:\n"
    "- Servicio de interés:\n"
    "- Datos del cliente (nombre, contacto, dirección):\n"
    "- Requisitos, presupuesto o plazos mencionados:\n"
    "- Siguiente paso recomendado:\n"
    "Reglas: \n"
    "   -Usa SOLO información que aparezca en la conversación. Si un dato no aparece, escribe 'No indicado'. No inventes nada."
)

def _llamar_ollama_resumen(mensajes):
    resp = requests.post(
        f"{settings.OLLAMA_HOST}/api/chat",
        json={
            "model": getattr(settings, "OLLAMA_MODEL_RESUMEN", "llama3.2"),
            "messages": mensajes,
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]

def generar_resumen_llm(transcripcion):
    mensajes = [
        {"role": "system", "content": PROMPT_RESUMEN_COMPRA},
        {"role": "user", "content": transcripcion},
    ]
    texto = _llamar_ollama_resumen(mensajes)
    return texto.strip()
