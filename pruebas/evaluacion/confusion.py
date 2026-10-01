# -*- coding: utf-8 -*-
"""Matriz de confusion de intenciones sobre dev.spacy con el modelo nuevo."""
import os
import sys
import collections
import django

import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # entrenamiento/evaluacion -> raiz
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import spacy
from spacy.tokens import DocBin
from django.conf import settings

nlp = spacy.load(settings.SPACY_MODEL_PATH)
db = DocBin().from_disk(r"C:\Users\CEFYE\chat\entrenamiento\spacy\dev.spacy")
docs = list(db.get_docs(nlp.vocab))

conf = collections.Counter()
fallos = []
for d in docs:
    ref = max(d.cats, key=d.cats.get)
    pred = nlp(d.text)
    top = max(pred.cats, key=pred.cats.get)
    conf[(ref, top)] += 1
    if ref != top:
        fallos.append((ref, top, d.text))

etiquetas = sorted({r for r, _ in conf} | {p for _, p in conf})
print("       " + "".join(f"{p[:9]:>10}" for p in etiquetas))
for r in etiquetas:
    fila = "".join(f"{conf.get((r, p), 0):>10}" for p in etiquetas)
    print(f"{r[:7]:>7}" + fila)

print(f"\nFallos: {len(fallos)}/{len(docs)}")
for ref, pred, texto in sorted(fallos):
    print(f"  [{ref} -> {pred}] {texto[:70]!r}")
