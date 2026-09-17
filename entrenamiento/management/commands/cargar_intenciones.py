import csv
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from entrenamiento.models import Intencion

RUTA_POR_DEFECTO = Path(settings.BASE_DIR) / "entrenamiento" / "datos" / "intenciones.csv"


class Command(BaseCommand):
    help = "Carga Intenciones desde un CSV (idempotente)"

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=str(RUTA_POR_DEFECTO))

    def handle(self, *args, **options):
        ruta = Path(options["csv"])
        if not ruta.exists():
            self.stderr.write(self.style.ERROR(f"No existe {ruta}"))
            return

        contadores = {"intencion_c": 0, "intencion_a": 0, "entidad_c": 0, "entidad_a": 0}

        with ruta.open(encoding="utf-8-sig") as f, transaction.atomic():
            for fila in csv.DictReader(f,  delimiter=";"):
                nombre = fila["nombre"].strip()
                descripcion = fila.get("descripcion", "").strip()
                activa = fila.get("activa", "").strip().lower() in ("1", "true", "si", "sí")
                _, creado = Intencion.objects.update_or_create(
                    nombre=nombre, defaults={"descripcion": descripcion, "activa": activa}
                )
                contadores["intencion_c" if creado else "intencion_a"] += 1

        self.stdout.write(self.style.SUCCESS(
            f"Intenciones: {contadores['intencion_c']} creadas, {contadores['intencion_a']} actualizadas. "
            f"Entidades: {contadores['entidad_c']} creadas, {contadores['entidad_a']} actualizadas."
        ))