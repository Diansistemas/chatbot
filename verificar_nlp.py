"""Comprueba como clasifica un modelo de spaCy una lista de frases de prueba."""
import sys
import spacy

RUTA_MODELO = sys.argv[1]

PRUEBAS = [
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

nlp = spacy.load(RUTA_MODELO)
print(f"Modelo: {RUTA_MODELO}")
print(f"Pipeline: {nlp.pipe_names}\n")

aciertos = 0
fallos = []
for frase, esperada in PRUEBAS:
    doc = nlp(frase)
    top = max(doc.cats, key=doc.cats.get)
    conf = doc.cats[top]
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
