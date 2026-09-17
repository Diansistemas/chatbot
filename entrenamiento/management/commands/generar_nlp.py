import random
from pathlib import Path

import spacy
from spacy.tokens import DocBin
from spacy.util import filter_spans
from django.conf import settings
from django.core.management.base import BaseCommand

from entrenamiento.models import EjemploNLP, Intencion

SPACY_DIR = Path(settings.BASE_DIR) / "entrenamiento" / "spacy"


class Command(BaseCommand):
    help = "Exporta EjemploEntrenamiento (texto + intencion + spans) a .spacy para textcat + ner"

    def handle(self, *args, **options):
        nlp = spacy.blank("es")

        etiquetas_intencion = list(Intencion.objects.filter(activa=True).values_list("nombre", flat=True))
        if not etiquetas_intencion:
            self.stderr.write(self.style.ERROR("No hay Intenciones activas en la BD."))
            return

        ejemplos = list(
            EjemploNLP.objects
            .select_related("intencion")
            .prefetch_related("spans__etiqueta")
        )
        random.shuffle(ejemplos)
        corte = int(len(ejemplos) * 0.8)

        for nombre_split, subset in [("train", ejemplos[:corte]), ("dev", ejemplos[corte:])]:
            db = DocBin()
            for ejemplo in subset:
                doc = nlp.make_doc(ejemplo.texto)

                # textcat: solo si el ejemplo tiene intencion asignada
                if ejemplo.intencion_id:
                    doc.cats = {
                        etq: 1.0 if etq == ejemplo.intencion.nombre else 0.0
                        for etq in etiquetas_intencion
                    }

                # ner: offsets de caracteres -> Span de spaCy
                spans = []
                for s in ejemplo.spans.all():
                    span = doc.char_span(s.inicio, s.fin, label=s.etiqueta.nombre, alignment_mode="contract")
                    if span is None:
                        self.stderr.write(self.style.WARNING(
                            f"Ejemplo #{ejemplo.id}: offsets ({s.inicio},{s.fin}) no alinean con ningun token, se ignora"
                        ))
                        continue
                    spans.append(span)

                doc.ents = filter_spans(spans)  # descarta solapamientos
                db.add(doc)

            db.to_disk(SPACY_DIR / f"{nombre_split}.spacy")
            self.stdout.write(self.style.SUCCESS(f"{nombre_split}.spacy: {len(subset)} ejemplos"))