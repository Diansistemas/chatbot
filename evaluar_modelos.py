# Compara el modelo ACTUAL con el NUEVO en todas las pruebas del proyecto.
# Sirve para decidir si merece la pena hacer el swap.
import sys
import spacy

RUTA_ACTUAL = "entrenamiento/spacy/modelo/model-best"
RUTA_NUEVO = "entrenamiento/spacy/modelo_nuevo/model-best"

# (frase, intencion esperada)
CASOS_INTENCION = [
    # saludos (el bug reportado)
    ("buenos dias", "otro"),
    ("buenos dias que tal", "otro"),
    ("buenos dias solo pasaba a saludar", "otro"),
    ("buenas tardes", "otro"),
    ("buenas noches", "otro"),
    ("hola", "otro"),
    ("hola, ¿que tal?", "otro"),
    ("saludos", "otro"),
    ("un saludo", "otro"),
    ("paso a saludar", "otro"),
    ("hey", "otro"),
    ("holaaa", "otro"),
    # consulta_tecnica (test_suite)
    ("tengo un error al instalar", "consulta_tecnica"),
    ("fallo al instalar", "consulta_tecnica"),
    ("problema instalando", "consulta_tecnica"),
    ("no funciona el login", "consulta_tecnica"),
    ("la app se cierra", "consulta_tecnica"),
    # regresiones de las demas intenciones
    ("quiero un presupuesto de 5000", "compra"),
    ("necesito presupuesto para una web", "compra"),
    ("buenos dias quiero un presupuesto", "compra"),
    ("quiero hablar con un agente", "contactar_humano"),
    ("necesito un operador humano", "contactar_humano"),
    ("pasame con un agente", "contactar_humano"),
    ("acepto el presupuesto", "confirmacion"),
    ("de acuerdo, procedan", "confirmacion"),
    ("adios, gracias por todo", "cerrar"),
    ("eso es todo, hasta luego", "cerrar"),
    ("mi ordenador no arranca", "consulta_tecnica"),
]

# (frase, fragmento que debe aparecer en alguna entidad)
CASOS_NER = [
    ("Mi empresa se llama Test SL", "Test SL"),
    ("la empresa se llama Test SL, email test@test.com", "Test SL"),
    ("El precio es 1500 euros", "1500 euros"),
]


def frases_del_csv():
    """Carga los textos de entrenamiento para poder descartar los casos memorizados."""
    import csv
    try:
        with open("entrenamiento/datos/nlp_final.csv", encoding="utf-8-sig") as f:
            return {(" ".join((r["texto"] or "").lower().split()))
                    for r in csv.DictReader(f, delimiter=";")}
    except OSError:
        return set()


def evaluar(nlp):
    en_csv = frases_del_csv()
    res = {"intencion_ok": 0, "intencion_total": 0, "ner_ok": 0, "ner_total": 0,
           "gen_ok": 0, "gen_total": 0, "fallos": []}

    for frase, esperada in CASOS_INTENCION:
        d = nlp(frase)
        top = max(d.cats, key=d.cats.get)
        clave = " ".join(frase.lower().split())
        memorizada = clave in en_csv
        res["intencion_total"] += 1
        if top == esperada:
            res["intencion_ok"] += 1
        else:
            res["fallos"].append(f"INTENCION {frase!r}: esperado={esperada} obtenido={top}")
        # Generalizacion: solo cuenta los casos que NO estan en el CSV
        if not memorizada:
            res["gen_total"] += 1
            if top == esperada:
                res["gen_ok"] += 1

    for frase, fragmento in CASOS_NER:
        d = nlp(frase)
        ents = [(e.text, e.label_) for e in d.ents]
        res["ner_total"] += 1
        if any(fragmento in t for t, _ in ents):
            res["ner_ok"] += 1
        else:
            res["fallos"].append(f"NER {frase!r}: falta {fragmento!r} -> {ents}")

    return res


def main():
    modelos = {}
    for nombre, ruta in [("ACTUAL", RUTA_ACTUAL), ("NUEVO", RUTA_NUEVO)]:
        try:
            modelos[nombre] = spacy.load(ruta)
        except Exception as e:
            print(f"[AVISO] No se pudo cargar {nombre} ({ruta}): {e}")

    if not modelos:
        print("No hay ningun modelo que evaluar.")
        sys.exit(1)

    lineas = []
    resultados = {}
    for nombre, nlp in modelos.items():
        r = evaluar(nlp)
        resultados[nombre] = r
        lineas.append(f"=== MODELO {nombre} ===")
        lineas.append(f"  intencion:     {r['intencion_ok']}/{r['intencion_total']}")
        lineas.append(f"  ner:           {r['ner_ok']}/{r['ner_total']}")
        lineas.append(f"  generaliza:    {r['gen_ok']}/{r['gen_total']} (casos fuera del CSV)")
        if r["fallos"]:
            lineas.append("  FALLOS:")
            for f in r["fallos"]:
                lineas.append(f"    - {f}")
        else:
            lineas.append("  sin fallos")
        lineas.append("")

    if len(resultados) == 2:
        a, n = resultados["ACTUAL"], resultados["NUEVO"]
        total_a = a["intencion_ok"] + a["ner_ok"] + a["gen_ok"]
        total_n = n["intencion_ok"] + n["ner_ok"] + n["gen_ok"]
        lineas.append("=== VEREDICTO ===")
        lineas.append(f"  ACTUAL: {total_a} aciertos (int+ner+generalizacion)")
        lineas.append(f"  NUEVO:  {total_n} aciertos (int+ner+generalizacion)")
        lineas.append("  -> " + ("CAMBIAR a NUEVO" if total_n > total_a else
                                 "MANTENER ACTUAL" if total_n < total_a else "IGUAL"))

    texto = "\n".join(lineas)
    with open("evaluacion_modelos.txt", "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    print(texto)
    print("\nGuardado en evaluacion_modelos.txt")


if __name__ == "__main__":
    main()
