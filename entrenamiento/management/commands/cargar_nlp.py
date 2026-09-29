import csv

from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from entrenamiento.models import Intencion, EtiquetaEntidad, EjemploNLP, SpanEntidad

# Donde guardamos los ejemplos
RUTA_POR_DEFECTO = Path(settings.BASE_DIR) / "entrenamiento" / "datos" / "nlp.csv"

# Que hacemos
class Command(BaseCommand):

    # Otros csv y si quieres borrar los ejemplos manuales
    def add_arguments(self, parser):
        parser.add_argument("--csv", default=str(RUTA_POR_DEFECTO))
        parser.add_argument("--limpiar", action="store_true")

    # Que hacemos
    def handle(self, *args, **options):
        ruta = Path(options["csv"])
        if not ruta.exists():
            self.stderr.write(self.style.ERROR(f"No existe {ruta}"))
            return

        # Borramos manuales
        if options["limpiar"]:
            EjemploNLP.objects.filter(origen="manual").delete()

        cache_intenciones = {i.nombre: i for i in Intencion.objects.all()}
        cache_etiquetas = {e.nombre: e for e in EtiquetaEntidad.objects.all()}
        creados = 0

        # Guardamos todos los ejemplos juntos, el tratamiento para el doc va en en el generar_nlp
        with ruta.open(encoding="utf-8-sig") as f, transaction.atomic():
            for n_fila, fila in enumerate(csv.DictReader(f, delimiter=";"), start=2):
                texto = (fila.get("texto") or "").strip()
                nombre_intencion = (fila.get("intencion") or "").strip()
                intencion = None
                if nombre_intencion:
                    intencion = cache_intenciones.get(nombre_intencion)
                    if intencion is None:
                        self.stderr.write(self.style.WARNING(f"Fila {n_fila}: intencion '{nombre_intencion}' no existe, fila omitida"))
                        continue

                if not texto or (not intencion and not (fila.get("entidades") or "").strip()):
                    self.stderr.write(self.style.WARNING(f"Fila {n_fila}: sin texto o sin intencion ni entidades, omitida"))
                    continue
                
                ejemplo = EjemploNLP.objects.create(
                    texto=texto, intencion=intencion,
                    origen=(fila.get("origen") or "").strip() or "manual",
                )

                for entrada in (fila.get("entidades") or "").split("|"):
                    entrada = entrada.strip()
                    if not entrada:
                        continue
                    if ":" not in entrada:
                        self.stderr.write(self.style.WARNING(f"Fila {n_fila}: entidad mal formada '{entrada}'"))
                        continue

                    nombre_etiqueta, texto_span = (p.strip() for p in entrada.split(":", 1))
                    etiqueta = cache_etiquetas.get(nombre_etiqueta)
                    if etiqueta is None:
                        self.stderr.write(self.style.WARNING(f"Fila {n_fila}: etiqueta '{nombre_etiqueta}' no existe"))
                        continue

                    ocurrencias = [i for i in range(len(texto)) if texto.startswith(texto_span, i)]
                    if not ocurrencias:
                        self.stderr.write(self.style.WARNING(f"Fila {n_fila}: '{texto_span}' no aparece en el texto"))
                        continue
                    if len(ocurrencias) > 1:
                        self.stderr.write(self.style.WARNING(
                            f"Fila {n_fila}: '{texto_span}' aparece {len(ocurrencias)} veces, se usa la primera"
                        ))

                    inicio = ocurrencias[0]
                    SpanEntidad.objects.create(ejemplo=ejemplo, etiqueta=etiqueta, inicio=inicio, fin=inicio + len(texto_span))

                creados += 1

        self.stdout.write(self.style.SUCCESS(f"NLP: {creados} ejemplos cargados"))