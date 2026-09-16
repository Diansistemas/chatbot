import random
from pathlib import Path

import spacy
from spacy.tokens import DocBin
from django.conf import settings
from django.core.management.base import BaseCommand

from entrenamiento.models import Par_Mensaje_Respuesta, Intencion

SPACY_DIR = Path(settings.BASE_DIR) / "entrenamiento" / "spacy"


class Command(BaseCommand):
    help = "Exporta Par_Mensaje_Respuesta a formato .spacy para entrenar textcat"

    def handle(self, *args, **options):
        nlp = spacy.blank("es")  # solo para el tokenizador, no carga pipeline

        etiquetas = list(Intencion.objects.values_list("nombre", flat=True))
        if not etiquetas:
            self.stderr.write(self.style.ERROR("No hay Intenciones en la BD."))
            return

        pares = list(Par_Mensaje_Respuesta.objects.select_related("intencion"))
        random.shuffle(pares)
        corte = int(len(pares) * 0.8)  # 80/20 train/dev

        for nombre_split, subset in [("train", pares[:corte]), ("dev", pares[corte:])]:
            db = DocBin()
            for par in subset:
                doc = nlp.make_doc(par.texto_usuario)
                doc.cats = {etq: 1.0 if etq == par.intencion.nombre else 0.0 for etq in etiquetas}
                db.add(doc)
            db.to_disk(SPACY_DIR / f"{nombre_split}.spacy")
            self.stdout.write(self.style.SUCCESS(f"{nombre_split}.spacy: {len(subset)} ejemplos"))