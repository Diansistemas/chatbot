with open('test_suite.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''def test_email_checklist_incompleto():
    from chat.models import Conversacion, Pedido, Servicio
    from notificaciones.models import _comprobar_datos_pedido, _construir_cuerpo_email
    from notificaciones.models import Resumen
    
    c = Conversacion.objects.create(dominio="test")
    servicio = Servicio.objects.first()
    pedido = Pedido.objects.create(
        conversacion=c,
        nombre="Test",
        direccion="",
        servicio=servicio,
        presupuesto=0,
        forma_contacto=""
    )
    resumen = Resumen.objects.create(conversacion=c, tipo="compra", texto="Test")
    
    cuerpo = _construir_cuerpo_email(c, None)
    tiene_faltantes = "Faltan datos" in cuerpo
    return tiene_faltantes, "Checklist incompleto OK"'''

new = '''def test_email_checklist_incompleto():
    from chat.models import Conversacion, Pedido, Servicio
    from notificaciones.models import _comprobar_datos_pedido, _construir_cuerpo_email
    from notificaciones.models import Resumen
    
    c = Conversacion.objects.create(dominio="test")
    servicio = Servicio.objects.first()
    pedido = Pedido.objects.create(
        conversacion=c,
        nombre="Test",
        direccion="",
        servicio=servicio,
        presupuesto=0,
        forma_contacto=""
    )
    resumen = Resumen.objects.create(conversacion=c, tipo="compra", texto="Test")
    
    cuerpo = _construir_cuerpo_email(c, resumen)
    tiene_faltantes = "Faltan datos" in cuerpo
    return tiene_faltantes, "Checklist incompleto OK"'''

content = content.replace(old, new)

with open('test_suite.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fix aplicado')