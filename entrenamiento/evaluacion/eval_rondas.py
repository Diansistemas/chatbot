# -*- coding: utf-8 -*-
"""Compara en el mismo dev.spacy: modelo original (244), ronda 4 y ronda 5."""
import spacy
from spacy.tokens import DocBin
from spacy.training import Example
from spacy.scorer import Scorer

MODELOS = [
    ("ORIGINAL (244 ej, seed=0)",
     r"C:\Users\CEFYE\AppData\Local\Temp\opencode\backup_premerge\spacy_modelo_previo\model-best"),
    ("RONDA 4/5 (560 ej, seed=0)",
     r"C:\Users\CEFYE\AppData\Local\Temp\opencode\backup_premerge\spacy_modelo_ronda4\model-best"),
    ("RONDA 8 (585 ej, seed=0)",
     r"C:\Users\CEFYE\AppData\Local\Temp\opencode\backup_premerge\spacy_modelo_ronda8_585\model-best"),
    ("RONDA 9 (597 ej, seed=0)",
     r"C:\Users\CEFYE\chat\entrenamiento\spacy\modelo\model-best"),
]
DEV = r"C:\Users\CEFYE\chat\entrenamiento\spacy\dev.spacy"


def evaluar(ruta):
    nlp = spacy.load(ruta)
    db = DocBin().from_disk(DEV)
    docs = list(db.get_docs(nlp.vocab))
    examples = [Example(nlp(d.text), d) for d in docs]
    return Scorer(nlp).score(examples), len(docs)


for nombre, ruta in MODELOS:
    try:
        s, n = evaluar(ruta)
    except Exception as e:  # si la ronda 5 aun no existe
        print(f"\n=== {nombre} === (no disponible: {e})")
        continue
    print(f"\n=== {nombre} — dev={n} ===")
    print(f"  ents_f={s['ents_f']:.3f}  ents_p={s['ents_p']:.3f}  ents_r={s['ents_r']:.3f}")
    print(f"  cats_macro_f={s.get('cats_macro_f', 0):.3f}  cats_micro_f={s.get('cats_micro_f', 0):.3f}")
    por_tipo = s.get("cats_f_per_type") or {}
    if por_tipo:
        print("  F1 por intencion: " + ", ".join(
            f"{k}={(v['f'] if isinstance(v, dict) else v):.2f}" for k, v in sorted(por_tipo.items())))
    por_ent = s.get("ents_per_type") or {}
    if por_ent:
        print("  F1 por entidad:   " + ", ".join(
            f"{k}={(v['f'] if isinstance(v, dict) else v):.2f}" for k, v in sorted(por_ent.items())))
