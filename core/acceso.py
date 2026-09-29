import logging
import time

import spacy
import requests
import re

from django.conf import settings
from functools import lru_cache

logger = logging.getLogger(__name__)

# Esquema de los nombres 
_ESQUEMA_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")

# Mapeo intencion (nombre en BD) -> etiqueta del modelo en Ollama
# Es la UNICA fuente de verdad: lo usan llamar_llm (runtime) y
# generar_modelfiles (para crear los Modelfiles y los modelos).
# Las intenciones sin modelo propio (confirmar, cerrar, contactar con un
# humano...) caen a "otro".
MAPEO_INTENCION_MODELO = {
    "compra": "compra",
    "consulta_tecnica": "consulta",
    "confirmacion": "otro",
    "cerrar": "otro",
    "contactar_humano": "otro",
    "solicitar_agente": "otro",
    "otro": "otro",
}

# Etiqueta de modelo para una intencion de BD (default "otro")
def etiqueta_modelo(intencion):
    if not intencion:
        return "otro"
    return MAPEO_INTENCION_MODELO.get(intencion, "otro")
 
# Punto de aceso al modelo de spaCy
# Cacheado: sin cache se recargaba el modelo en CADA mensaje (6-15 s extra).
# Si reentrenamos en el mismo proceso, hay que limpiar: get_nlp.cache_clear()
@lru_cache(maxsize=1)
def get_nlp():

    # Miramos si tenemos modelo propio
    ruta_modelo = getattr(settings, "SPACY_MODEL_PATH", None)

    # Si lo tenemos, lo añadimos
    if ruta_modelo:
        logger.info("Cargando modelo spaCy propio: %s", ruta_modelo)
        nlp = spacy.load(ruta_modelo)
        logger.info("Modelo spaCy cargado (pipeline: %s)", nlp.pipe_names)
        return nlp

    # Si no, cargamos el base
    else:
        base_model = getattr(settings, "SPACY_MODEL_BASE", "es_core_news_sm")
        logger.warning("No hay modelo propio; usando el base: %s", base_model)
        return spacy.load(base_model)


# Como nombramos al modelo
# Recibe la ETIQUETA (compra/consulta/otro), no la intencion de BD
def nombre_modelo(etiqueta="otro", dominio=None):

    if dominio:
        return f"chatbot-{dominio}-{etiqueta}"

    else:
        return f"chatbot-{etiqueta}"
 

# Como llamamos al ollama
def _llamar_ollama_llm(modelo, mensajes):
    inicio = time.monotonic()
    try:
        resp = requests.post(
            f"{settings.OLLAMA_HOST}/api/chat",
            json={"model": modelo, "messages": mensajes, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        contenido = resp.json()["message"]["content"]
        logger.info(
            "OLLAMA OK modelo=%s tiempo=%.2fs chars=%d",
            modelo, time.monotonic() - inicio, len(contenido),
        )
        return contenido
    except requests.RequestException:
        logger.exception(
            "OLLAMA fallo modelo=%s tiempo=%.2fs",
            modelo, time.monotonic() - inicio,
        )
        raise
 
 
# Punto de acceso al llm llama
def llamar_llm(intencion, mensaje, historico, contexto, dominio=None):

    mensajes = historico + [{
        "role": "user",
        "content": f"{contexto}\n\n{mensaje}"
    }]

    # La intencion de BD se traduce a la etiqueta del modelo
    # (p.ej. "consulta_tecnica" -> "consulta"; antes se pedia
    # "chatbot-consulta_tecnica", que no existe en Ollama -> 404)
    etiqueta = etiqueta_modelo(intencion)
    logger.info(
        "LLM intencion=%s etiqueta=%s dominio=%s", intencion, etiqueta, dominio or "-"
    )

    # Candidatos en orden: modelo del dominio, generico, y "otro" como
    # ultimo recurso. Solo reintentamos cuando Ollama dice que el modelo
    # no existe (404); cualquier otro error (servidor caido, timeout...)
    # se propaga y se ve en el log.
    candidatos = []
    if dominio:
        candidatos.append(nombre_modelo(etiqueta, dominio))
    candidatos.append(nombre_modelo(etiqueta, None))
    if dominio and etiqueta != "otro":
        candidatos.append(nombre_modelo("otro", dominio))
    candidatos.append(nombre_modelo("otro", None))
    # Ultimo recurso: modelo base (heredado de la rama)
    candidatos.append("llama3.2")

    ultimo_error = None
    for modelo in dict.fromkeys(candidatos):
        try:
            return _llamar_ollama_llm(modelo, mensajes)
        except requests.HTTPError as error:
            respuesta = getattr(error, "response", None)
            if respuesta is None or respuesta.status_code != 404:
                raise
            ultimo_error = error

    raise ultimo_error

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
    inicio = time.monotonic()
    texto = _llamar_ollama_resumen(mensajes)
    logger.info("Resumen generado en %.2fs (%d chars)",
                time.monotonic() - inicio, len(texto))
    return texto.strip()
