import csv
from decimal import Decimal
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from entrenamiento.models import Servicio

RUTA_POR_DEFECTO = Path(settings.BASE_DIR) / "entrenamiento" / "datos" / "servicios.csv"


class Command(BaseCommand):
    help = "Carga Servicios desde un CSV (idempotente, por nombre unico)"

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=str(RUTA_POR_DEFECTO))

    def handle(self, *args, **options):
        ruta = Path(options["csv"])
        if not ruta.exists():
            self.stderr.write(self.style.ERROR(f"No existe {ruta}"))
            return

        creados = actualizados = 0
        with ruta.open(encoding="utf-8-sig") as f, transaction.atomic():
            for fila in csv.DictReader(f):
                _, creado = Servicio.objects.update_or_create(
                    nombre=fila["nombre"].strip(),
                    defaults={
                        "descripcion": fila.get("descripcion", "").strip(),
                        "coste": Decimal(fila["coste"]),
                        "tiempo_aproximado": int(fila["tiempo_aproximado"]),
                    },
                )
                creados += creado
                actualizados += not creado

        self.stdout.write(self.style.SUCCESS(f"Servicios: {creados} creados, {actualizados} actualizados."))