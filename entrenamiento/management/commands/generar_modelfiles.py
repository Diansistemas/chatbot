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
from core.acceso import nombre_modelo, dominios_desde_allowed_hosts

from entrenamiento.models import EjemploLLM

# Conversacion.tipo (chat.models) -> nombre de intencion usado en MAPA_MODELO
# (acceso.py) y en los nombres Modelfile.<intencion> / chatbot-<intencion>.
# OJO: si cambias los "choices" de Conversacion.tipo o las claves de
# MAPA_MODELO, actualiza este mapa tambien.
TIPO_INTENCION = {
    "compra": "compra",
    "consulta_tecnica": "consulta",
    "sin_clasificar": "otro",
}

# Carpeta donde viven los Modelfile.* y crear_modelos.bash/.ps1
LLMS_DIR = Path(settings.BASE_DIR) / "entrenamiento" / "llms"
CABECERAS_DIR = LLMS_DIR / "cabeceras"
CABECERAS_DEFAULT_DIR = CABECERAS_DIR / "default"
CABECERAS_DOMINIOS_DIR = CABECERAS_DIR / "dominios"

# Limite de conversaciones de ejemplo por modelo, para no disparar el tamano
# del prompt fijo que se antepone en cada llamada al LLM
MAX_EJEMPLOS_POR_MODELO = 9999

# Cabereceras por defecto
CABECERAS_POR_DEFECTO = {
    "compra": '''FROM llama3.2
 
PARAMETER temperature 0.5
 
SYSTEM """
Eres el asistente virtual de ventas de Dian Sistemas. Tu trabajo es ayudar a
un usuario a completar un pedido de un servicio de la empresa.
 
Se breve, cercano y profesional. No inventes precios, plazos ni servicios que
no te haya dado el contexto.
"""
''',
    "consulta": '''FROM llama3.2
 
PARAMETER temperature 0.5
 
SYSTEM """
Eres el asistente virtual de soporte tecnico de Dian Sistemas. Tu trabajo es
ayudar a un usuario a resolver dudas o problemas tecnicos sobre los servicios
de la empresa.
 
Se claro, preciso y profesional. No inventes soluciones ni datos tecnicos que
no te haya dado el contexto.
"""
''',
    "otro": '''FROM llama3.2
 
PARAMETER temperature 0.5
 
SYSTEM """
Eres el asistente virtual de Dian Sistemas. Ayuda al usuario con su consulta
de la forma mas util posible y, si detectas que en realidad busca comprar un
servicio o resolver una duda tecnica, guialo hacia ello.
 
Se breve, cercano y profesional.
"""
''',
}

def escapar_triple_comillas(texto):
    # Los MESSAGE de Ollama se delimitan con """; si el texto real contuviera
    # ese literal (muy raro) rompemos la secuencia para no cerrar el bloque antes de tiempo
    return texto.replace('"""', '\\"\\"\\"')


class Command(BaseCommand):
    help = "Genera los Modelfile.* (default + uno por dominio de ALLOWED_HOSTS) a partir de las conversaciones de ejemplo guardadas en la BD"
 
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
        parser.add_argument(
            "--dominio",
            action="append",
            default=None,
            help="Genera solo para este dominio (repite la opcion para varios). Por defecto: 'default' + todos los dominios de settings.ALLOWED_HOSTS.",
        )
 
    def handle(self, *args, **options):
        LLMS_DIR.mkdir(parents=True, exist_ok=True)
        CABECERAS_DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
        CABECERAS_DOMINIOS_DIR.mkdir(parents=True, exist_ok=True)
 
        if options["dominio"]:
            dominios = list(options["dominio"])
        else:
            dominios = [None] + dominios_desde_allowed_hosts(settings.ALLOWED_HOSTS)
            if len(dominios) == 1:
                self.stdout.write(self.style.WARNING(
                    "settings.ALLOWED_HOSTS no tiene dominios (solo se generara el set 'default'). "
                    "Anade tus dominios ahi para que tengan su propio modelo."
                ))
 
        for dominio in dominios:
            for tipo, intencion in TIPO_INTENCION.items():
                ok = self.generar_modelfile(intencion, dominio, solo_manual=options["solo_manual"])
                if ok and options["crear"]:
                    self.crear_modelo_ollama(intencion, dominio)
 
    # ------------------------------------------------------------------
    # Cabeceras
    # ------------------------------------------------------------------
 
    def ruta_cabecera(self, intencion, dominio):
        if dominio:
            return CABECERAS_DOMINIOS_DIR / dominio / f"cabecera.{intencion}"
        return CABECERAS_DEFAULT_DIR / f"cabecera.{intencion}"
 
    def resolver_cabecera(self, intencion, dominio):
        """
        Texto de la cabecera a usar para (intencion, dominio): la propia del
        dominio si existe, si no la de default/ (creandola con una plantilla
        basica si tampoco existe todavia).
        """
        ruta_default = self.ruta_cabecera(intencion, None)
        if not ruta_default.exists():
            if not self.crear_cabecera_basica(ruta_default, intencion):
                return None
        cabecera_default = ruta_default.read_text(encoding="utf-8")
 
        if dominio is None:
            return cabecera_default
 
        ruta_dominio = self.ruta_cabecera(intencion, dominio)
        if ruta_dominio.exists():
            return ruta_dominio.read_text(encoding="utf-8")
 
        self.stdout.write(self.style.WARNING(
            f"[{dominio}] No hay {ruta_dominio}; uso la cabecera de default/ para '{intencion}'."
        ))
        return cabecera_default
 
    def crear_cabecera_basica(self, cabecera_path, intencion):
        plantilla = CABECERAS_POR_DEFECTO.get(intencion)
        if plantilla is None:
            self.stderr.write(self.style.ERROR(
                f"No encuentro {cabecera_path} y no hay cabecera por defecto para "
                f"'{intencion}'. Anade una entrada en CABECERAS_POR_DEFECTO o crea "
                f"el fichero a mano antes de generar."
            ))
            return False
 
        cabecera_path.parent.mkdir(parents=True, exist_ok=True)
        cabecera_path.write_text(plantilla, encoding="utf-8")
        self.stdout.write(self.style.WARNING(
            f"No existia {cabecera_path}: creada una cabecera basica por defecto. "
            f"Revisala y ajustala a mano si hace falta."
        ))
        return True
 
    # ------------------------------------------------------------------
    # Ejemplos
    # ------------------------------------------------------------------
 
    def obtener_ejemplos(self, intencion, dominio, solo_manual):
        base = EjemploLLM.objects.filter(
            mensaje_respuesta__intencion__nombre=intencion
        ).select_related("mensaje_respuesta")
        if solo_manual:
            base = base.filter(origen="manual")
 
        if dominio is None:
            return list(base[:MAX_EJEMPLOS_POR_MODELO])
 
        ejemplos_dominio = list(
            base.filter(
                mensaje_respuesta__mensaje_usuario__conversacion__dominio=dominio
            )[:MAX_EJEMPLOS_POR_MODELO]
        )
        if ejemplos_dominio:
            return ejemplos_dominio
 
        # El dominio todavia no tiene ejemplos propios: usamos los generales
        # como semilla, para que el modelo del dominio no se quede vacio.
        self.stdout.write(self.style.WARNING(
            f"[{dominio}] No tiene ejemplos propios para '{intencion}'; "
            f"uso los ejemplos generales como semilla."
        ))
        return list(base[:MAX_EJEMPLOS_POR_MODELO])
 
    # ------------------------------------------------------------------
    # Generacion
    # ------------------------------------------------------------------
 
    def generar_modelfile(self, intencion, dominio, solo_manual):
        cabecera = self.resolver_cabecera(intencion, dominio)
        if cabecera is None:
            return False
 
        ejemplos = self.obtener_ejemplos(intencion, dominio, solo_manual)
 
        if not ejemplos:
            self.stdout.write(self.style.WARNING(
                f"No hay ejemplos en BD (ni propios ni generales) para intencion='{intencion}' "
                f"dominio='{dominio or 'default'}'. Se genera el Modelfile solo con la cabecera."
            ))
 
        bloques_message = []
        for ejemplo in ejemplos:
            mensaje_usuario = escapar_triple_comillas(ejemplo.mensaje_respuesta.texto_usuario)
            mensaje_chat = escapar_triple_comillas(ejemplo.mensaje_respuesta.texto_chatbot)
 
            bloques_message.append(f'MESSAGE user """{mensaje_usuario}"""')
            bloques_message.append(f'MESSAGE assistant """{mensaje_chat}"""')
 
        contenido = cabecera.rstrip() + "\n\n" + "\n".join(bloques_message) + "\n"
 
        etiqueta = dominio or "default"
        salida_path = LLMS_DIR / f"Modelfile.{etiqueta}.{intencion}"
        salida_path.write_text(contenido, encoding="utf-8")
 
        self.stdout.write(self.style.SUCCESS(
            f"{salida_path} generado: {len(bloques_message)} mensajes"
        ))
 
        return True
 
    def crear_modelo_ollama(self, intencion, dominio):
        etiqueta = dominio or "default"
        modelfile = LLMS_DIR / f"Modelfile.{etiqueta}.{intencion}"
        modelo = nombre_modelo(intencion, dominio)
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