# -*- coding: utf-8 -*-
"""Sondea si 'cerrar' se dispara de forma sistematica con mensajes fuera de dominio."""
import os
import pathlib
import sys
import django

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # entrenamiento/evaluacion -> raiz
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.acceso import get_nlp

nlp = get_nlp()

PRUEBAS = [
    "Me han cobrado 150 euros de mas",
    "Me han cobrado dos veces la factura",
    "Quiero una devolucion del dinero",
    "Necesito la factura del mes pasado",
    "El precio ha subido demasiado",
    "Tu servicio es una porqueria",
    "Que pasa si cancelo el pedido",
    "Llueve mucho hoy en Madrid",
    "Me duele la cabeza",
    "Ponme musica",
]

for texto in PRUEBAS:
    doc = nlp(texto)
    top = sorted(doc.cats.items(), key=lambda kv: -kv[1])[:3]
    resumen = "  ".join(f"{k}={v:.2f}" for k, v in top)
    print(f"{texto!r}\n   {resumen}")
