"""Comprueba como clasifica el chatbot una lista de frases de prueba.

Se clasifica a traves de core.acceso.clasificar_texto(), que es EXACTAMENTE
lo que hace la app (core.models.procesar_mensaje): el textcat corre sobre el
texto en minusculas, porque es sensible a las mayusculas ("Paso a saludar"
salia 'cerrar' mientras que "paso a saludar" salia 'otro'). Clasificar con
el modelo "pelado" (spacy.load + nlp(frase)) mediria algo distinto de lo que
ve el usuario.

Cada frase se comprueba tal cual, con la inicial en mayuscula y con la
inicial en minuscula: la intencion NO debe depender de como el usuario
escriba la primera letra.

Ejecutar desde la raiz:
    python pruebas/evaluacion/verificar_nlp.py [ruta/modelo]
"""
import os
import sys
from pathlib import Path

import django

# Raiz del proyecto: pruebas/evaluacion/ -> raiz
RAIZ = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.acceso import clasificar_texto, get_nlp

# La ruta se acepta solo por compatibilidad con la documentacion
# (docs/configuracion_entrenamiento.md): el modelo lo decide la app,
# settings.SPACY_MODEL_PATH con fallback a SPACY_MODEL_BASE.
if len(sys.argv) > 1:
    print(f"[aviso] argumento ignorado, se usa el modelo de la app: {sys.argv[1]}")

get_nlp.cache_clear()
nlp = get_nlp()

FRASES = [
    # (frase, intencion esperada)
    ("buenos dias, quiero un presupuesto", "compra"),
    ("hola buenos dias necesito un presupuesto", "compra"),
    ("necesito un presupuesto", "compra"),
    ("quiero contratar el mantenimiento anual", "compra"),
    ("me gustaria comprar el paquete basico", "compra"),
    ("hola buenos dias", "otro"),
    ("buenos dias que tal", "otro"),
    ("buenos dias solo pasaba a saludar", "otro"),
    ("hola, ¿que tal?", "otro"),
    ("Eso es todo por hoy muchas gracias", "cerrar"),
    ("Hasta luego que tengas buen dia", "cerrar"),
    ("Adios que pases buena tarde", "cerrar"),
    ("Mi conexion a internet no funciona", "consulta_tecnica"),
    ("Tengo un error al instalar el programa", "consulta_tecnica"),
    ("Quiero hablar con un agente", "contactar_humano"),
    ("Perfecto acepto el presupuesto de 150 euros", "confirmacion"),
]

# Tres variantes de cada frase: tal cual, inicial en mayuscula y en
# minuscula (sin duplicados).
PRUEBAS = {}
for frase, esperada in FRASES:
    for variante in (
        frase,
        frase[0].upper() + frase[1:],
        frase[0].lower() + frase[1:],
    ):
        PRUEBAS.setdefault(variante, esperada)
PRUEBAS = list(PRUEBAS.items())

print(f"Modelo: {nlp.meta.get('name', '?')}")
print(f"Pipeline: {nlp.pipe_names}")
print(f"Frases: {len(FRASES)} -> {len(PRUEBAS)} comprobaciones\n")

aciertos = 0
fallos = []
for frase, esperada in PRUEBAS:
    cats, _doc = clasificar_texto(nlp, frase)
    top = max(cats, key=cats.get)
    conf = cats[top]
    ok = top == esperada
    aciertos += ok
    marca = "OK " if ok else "FALLO"
    print(f"[{marca}] '{frase}' -> {top} ({conf:.3f})  esperado: {esperada}")
    if not ok:
        fallos.append((frase, top, esperada, conf))

print(f"\nResultado: {aciertos}/{len(PRUEBAS)} aciertos")
if fallos:
    print("Fallos:")
    for frase, top, esperada, conf in fallos:
        print(f"  - '{frase}': salio '{top}' (conf {conf:.3f}), esperado '{esperada}'")
sys.exit(1 if fallos else 0)
