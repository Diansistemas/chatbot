from functools import lru_cache
import spacy
from django.conf import settings

# Punto de aceso al modelo de spaCy, de momentos solo cargamos 1 modelo
# Si en algun momento cargamos mas de uno, hay que cambiar el max_size y cargarlos todos
@lru_cache(maxsize=1)
def get_nlp():

    # Miramos si tenemos modelo propio
    model_path = getattr(settings, "SPACY_MODEL_PATH", None)

    # Si lo tenemos, lo añadimos
    if model_path:
        return spacy.load(model_path)

    # Si no, cargamos el base
    else:
        base_model = getattr(settings, "SPACY_BASE_MODEL", "es_core_news_sm")
        return spacy.load(base_model)

