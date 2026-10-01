with open('core/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = 'if datos_extraidos["servicio"] and datos_extraidos["presupuesto"]:'
new = 'if datos_extraidos["servicio"]:'
content = content.replace(old, new)

# También cambiar presupuesto
content = content.replace('presupuesto = datos_extraidos["presupuesto"]', 'presupuesto = datos_extraidos["presupuesto"] or 0')

with open('core/models.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Reemplazo completado')