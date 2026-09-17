import csv
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from entrenamiento.models import Intencion, Par_Mensaje_Respuesta, EjemploLLM

RUTA_POR_DEFECTO = Path(settings.BASE_DIR) / "entrenamiento" / "dats" / "llm.csv"


class Command(BaseCommand):
    help = "Carga ejemplos de conversacion (Par_Mensaje_Respuesta + Ejemplo) para el LLM"

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=str(RUTA_POR_DEFECTO))
        parser.add_argument("--limpiar", action="store_true",
                             help="Borra los Ejemplo/Par_Mensaje_Respuesta con origen manual antes de cargar")

    def handle(self, *args, **options):
        ruta = Path(options["csv"])
        if not ruta.exists():
            self.stderr.write(self.style.ERROR(f"No existe {ruta}"))
            return

        if options["limpiar"]:
            ids = list(EjemploLLM.objects.filter(origen="manual").values_list("conversacion_id", flat=True))
            EjemploLLM.objects.filter(origen="manual").delete()
            Par_Mensaje_Respuesta.objects.filter(id__in=ids).delete()

        cache_intenciones = {i.nombre: i for i in Intencion.objects.all()}
        creados = 0

        with ruta.open(encoding="utf-8-sig") as f, transaction.atomic():
            for n_fila, fila in enumerate(csv.DictReader(f), start=2,  delimiter=";"):
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

                EjemploLLM.objects.create(conversacion=par, origen=fila.get("origen", "manual").strip() or "manual")
                creados += 1

        self.stdout.write(self.style.SUCCESS(f"LLM: {creados} ejemplos cargados"))