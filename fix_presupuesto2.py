with open('core/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = 'forma_contacto = datos_extraidos["forma_contacto"] or "Por facilitar"\n        \n        try:'
new = 'forma_contacto = datos_extraidos["forma_contacto"] or "Por facilitar"\n        presupuesto = datos_extraidos["presupuesto"] or 0\n        \n        try:'
content = content.replace(old, new)

with open('core/models.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Reemplazo completado')