"""
Evaluacion del LLM (modelos de Ollama) entrenados con llm.csv.

Para cada ejemplo de evaluacion:
  1. Envia texto_usuario al modelo que le corresponde (via MAPEO_INTENCION_MODELO)
  2. Compara la respuesta con el texto_chatbot esperado
  3. Calcula similitud (difflib) y solapamiento de palabras clave

Metricas globales y desglosadas por etiqueta de modelo.

Uso:
    python entrenamiento/evaluacion/evaluar_llm.py
    python entrenamiento/evaluacion/evaluar_llm.py --csv otra_ruta.csv --umbral 0.3
"""
import argparse
import csv
import difflib
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

# --------------------------------------------------------------------------
# Configuracion
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CSV_POR_DEFECTO = BASE_DIR / "entrenamiento" / "datos" / "llm.csv"
OLLAMA_HOST = "http://localhost:11434"
TIMEOUT = 60

# Mapeo intencion -> etiqueta de modelo (misma fuente que core.acceso)
MAPEO_INTENCION_MODELO = {
    "compra": "compra",
    "consulta_tecnica": "consulta",
    "confirmacion": "otro",
    "cerrar": "otro",
    "contactar_humano": "otro",
    "solicitar_agente": "otro",
    "otro": "otro",
}

# Stopwords espanol/ingles para no inflar el solapamiento de palabras
STOPWORDS = set(
    """el la los las un una unos unas de del al a o u y e en con por para para
    que se lo le les mi tu su nuestro vuestro es son sera sido hay no si
    como mas mas muy ya tambien este esta estos estas ese esa eso aquel
    te me nos the a an of to in on for is are with and or""".split()
)


def modelo_para(intencion: str) -> str:
    etiqueta = MAPEO_INTENCION_MODELO.get(intencion, "otro")
    return f"chatbot-{etiqueta}"


def limpiar(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r"[¿?¡!.,;:()\[\]{}\"']", " ", texto)
    return texto


def palabras(texto: str) -> set:
    return {p for p in limpiar(texto).split() if p and p not in STOPWORDS}


def similitud(esperado: str, obtenido: str) -> float:
    """Ratio de difflib sobre textos normalizados (0..1)."""
    a = " ".join(sorted(palabras(esperado)))
    b = " ".join(sorted(palabras(obtenido)))
    return difflib.SequenceMatcher(None, a, b).ratio()


def solapamiento(esperado: str, obtenido: str) -> float:
    """Jaccard sobre palabras con contenido (0..1)."""
    pa, pb = palabras(esperado), palabras(obtenido)
    if not pa:
        return 0.0
    return len(pa & pb) / len(pa)


def llamar_modelo(modelo: str, texto: str) -> tuple:
    """Devuelve (respuesta, error)."""
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": modelo,
                "messages": [{"role": "user", "content": texto}],
                "stream": False,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip(), None
    except Exception as error:  # noqa: BLE001 - queremos capturarlo todo
        return "", error


def cargar_casos(ruta: Path) -> list:
    with ruta.open(encoding="utf-8-sig") as f:
        return [fila for fila in csv.DictReader(f, delimiter=";") if fila.get("texto_usuario")]


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalua los modelos LLM de Ollama")
    parser.add_argument("--csv", default=str(CSV_POR_DEFECTO))
    parser.add_argument("--umbral", type=float, default=0.30,
                        help="Similitud minima para dar el caso por OK (default 0.30)")
    args = parser.parse_args()

    casos = cargar_casos(Path(args.csv))
    if not casos:
        print(f"No hay casos de evaluacion en {args.csv}")
        return 1

    print(f"Evaluando {len(casos)} casos contra {OLLAMA_HOST} (umbral={args.umbral:.2f})")
    print("=" * 78)

    resultados = []
    por_etiqueta = defaultdict(list)
    errores = 0
    inicio = time.monotonic()

    for i, caso in enumerate(casos, 1):
        intencion = caso["intencion"].strip()
        esperado = caso["texto_chatbot"].strip()
        texto_usuario = caso["texto_usuario"].strip()
        modelo = modelo_para(intencion)

        t0 = time.monotonic()
        obtenido, error = llamar_modelo(modelo, texto_usuario)
        dt = time.monotonic() - t0

        if error:
            errores += 1
            sim, sol = 0.0, 0.0
            estado = "ERROR"
        else:
            sim = similitud(esperado, obtenido)
            sol = solapamiento(esperado, obtenido)
            estado = "OK" if sim >= args.umbral else "FALLA"

        etiqueta = MAPEO_INTENCION_MODELO.get(intencion, "otro")
        resultados.append({
            "intencion": intencion, "etiqueta": etiqueta, "modelo": modelo,
            "sim": sim, "sol": sol, "estado": estado, "tiempo": dt,
            "esperado": esperado, "obtenido": obtenido,
        })
        por_etiqueta[etiqueta].append(resultados[-1])

        print(f"[{i:2d}/{len(casos)}] {estado:6s} sim={sim:.2f} sol={sol:.2f} "
              f"{dt:5.1f}s [{modelo}] ({intencion})")
        if estado != "OK":
            print(f"         usuario:  {texto_usuario}")
            print(f"         esperado: {esperado}")
            print(f"         obtenido: {obtenido[:200]}")

    total = time.monotonic() - inicio

    # ------------------------------------------------------------------
    # Informe
    # ------------------------------------------------------------------
    sims = [r["sim"] for r in resultados]
    sols = [r["sol"] for r in resultados]
    ok = sum(1 for r in resultados if r["estado"] == "OK")

    print()
    print("=" * 78)
    print("RESUMEN GLOBAL")
    print("=" * 78)
    print(f"Casos evaluados      : {len(resultados)}")
    print(f"Respuestas con error : {errores}")
    print(f"Casos OK (sim>=umbral): {ok} ({100 * ok / len(resultados):.1f}%)")
    print(f"Similitud media      : {sum(sims) / len(sims):.3f}")
    print(f"Solapamiento media   : {sum(sols) / len(sols):.3f}")
    print(f"Tiempo total         : {total:.1f}s (media {total / len(resultados):.1f}s/caso)")

    print()
    print("=" * 78)
    print("POR ETIQUETA DE MODELO")
    print("=" * 78)
    print(f"{'etiqueta':12s} {'casos':>5s} {'OK':>5s} {'sim media':>9s} {'sol media':>9s}")
    for etiqueta, grup in sorted(por_etiqueta.items()):
        gsims = [r["sim"] for r in grup]
        gsols = [r["sol"] for r in grup]
        gok = sum(1 for r in grup if r["estado"] == "OK")
        print(f"{etiqueta:12s} {len(grup):5d} {gok:5d} "
              f"{sum(gsims) / len(gsims):9.3f} {sum(gsols) / len(gsols):9.3f}")

    print()
    print("=" * 78)
    print("POR INTENCION")
    print("=" * 78)
    por_int = defaultdict(list)
    for r in resultados:
        por_int[r["intencion"]].append(r)
    print(f"{'intencion':18s} {'casos':>5s} {'OK':>5s} {'sim media':>9s}")
    for intencion, grup in sorted(por_int.items()):
        gsims = [r["sim"] for r in grup]
        gok = sum(1 for r in grup if r["estado"] == "OK")
        print(f"{intencion:18s} {len(grup):5d} {gok:5d} {sum(gsims) / len(gsims):9.3f}")

    print()
    print(f"VEREDICTO: {ok}/{len(resultados)} casos por encima del umbral "
          f"({100 * ok / len(resultados):.1f}%)")
    return 0 if errores == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
