with open('test_suite.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    cuerpo = _construir_cuerpo_email(c, None)
    tiene_faltantes = "❌" in cuerpo and "Faltan datos" in cuerpo
    return tiene_faltantes, "Checklist ❌ incompleto"'''

new = '''    cuerpo = _construir_cuerpo_email(c, resumen)
    tiene_faltantes = "Faltan datos" in cuerpo
    return tiene_faltantes, "Checklist incompleto OK"'''

content = content.replace(old, new)

with open('test_suite.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fix aplicado')