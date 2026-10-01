# -*- coding: utf-8 -*-
"""Analisis del entrenamiento ronda 5 (= ronda 4): curvas del log + metricas
detalladas + analisis de confianza de los fallos de dev."""
import re
import statistics
import django
import os
import sys

sys.path.insert(0, r"C:\Users\CEFYE\chat")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# ---------- 1. curvas desde el log de entrenamiento ----------
LOG = sys.argv[1] if len(sys.argv) > 1 else (
    r"C:\Users\CEFYE\.local\share\opencode\shell"
    r"\6a1d1cb21285b3801f39495f9a5ba387bca9fb8a\sh_0f17571380018B1UJvQ1MfMQl0.out")
filas = []
pat = re.compile(r"^\s*(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"
                 r"\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$")
for linea in open(LOG, encoding="utf-8", errors="ignore"):
    m = pat.match(linea)
    if m:
        v = [float(x) for x in m.groups()]
        filas.append(v)  # epoca, paso, l_t2v, l_ner, l_txt, entsF, entsP, entsR, cats, score

if filas:
    print("== CURVAS ==")
    print(f"evaluaciones: {len(filas)}  |  epocas: {int(filas[-1][0])}  |  pasos: {int(filas[-1][1])}")
    mejor = max(filas, key=lambda f: f[9])
    print(f"mejor SCORE: {mejor[9]:.2f} en paso {int(mejor[1])} (epoca {int(mejor[0])}): "
          f"ENTS_F={mejor[5]:.1f} CATS={mejor[8]:.1f}")
    pico_ents = max(filas, key=lambda f: f[5])
    pico_cats = max(filas, key=lambda f: f[8])
    print(f"pico ENTS_F: {pico_ents[5]:.1f} en paso {int(pico_ents[1])}  |  "
          f"pico CATS: {pico_cats[8]:.1f} en paso {int(pico_cats[1])}")
    txt0 = next((f for f in filas if f[4] < 0.01), None)
    ner20 = next((f for f in filas if f[3] < 20), None)
    if txt0: print(f"LOSS TEXTCAT < 0.01 desde paso {int(txt0[1])} (memoriza train)")
    if ner20: print(f"LOSS NER < 20 desde paso {int(ner20[1])}")
    mitad = len(filas) // 2
    print(f"ENTS_F media 1a mitad: {statistics.mean(f[5] for f in filas[:mitad]):.1f} | "
          f"2a mitad: {statistics.mean(f[5] for f in filas[mitad:]):.1f}")
    print(f"CATS media 1a mitad: {statistics.mean(f[8] for f in filas[:mitad]):.1f} | "
          f"2a mitad: {statistics.mean(f[8] for f in filas[mitad:]):.1f}")

# ---------- 2. metricas detalladas + confianza ----------
import spacy
from spacy.tokens import DocBin
from spacy.training import Example
from spacy.scorer import Scorer

nlp = spacy.load(r"C:\Users\CEFYE\chat\entrenamiento\spacy\modelo\model-best")
db = DocBin().from_disk(r"C:\Users\CEFYE\chat\entrenamiento\spacy\dev.spacy")
docs = list(db.get_docs(nlp.vocab))
examples = [Example(nlp(d.text), d) for d in docs]
s = Scorer(nlp).score(examples)

print("\n== TEXTCAT por clase (P / R / F) ==")
for k, v in sorted((s.get("cats_f_per_type") or {}).items()):
    if isinstance(v, dict):
        print(f"  {k:22} P={v.get('p', 0):.2f} R={v.get('r', 0):.2f} F={v.get('f', 0):.2f}")
    else:
        print(f"  {k:22} F={v:.2f}")

print("\n== NER por etiqueta (P / R / F) ==")
for k, v in sorted((s.get("ents_per_type") or {}).items()):
    print(f"  {k:24} P={v.get('p', 0):.2f} R={v.get('r', 0):.2f} F={v.get('f', 0):.2f}")

print("\n== CONFIANZA aciertos vs fallos ==")
aciertos, fallos = [], []
for d in docs:
    ref = max(d.cats, key=d.cats.get)
    pred = nlp(d.text)
    top = max(pred.cats, key=pred.cats.get)
    conf = pred.cats[top]
    (aciertos if top == ref else fallos).append((conf, ref, top, d.text))
print(f"aciertos: {len(aciertos)}  confianza media={statistics.mean(c[0] for c in aciertos):.2f} "
      f"mediana={statistics.median(c[0] for c in aciertos):.2f}")
if fallos:
    print(f"fallos:   {len(fallos)}  confianza media={statistics.mean(c[0] for c in fallos):.2f} "
          f"mediana={statistics.median(c[0] for c in fallos):.2f}")
    altos = [f for f in fallos if f[0] >= 0.90]
    print(f"fallos con confianza >= 0.90 (indetectables por umbral): {len(altos)}")
    print("\nFALLOS con su confianza:")
    for conf, ref, top, texto in sorted(fallos, key=lambda f: -f[0]):
        print(f"  [{conf:.2f}] {ref} -> {top}: {texto[:60]!r}")
