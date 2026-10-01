# -*- coding: utf-8 -*-
"""Prueba de humo: carga el modelo nuevo por la via real (core.acceso.get_nlp)."""
import os
import pathlib
import sys
import django

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # entrenamiento/evaluacion -> raiz
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from core.acceso import get_nlp, etiqueta_modelo

ruta = pathlib.Path(settings.SPACY_MODEL_PATH)
print("modelo:", ruta)
print("modificado:", __import__("datetime").datetime.fromtimestamp(ruta.joinpath("meta.json").stat().st_mtime))

nlp = get_nlp()

PRUEBAS = [
    "Confirmo el presupuesto de 200 euros",
    "Quiero contratar el plan basico por 30 euros",
    "Pasame con un supervisor por favor",
    "Hasta luego que tengas buen dia",
    "Como limpio el virus del ordenador?",
    "Necesito ayuda con la factura",
    "Me han cobrado 150 euros de mas",
]

for texto in PRUEBAS:
    doc = nlp(texto)
    top = sorted(doc.cats.items(), key=lambda kv: -kv[1])
    ents = ", ".join(f"{e.label_}:{e.text}" for e in doc.ents) or "-"
    print(f"\n{texto!r}")
    print(f"   top: {top[0][0]} ({top[0][1]:.2f})  |  {top[1][0]} ({top[1][1]:.2f})")
    print(f"   ents: {ents}")
