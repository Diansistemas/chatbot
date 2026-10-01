"""Verificacion dirigida de la ronda 8: casos que fallaban + regresiones.

Esperado:
  - texto normal -> intencion exacta
  - "<>cerrar"   -> cualquier cosa MENOS cerrar (familia OOD que cerraba)
"""
import os
import sys

import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # entrenamiento/evaluacion -> raiz
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from core.acceso import get_nlp  # noqa: E402

CASOS = [
    # --- familia disponibilidad/turnos (ANTES: cerrar)
    ("Hola buenos dias, tiene algun turno libre", "<>cerrar"),
    ("¿Que turnos tienen libres?", "<>cerrar"),
    ("Quiero saber si hay citas disponibles para manana", "<>cerrar"),
    ("¿A que hora se abre por la manana?", "<>cerrar"),
    # --- familia chitchat/descarga (ANTES: cerrar en el dev)
    ("Me duele la cabeza desde ayer", "otro"),
    ("Mi jefe no me deja salir temprano", "otro"),
    ("Ok perfecto gracias", "otro"),
    ("Me duele mucho la cabeza desde hace dos dias", "otro"),
    ("Vale, muchas gracias por toda la ayuda", "otro"),
    # --- familia reclamacion (ANTES: compra)
    ("Quiero devolver el dinero que pague", "otro"),
    ("Me han cobrado dos veces la factura", "otro"),
    ("Me han cobrado de mas y quiero el reembolso", "otro"),
    # --- familia FACTURA / justificante (RONDAS 8->9: iba a compra 0.99)
    ("Necesito la factura del mes pasado", "otro"),
    ("¿Me pueden enviar la factura de este mes?", "otro"),
    ("No entiendo el importe que aparece en la factura", "otro"),
    ("Necesito un justificante de pago del ultimo mes", "otro"),
    ("¿Pueden reenviarme la factura por correo?", "otro"),
    # --- regresiones: lo que YA funcionaba debe seguir igual
    ("Quiero contratar el plan basico por 30 euros", "compra"),
    ("Cuanto tarda la revision general", "consulta_tecnica"),
    ("Hasta luego que tengas buen dia", "cerrar"),
    ("Pasame con un supervisor por favor", "contactar_humano"),
    ("Confirmo el presupuesto de 200 euros", "confirmacion"),
    ("¿Hay disponibilidad para la revision general?", "consulta_tecnica"),
]


def main():
    nlp = get_nlp()
    print(f"modelo: {sys.modules['django.conf'].settings.SPACY_MODEL_PATH}")
    print(f"{'FAMILIA/TEXTO':58} {'OBTENIDO':18} conf  esperado")
    print("-" * 100)
    aciertos = fallos = 0
    for texto, esperado in CASOS:
        doc = nlp(texto)
        top = max(doc.cats, key=doc.cats.get)
        conf = doc.cats[top]
        if esperado == "<>cerrar":
            ok = top != "cerrar"
            espera_txt = "NO cerrar"
        else:
            ok = top == esperado
            espera_txt = esperado
        aciertos += ok
        fallos += not ok
        marca = "OK  " if ok else "FALL"
        if not ok:
            print(f"[{marca}] {texto[:56]:58} {top:18} {conf:.2f}  {esperado}")
        else:
            print(f"[{marca}] {texto[:56]:58} {top:18} {conf:.2f}  {esperado}")
    print("-" * 100)
    print(f"RESULTADO: {aciertos}/{len(CASOS)} correctos, {fallos} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
