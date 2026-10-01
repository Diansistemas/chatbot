with open('test_suite.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix test_email_checklist_completo
old = '''def test_email_checklist_completo():
    from chat.models import Conversacion, Mensaje, Pedido, Servicio
    from notificaciones.models import _comprobar_datos_pedido, _construir_cuerpo_email
    
    c = Conversacion.objects.create(dominio="test")
    servicio = Servicio.objects.first()
    pedido = Pedido.objects.create(
        conversacion=c,
        nombre="Test",
        direccion="Dir",
        servicio=servicio,
        presupuesto=1000,
        forma_contacto="test@test.com"
    )
    
    check = _comprobar_datos_pedido(c)
    cuerpo = _construir_cuerpo_email(c, None)  # resumen dummy
    
    tiene_checklist_ok = "✅" in cuerpo and "completos" in cuerpo
    return tiene_checklist_ok and all(check[k] for k in check if k != "tiene_pedido"), "Checklist ✅ completo"'''

new = '''def test_email_checklist_completo():
    from chat.models import Conversacion, Mensaje, Pedido, Servicio
    from notificaciones.models import _comprobar_datos_pedido, _construir_cuerpo_email
    from notificaciones.models import Resumen
    
    c = Conversacion.objects.create(dominio="test")
    servicio = Servicio.objects.first()
    pedido = Pedido.objects.create(
        conversacion=c,
        nombre="Test",
        direccion="Dir",
        servicio=servicio,
        presupuesto=1000,
        forma_contacto="test@test.com"
    )
    resumen = Resumen.objects.create(conversacion=c, tipo="compra", texto="Test")
    
    check = _comprobar_datos_pedido(c)
    cuerpo = _construir_cuerpo_email(c, resumen)
    
    tiene_checklist_ok = "Todos los datos del pedido están completos" in cuerpo
    return tiene_checklist_ok and all(check[k] for k in check if k != "tiene_pedido"), "Checklist completo OK"'''

content = content.replace(old, new)

with open('test_suite.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fix aplicado')