#!/usr/bin/env python3
"""Asistente de configuracion para dockerizar el Chatbot.

Pregunta paso a paso los datos del proyecto y escribe el fichero .env que
usan docker compose (env_file e interpolacion) y Django (python-dotenv).
Al dockerizar no hace falta editar nada a mano: el propio ejecutable va
pidiendo los datos para configurarse.

Uso:
    python configurar_entorno.py                # interactivo (pregunta)
    python configurar_entorno.py --fuerza       # reconfigurar aunque ya exista .env
    python configurar_entorno.py --defaults     # sin preguntar: valores por defecto
    python configurar_entorno.py --salida RUTA  # escribir en otra ruta (defecto: .env)

Lo lanzan: docker_setup.sh, install.sh e install.ps1.
Solo usa la libreria estandar: no necesita Django ni dependencias instaladas.
"""
import argparse
import datetime
import getpass
import secrets
import sys
from pathlib import Path

# Valores por defecto de cada variable del .env
DEFECTOS = {
    "SECRET_KEY": "",
    "DEBUG": "True",
    "ALLOWED_HOSTS": "localhost,127.0.0.1",
    "CSRF_TRUSTED_ORIGINS": "",
    "DOMINIOS_PERMITIDOS": "",
    "WEB_PORT": "8000",
    "OLLAMA_HOST": "http://localhost:11434",
    "OLLAMA_MODEL_RESUMEN": "llama3.2",
    "EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend",
    "EMAIL_HOST": "",
    "EMAIL_PORT": "587",
    "EMAIL_HOST_USER": "",
    "EMAIL_HOST_PASSWORD": "",
    "EMAIL_USE_TLS": "False",
    "RESUMEN_EMAIL_DESTINATARIOS": "",
    "SPACY_MODEL_HOST_PATH": "",
    "FORCE_TRAIN": "0",
}

# Orden y comentarios con los que se escribe el .env
CLAVES = [
    ("SECRET_KEY", "Clave secreta de Django (no la subas a GitHub)"),
    ("DEBUG", "True/False; en produccion mejor False"),
    ("ALLOWED_HOSTS", "Hosts que puede servir Django, sin esquema, separados por coma"),
    ("CSRF_TRUSTED_ORIGINS", "Origenes admitidos en peticiones cross-origin, con esquema"),
    ("DOMINIOS_PERMITIDOS", "Dominios que pueden embeber el widget (obligatorio esquema)"),
    ("WEB_PORT", "Puerto del chatbot en el host (lo usa docker-compose)"),
    ("OLLAMA_HOST", "Ollama local; en Docker compose lo sustituye por http://ollama:11434"),
    ("OLLAMA_MODEL_RESUMEN", "Modelo de Ollama para resumenes (se baja en el primer arranque)"),
    ("EMAIL_BACKEND", "Correo de resumenes: consola (pruebas) o SMTP (real)"),
    ("EMAIL_HOST", "Servidor SMTP"),
    ("EMAIL_PORT", "Puerto SMTP"),
    ("EMAIL_HOST_USER", "Usuario SMTP"),
    ("EMAIL_HOST_PASSWORD", "Contrasena SMTP"),
    ("EMAIL_USE_TLS", "True/False"),
    ("RESUMEN_EMAIL_DESTINATARIOS", "Destinatarios de los resumenes, separados por coma"),
    ("SPACY_MODEL_HOST_PATH", "Ruta a un modelo spaCy entrenado (vacio = entrenar en el contenedor)"),
    ("FORCE_TRAIN", "1 = reentrenar el modelo NLP en el primer arranque de Docker"),
]


# ---------------------------------------------------------------------------
# Utilidades de entrada
# ---------------------------------------------------------------------------
def preguntar(texto, defecto=""):
    """Pide un valor por teclado. Enter = defecto. Sin entrada = defecto."""
    try:
        if defecto:
            respuesta = input("  %s [%s]: " % (texto, defecto)).strip()
        else:
            respuesta = input("  %s: " % texto).strip()
    except EOFError:
        print("")
        return defecto
    return respuesta or defecto


def preguntar_si_no(texto, defecto=True):
    while True:
        try:
            respuesta = input(
                "  %s [s/n] (%s): " % (texto, "s" if defecto else "n")
            ).strip().lower()
        except EOFError:
            print("")
            return defecto
        if not respuesta:
            return defecto
        if respuesta in ("s", "si", "sí", "y", "yes"):
            return True
        if respuesta in ("n", "no"):
            return False
        print("    Responde 's' o 'n'.")


def preguntar_puerto(texto, defecto="8000"):
    while True:
        respuesta = preguntar(texto, defecto)
        if respuesta.isdigit() and 1 <= int(respuesta) <= 65535:
            return respuesta
        print("    Eso no es un puerto valido (entre 1 y 65535).")


def preguntar_dominios(texto, defecto):
    """Lista separada por comas; cada entrada tiene que llevar esquema."""
    while True:
        respuesta = preguntar(texto, defecto)
        piezas = [p.strip() for p in respuesta.split(",") if p.strip()]
        if not piezas:
            print("    Tiene que haber al menos un valor.")
            return defecto
        sin_esquema = [p for p in piezas if "://" not in p]
        if sin_esquema:
            print(
                "    Falta el esquema en: %s   (ejemplo: https://midominio.com)"
                % ", ".join(sin_esquema)
            )
            continue
        return ",".join(piezas)


def preguntar_contrasena(texto, defecto=""):
    """Como preguntar pero sin mostrar lo que se teclea."""
    etiqueta = "%s [Enter para conservar]" % texto if defecto else texto
    try:
        respuesta = getpass.getpass("  %s: " % etiqueta)
    except (EOFError, KeyboardInterrupt):
        print("")
        return defecto
    return respuesta or defecto


def es_verdadero(valor):
    return str(valor).strip().lower() in ("1", "true", "yes", "s", "si", "sí")


def generar_secret_key():
    return secrets.token_urlsafe(48)


# ---------------------------------------------------------------------------
# Lectura / escritura del .env
# ---------------------------------------------------------------------------
def leer_env(ruta):
    """Lee KEY=VALUE tolerando espacios y comillas (formato del .env actual)."""
    datos = {}
    try:
        lineas = Path(ruta).read_text(encoding="utf-8").splitlines()
    except OSError:
        return datos
    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        clave = clave.strip()
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "'\"":
            valor = valor[1:-1]
        if clave:
            datos[clave] = valor
    return datos


def formatear_valor(valor):
    """Las contraseñas con espacios, # o comillas van entre comillas dobles."""
    if any(c in valor for c in " \t#\"'"):
        return '"%s"' % valor.replace("\\", "\\\\").replace('"', '\\"')
    return valor


def escribir_env(ruta, valores, extras):
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lineas = [
        "# .env del Chatbot - generado por configurar_entorno.py el %s" % fecha,
        "# No lo subas a GitHub (esta en .gitignore y en .dockerignore).",
        "# docker-compose lo usa como env_file y como fuente de ${WEB_PORT},",
        "# ${OLLAMA_MODEL_RESUMEN} y ${SPACY_MODEL_HOST_PATH}.",
        "",
    ]
    for clave, comentario in CLAVES:
        if clave in valores:
            lineas.append("# %s" % comentario)
            lineas.append("%s=%s" % (clave, formatear_valor(valores[clave])))
            lineas.append("")
    if extras:
        lineas.append("# Otras variables conservadas del fichero anterior")
        for clave, valor in extras.items():
            lineas.append("%s=%s" % (clave, formatear_valor(valor)))
        lineas.append("")
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Asistente
# ---------------------------------------------------------------------------
def completar_defaults(valores):
    """Rellena sin preguntar lo que dependa de otras respuestas."""
    if not valores.get("SECRET_KEY"):
        valores["SECRET_KEY"] = generar_secret_key()
    puerto = valores.get("WEB_PORT") or "8000"
    if not valores.get("CSRF_TRUSTED_ORIGINS"):
        valores["CSRF_TRUSTED_ORIGINS"] = "http://localhost:%s" % puerto
    if not valores.get("DOMINIOS_PERMITIDOS"):
        valores["DOMINIOS_PERMITIDOS"] = "http://localhost:%s" % puerto
    if not valores.get("DEBUG"):
        valores["DEBUG"] = "True"


def preguntar_todo(valores):
    print("")
    print("== 1) Servidor web ==")
    valores["WEB_PORT"] = preguntar_puerto(
        "Puerto en el que atendera el chatbot", valores.get("WEB_PORT") or "8000"
    )

    print("")
    print("== 2) Seguridad de Django ==")
    clave_actual = valores.get("SECRET_KEY") or ""
    if clave_actual:
        if not preguntar_si_no("Ya hay una SECRET_KEY; conservarla", True):
            valores["SECRET_KEY"] = generar_secret_key()
            print("    Nueva SECRET_KEY generada.")
    else:
        valores["SECRET_KEY"] = (
            preguntar("SECRET_KEY (Enter para generar una nueva)", "")
            or generar_secret_key()
        )
    valores["DEBUG"] = (
        "True"
        if preguntar_si_no(
            "Modo DEBUG (errores detallados en pantalla; en produccion mejor no)",
            es_verdadero(valores.get("DEBUG", "True")),
        )
        else "False"
    )

    print("")
    print("== 3) Hosts y origenes ==")
    valores["ALLOWED_HOSTS"] = preguntar(
        "Hosts admitidos (coma, sin esquema; anade aqui tu dominio)",
        valores.get("ALLOWED_HOSTS") or "localhost,127.0.0.1",
    )
    origen_defecto = valores.get("CSRF_TRUSTED_ORIGINS") or (
        "http://localhost:%s" % valores["WEB_PORT"]
    )
    valores["CSRF_TRUSTED_ORIGINS"] = preguntar_dominios(
        "Origenes admitidos en peticiones cross-origin", origen_defecto
    )

    print("")
    print("== 4) Widget embebido ==")
    widget_defecto = valores.get("DOMINIOS_PERMITIDOS") or (
        "http://localhost:%s" % valores["WEB_PORT"]
    )
    valores["DOMINIOS_PERMITIDOS"] = preguntar_dominios(
        "Dominios que pueden embeber el widget (esquema obligatorio)",
        widget_defecto,
    )

    print("")
    print("== 5) Ollama (modelos LLM) ==")
    valores["OLLAMA_MODEL_RESUMEN"] = preguntar(
        "Modelo de Ollama para los resumenes",
        valores.get("OLLAMA_MODEL_RESUMEN") or "llama3.2",
    )

    print("")
    print("== 6) Email de resumenes ==")
    es_smtp = "smtp" in (valores.get("EMAIL_BACKEND") or "")
    if preguntar_si_no("Enviar los resumenes por SMTP real (si no: consola/pruebas)", es_smtp):
        valores["EMAIL_BACKEND"] = "django.core.mail.backends.smtp.EmailBackend"
        valores["EMAIL_HOST"] = preguntar(
            "Servidor SMTP", valores.get("EMAIL_HOST") or "smtp.gmail.com"
        )
        valores["EMAIL_PORT"] = preguntar_puerto(
            "Puerto SMTP", valores.get("EMAIL_PORT") or "587"
        )
        valores["EMAIL_HOST_USER"] = preguntar(
            "Usuario SMTP", valores.get("EMAIL_HOST_USER") or ""
        )
        valores["EMAIL_HOST_PASSWORD"] = preguntar_contrasena(
            "Contrasena SMTP", valores.get("EMAIL_HOST_PASSWORD") or ""
        )
        tls_defecto = es_verdadero(valores.get("EMAIL_USE_TLS", "")) or (
            valores["EMAIL_PORT"] == "587"
        )
        valores["EMAIL_USE_TLS"] = (
            "True" if preguntar_si_no("Usar TLS", tls_defecto) else "False"
        )
    else:
        valores["EMAIL_BACKEND"] = "django.core.mail.backends.console.EmailBackend"
    valores["RESUMEN_EMAIL_DESTINATARIOS"] = preguntar(
        "Destinatarios de los resumenes (coma)",
        valores.get("RESUMEN_EMAIL_DESTINATARIOS") or "",
    )

    print("")
    print("== 7) Modelo spaCy (NLP) ==")
    valores["SPACY_MODEL_HOST_PATH"] = preguntar(
        "Ruta a un modelo spaCy ya entrenado (Enter vacio = entrenarlo en el contenedor)",
        valores.get("SPACY_MODEL_HOST_PATH") or "",
    )
    if valores["SPACY_MODEL_HOST_PATH"]:
        valores["FORCE_TRAIN"] = "0"
        print("    Con modelo externo no se reentrena (FORCE_TRAIN=0).")
    else:
        valores["FORCE_TRAIN"] = (
            "1"
            if preguntar_si_no(
                "Reentrenar el modelo NLP en el primer arranque (tarda)",
                es_verdadero(valores.get("FORCE_TRAIN", "0")),
            )
            else "0"
        )


def resumen(ruta, valores):
    print("")
    print("Configuracion guardada en %s" % ruta)
    visibles = [
        "WEB_PORT",
        "DEBUG",
        "ALLOWED_HOSTS",
        "CSRF_TRUSTED_ORIGINS",
        "DOMINIOS_PERMITIDOS",
        "OLLAMA_MODEL_RESUMEN",
        "EMAIL_BACKEND",
        "RESUMEN_EMAIL_DESTINATARIOS",
        "SPACY_MODEL_HOST_PATH",
        "FORCE_TRAIN",
    ]
    for clave in visibles:
        print("  %-26s %s" % (clave, valores.get(clave, "")))
    print("  %-26s (guardada, no se muestra)" % "SECRET_KEY")
    print("")
    print("Siguientes pasos:")
    print("  ./docker_setup.sh       dockerizar y arrancar (lo pide todo si falta .env)")
    print("  docker compose up -d    arrancar con lo ya configurado")
    print("  docker compose down     parar los contenedores")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Asistente interactivo que escribe el .env del proyecto.",
        epilog="Lo lanzan docker_setup.sh, install.sh e install.ps1.",
    )
    parser.add_argument(
        "--fuerza",
        action="store_true",
        help="reconfigurar aunque ya exista el .env (en interactivo)",
    )
    parser.add_argument(
        "--defaults",
        action="store_true",
        help="no preguntar: usar los valores por defecto y conservar los existentes",
    )
    parser.add_argument(
        "--salida",
        default=".env",
        help="fichero que escribir (por defecto: .env)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    ruta = Path(args.salida)

    existente = leer_env(ruta) if ruta.exists() else {}

    # Con .env existente y modo interactivo, dejamos conservarlo por defecto
    if existente and not args.fuerza and not args.defaults:
        if not preguntar_si_no("Ya existe %s; reconfigurar" % ruta, False):
            print("  Se conserva el fichero actual; no se toca nada.")
            return 0

    valores = dict(DEFECTOS)
    valores.update(existente)

    if args.defaults:
        completar_defaults(valores)
    else:
        print("")
        print("==========================================")
        print("  Configuracion del Chatbot (para Docker)")
        print("==========================================")
        print("  Pulsa Enter para aceptar el valor entre corchetes.")
        preguntar_todo(valores)

    # Variables que traiga el .env antiguo y no gestione este asistente
    extras = {k: v for k, v in existente.items() if k not in valores}

    escribir_env(ruta, valores, extras)
    resumen(ruta, valores)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Cancelado: no se ha escrito nada.")
        sys.exit(130)
