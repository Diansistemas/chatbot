# Verifica que los saludos ya NO se clasifican como compra
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.acceso import get_nlp

get_nlp.cache_clear()
nlp = get_nlp()

CASOS = [
    # (frase, intencion esperada)
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
    # Regresiones: no deben romperse
    ("quiero un presupuesto de 5000", "compra"),
    ("necesito presupuesto para una web", "compra"),
    ("buenos dias quiero un presupuesto", "compra"),
    ("mi ordenador no arranca", "consulta_tecnica"),
    ("quiero hablar con un agente", "contactar_humano"),
    ("acepto el presupuesto", "confirmacion"),
    ("adios, gracias por todo", "cerrar"),
]

salida = []
pasados = 0
for frase, esperada in CASOS:
    doc = nlp(frase)
    top = max(doc.cats.items(), key=lambda kv: kv[1])
    ok = top[0] == esperada
    pasados += ok
    salida.append(
        f"[{'PASS' if ok else 'FAIL'}] {frase!r}\n"
        f"       esperado={esperada} obtenido={top[0]} ({top[1]:.3f}) | "
        + ", ".join(f"{k}={v:.2f}" for k, v in sorted(doc.cats.items(), key=lambda kv: -kv[1])[:3])
    )

with open("verificacion_saludos.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(salida) + f"\n\nTOTAL: {pasados}/{len(CASOS)} pasados\n")

print(f"TOTAL: {pasados}/{len(CASOS)} pasados -> verificacion_saludos.txt")
