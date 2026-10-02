import hashlib
import spacy

from collections import Counter
from pathlib import Path
from spacy.tokens import DocBin
from spacy.util import filter_spans
from django.conf import settings
from django.core.management.base import BaseCommand

from entrenamiento.models import EjemploNLP, Intencion

# Donde vamos a guardar el nlp
SPACY_DIR = Path(settings.BASE_DIR) / "entrenamiento" / "spacy"


# Divide el texto para los ejemplos
# Siempre el mismo split
def es_dev(texto, ratio_dev):
    normalizado = " ".join(texto.lower().split())
    h = int(hashlib.sha1(normalizado.encode("utf-8")).hexdigest(), 16)
    return (h % 10_000) < ratio_dev * 10_000


# Crea el "doc" de spaCy
# Si solo tiene intent va a cat
# Si solo tiene entidades va a ent
class Command(BaseCommand):
    help = "Exporta EjemploNLP a .spacy: ejemplos de intencion -> textcat, de entidades -> ner"

    # Ajustar el dev ratio
    def add_arguments(self, parser):
        parser.add_argument("--dev-ratio", type=float, default=0.2)

    # El comando real
    def handle(self, *args, **options):
        nlp = spacy.blank("es")

        etiquetas_intencion = list(
            Intencion.objects.filter(activa=True).order_by("nombre")
            .values_list("nombre", flat=True)
        )
        if not etiquetas_intencion:
            self.stderr.write(self.style.ERROR("No hay Intenciones activas en la BD."))
            return

        ejemplos = (
            EjemploNLP.objects
            .exclude(texto__isnull=True).exclude(texto="")
            .select_related("intencion")
            .prefetch_related("ejemplo_spansEntidad__etiqueta")
            .order_by("id")
        )

        dbs = {"train": DocBin(), "dev": DocBin()}
        stats = {s: Counter() for s in dbs}

        for ejemplo in ejemplos:
            doc = nlp.make_doc(ejemplo.texto)

            # Si detecta intenciones va al textcat
            tiene_intencion = bool(ejemplo.intencion_id and ejemplo.intencion.activa)
            if tiene_intencion:
                doc.cats = {
                    etq: 1.0 if etq == ejemplo.intencion.nombre else 0.0
                    for etq in etiquetas_intencion
                }

            spans_bd = list(ejemplo.ejemplo_spansEntidad.all())
            spans = []
            for s in spans_bd:
                span = doc.char_span(
                    s.inicio, s.fin, label=s.etiqueta.nombre, alignment_mode="strict"
                )
                if span is None:
                    self.stderr.write(self.style.WARNING(
                        f"Ejemplo #{ejemplo.id}: offsets ({s.inicio},{s.fin}) "
                        f"no alinean con tokens, span ignorado"
                    ))
                    continue
                spans.append(span)

            # Si no va a para el ner
            if spans_bd and not spans and not tiene_intencion:
                # Todas las anotaciones fallaron: usarlo sería enseñar "sin entidades"
                self.stderr.write(self.style.WARNING(
                    f"Ejemplo #{ejemplo.id}: sin spans validos ni intencion, omitido"
                ))
                continue

            if spans:
                doc.set_ents(filter_spans(spans))
            else:
                doc.set_ents([], default="missing")

            if not tiene_intencion and not spans:
                self.stderr.write(self.style.WARNING(
                    f"Ejemplo #{ejemplo.id}: sin intencion ni entidades, omitido"
                ))
                continue

            split = "dev" if es_dev(ejemplo.texto, options["dev_ratio"]) else "train"
            dbs[split].add(doc)

            c = stats[split]
            c["ejemplos"] += 1
            if tiene_intencion:
                c[f"intent:{ejemplo.intencion.nombre}"] += 1
            for ent in doc.ents:
                c[f"ent:{ent.label_}"] += 1

        SPACY_DIR.mkdir(parents=True, exist_ok=True)
        for split, db in dbs.items():
            db.to_disk(SPACY_DIR / f"{split}.spacy")
            self.stdout.write(self.style.SUCCESS(f"{split}.spacy: {stats[split]['ejemplos']} ejemplos"))
            for k, v in sorted(stats[split].items()):
                if k != "ejemplos":
                    self.stdout.write(f"  {k}: {v}")

            faltan = [e for e in etiquetas_intencion if stats[split][f"intent:{e}"] == 0]
            if faltan:
                self.stderr.write(self.style.WARNING(f"  {split} no tiene ejemplos de: {faltan}"))