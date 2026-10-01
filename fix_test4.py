with open('test_suite.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix test_email_checklist_incompleto
old = '''def test_email_checklist_incompleto():
    from chat.models import Conversacion, Pedido, Servicio
    from notificaciones.models import _comprobar_datos_pedido, _construir_cuerpo_email
    
    c = Conversacion.objects.create(dominio="test")
    servicio = Servicio.objects.first()
    pedido = Pedido.objects.create(
        conversacion=c,
        nombre="Test",
        direccion="",
        servicio=servicio,
        presupuesto=0,
        forma_contacto=""
    )'''

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
    resumen = Resumen.objects.create(conversacion=c, tipo="compra", texto="Test")'''

content = content.replace(old, new)

# Fix test_email_sin_pedido
old2 = '''def test_email_sin_pedido():
    from chat.models import Conversacion
    from notificaciones.models import _construir_cuerpo_email
    
    c = Conversacion.objects.create(dominio="test")
    cuerpo = _construir_cuerpo_email(c, None)
    tiene_espera = "⏳" in cuerpo and "registrados aún" in cuerpo
    return tiene_espera, "Checklist ⏳ sin pedido"'''

new2 = '''def test_email_sin_pedido():
    from chat.models import Conversacion
    from notificaciones.models import _construir_cuerpo_email
    from notificaciones.models import Resumen
    
    c = Conversacion.objects.create(dominio="test")
    resumen = Resumen.objects.create(conversacion=c, tipo="compra", texto="Test")
    
    cuerpo = _construir_cuerpo_email(c, resumen)
    tiene_espera = "No hay datos de pedido registrados aún" in cuerpo
    return tiene_espera, "Checklist sin pedido OK"'''

content = content.replace(old2, new2)

with open('test_suite.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fix aplicado')