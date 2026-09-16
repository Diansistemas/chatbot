"""
Regenera los bloques MESSAGE de los Modelfile.* a partir de las conversaciones
de ejemplo (entrenamiento.Ejemplo) guardadas en la base de datos.

La cabecera (FROM / PARAMETER / SYSTEM) de cada modelo NO se toca: se lee tal
cual de llms/cabeceras/cabecera.<intencion>, que se edita a mano. Este comando
solo se encarga de anadir los ejemplos de conversacion reales.

Uso:
    python manage.py generar_modelfiles
    python manage.py generar_modelfiles --solo-manual
    python manage.py generar_modelfiles --crear      # ademas ejecuta "ollama create"
"""

import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from entrenamiento.models import Ejemplo

# Conversacion.tipo (chat.models) -> nombre de intencion usado en MAPA_MODELO
# (acceso.py) y en los nombres Modelfile.<intencion> / chatbot-<intencion>.
# OJO: si cambias los "choices" de Conversacion.tipo o las claves de
# MAPA_MODELO, actualiza este mapa tambien.
TIPO_A_INTENCION = {
    "compra": "compra",
    "consulta_tecnica": "consulta",
    "sin_clasificar": "otro",
}

# Carpeta donde viven los Modelfile.* y crear_modelos.bash/.ps1
LLMS_DIR = Path(settings.BASE_DIR) / "llms"
CABECERAS_DIR = LLMS_DIR / "cabeceras"

# Limite de conversaciones de ejemplo por modelo, para no disparar el tamano
# del prompt fijo que se antepone en cada llamada al LLM
MAX_EJEMPLOS_POR_MODELO = 9999


def escapar_triple_comillas(texto):
    # Los MESSAGE de Ollama se delimitan con """; si el texto real contuviera
    # ese literal (muy raro) rompemos la secuencia para no cerrar el bloque antes de tiempo
    return texto.replace('"""', '\\"\\"\\"')


class Command(BaseCommand):
    help = "Genera los Modelfile.* a partir de las conversaciones de ejemplo guardadas en la BD"

    def add_arguments(self, parser):
        parser.add_argument(
            "--solo-manual",
            action="store_true",
            help="Usar unicamente ejemplos con origen='manual' (curados a mano), ignorando los que vienen del propio chatbot",
        )
        parser.add_argument(
            "--crear",
            action="store_true",
            help="Ademas de generar los Modelfile.*, ejecuta 'ollama create' para cada uno",
        )

    def handle(self, *args, **options):
        LLMS_DIR.mkdir(parents=True, exist_ok=True)

        for tipo, intencion in TIPO_A_INTENCION.items():
            ok = self.generar_modelfile(tipo, intencion, solo_manual=options["solo_manual"])
            if ok and options["crear"]:
                self.crear_modelo_ollama(intencion)

    def generar_modelfile(self, tipo, intencion, solo_manual):
        cabecera_path = CABECERAS_DIR / f"cabecera.{intencion}"
        if not cabecera_path.exists():
            self.stderr.write(self.style.ERROR(
                f"No encuentro {cabecera_path}. Crea ahi el FROM/PARAMETER/SYSTEM fijo de '{intencion}' antes de generar."
            ))
            return False

        cabecera = cabecera_path.read_text(encoding="utf-8")

        ejemplos = (
            Ejemplo.objects.filter(conversacion__intencion__nombre=tipo)
            .select_related("conversacion")
        )
        if solo_manual:
            ejemplos = ejemplos.filter(origen="manual")
        ejemplos = list(ejemplos[:MAX_EJEMPLOS_POR_MODELO])

        if not ejemplos:
            self.stdout.write(self.style.WARNING(
                f"No hay ejemplos en BD para tipo='{tipo}' (intencion='{intencion}'). "
                f"Se genera el Modelfile solo con la cabecera, sin MESSAGE."
            ))

        bloques_message = []
        for ejemplo in ejemplos:

            mensaje_usuario = ejemplo.conversacion.texto_usuario
            mensaje_chat = ejemplo.conversacion.texto_chatbot

            bloques_message.append(f'MESSAGE user """{mensaje_usuario}"""')
            bloques_message.append(f'MESSAGE assistant """{mensaje_chat}"""')

        contenido = cabecera.rstrip() + "\n\n" + "\n".join(bloques_message) + "\n"

        salida_path = LLMS_DIR / f"Modelfile.{intencion}"
        salida_path.write_text(contenido, encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(
            f"{salida_path} generado: {len(bloques_message)} mensajes"
        ))

    def crear_modelo_ollama(self, intencion):
        modelfile = LLMS_DIR / f"Modelfile.{intencion}"
        modelo = f"chatbot-{intencion}"
        self.stdout.write(f"Ejecutando: ollama create {modelo} -f {modelfile.name}")
        try:
            subprocess.run(
                ["ollama", "create", modelo, "-f", modelfile.name],
                cwd=LLMS_DIR,
                check=True,
            )
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(
                "No se encuentra el ejecutable 'ollama' en el PATH. Instala Ollama o ejecuta el comando sin --crear."
            ))
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"'ollama create' fallo para {modelo}: {e}"))