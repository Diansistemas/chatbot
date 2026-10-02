from django.core.management import call_command
from django.core.management.base import BaseCommand

# Todos los cargar en linea
class Command(BaseCommand):

    # Si le pasas --limpiar, limpiamos los ejemplos existentes
    # Esta solo para los ejemplos iniciales de llm y nlp para evitar tener varias veces el mismo mensaje
    def add_arguments(self, parser):
        parser.add_argument("--limpiar", action="store_true",)

    # Que hacemos y en que orden
    def handle(self, *args, **options):
        self.stdout.write("1/5 etiquetas...")
        call_command("cargar_etiquetas")
        self.stdout.write("2/5 intenciones...")
        call_command("cargar_intenciones")
        self.stdout.write("3/5 servicios...")
        call_command("cargar_servicios")
        self.stdout.write("4/5 llm...")
        call_command("cargar_llm", limpiar=options["limpiar"])
        self.stdout.write("5/5 nlp...")
        call_command("cargar_nlp", limpiar=options["limpiar"])
        self.stdout.write(self.style.SUCCESS("Datos iniciales cargados."))