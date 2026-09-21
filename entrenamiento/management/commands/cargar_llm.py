import csv
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from entrenamiento.models import Intencion, Par_Mensaje_Respuesta, EjemploLLM

# Donde guardamos los pares de mensaje
RUTA_POR_DEFECTO = Path(settings.BASE_DIR) / "entrenamiento" / "datos" / "llm.csv"

# Que hacaemos
class Command(BaseCommand):

    # Otros csv y si quieres eliminar los ejemplos "manuales"
    def add_arguments(self, parser):
        parser.add_argument("--csv", default=str(RUTA_POR_DEFECTO))
        parser.add_argument("--limpiar", action="store_true")

    # Que hacemos
    def handle(self, *args, **options):
        ruta = Path(options["csv"])
        if not ruta.exists():
            self.stderr.write(self.style.ERROR(f"No existe {ruta}"))
            return

        # Estamos limpiando?
        if options["limpiar"]:
            ids = list(EjemploLLM.objects.filter(origen="manual").values_list("conversacion_id", flat=True))
            EjemploLLM.objects.filter(origen="manual").delete()
            Par_Mensaje_Respuesta.objects.filter(id__in=ids).delete()

        cache_intenciones = {i.nombre: i for i in Intencion.objects.all()}
        creados = 0

        with ruta.open(encoding="utf-8-sig") as f, transaction.atomic():
            for n_fila, fila in enumerate(csv.DictReader(f, delimiter=";"), start=2):
                intencion = cache_intenciones.get(fila["intencion"].strip())
                if intencion is None:
                    self.stderr.write(self.style.WARNING(
                        f"Fila {n_fila}: intencion '{fila['intencion']}' no existe (¿cargaste labels.csv antes?), ignorada"
                    ))
                    continue

                par = Par_Mensaje_Respuesta(
                    intencion=intencion,
                    texto_usuario=fila["texto_usuario"].strip(),
                    texto_chatbot=fila["texto_chatbot"].strip(),
                )
                par.save()

                EjemploLLM.objects.create(mensaje_respuesta=par, origen=fila.get("origen", "manual").strip() or "manual")
                creados += 1

        self.stdout.write(self.style.SUCCESS(f"LLM: {creados} ejemplos cargados"))