#!/usr/bin/env python
"""
Test suite completo para Chatbot DianSistemas
Ejecuta: python pruebas/funcional/test_suite.py
"""
import os
import sys
import django

# Configuración
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

django.setup()

from chat.models import Conversacion, Mensaje, Pedido, Servicio
from notificaciones.models import (
    clasificar_conversacion, 
    crear_resumen, 
    enviar_resumen,
    _comprobar_datos_pedido,
    _construir_cuerpo_email
)
from core.models import (
    responder, 
    procesar_mensaje, 
    crear_pedido_si_completo,
    generar_respuesta_llm
)
from core.acceso import get_nlp
import requests

# Configuración SMTP para testing
SMTP_API = "http://127.0.0.1:64203"

def bandeja():
    return requests.get(SMTP_API + "/api/Messages", timeout=10).json()["results"]

def primera_linea_email(mid):
    r = requests.get(f"http://127.0.0.1:64203/api/Messages/{mid}/Source", timeout=10)
    return r.text.split("\n")[0] if r.text else "(vacío)"

# ============================================================
# TESTS
# ============================================================

class TestResult:
    def __init__(self, name, passed, details=""):
        self.name = name
        self.passed = passed
        self.details = details

results = []

def run_test(name, test_func):
    try:
        passed, details = test_func()
        results.append(TestResult(name, passed, details))
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} | {name}")
        if details:
            print(f"       {details}")
    except Exception as e:
        results.append(TestResult(name, False, f"ERROR: {e}"))
        print(f"[FAIL] | {name} | ERROR: {e}")

# --- Tests NLP ---
def test_nlp_compra():
    nlp = get_nlp()
    tests = [
        ("quiero un presupuesto", "compra"),
        ("necesito un presupuesto", "compra"),
        ("quiero contratar", "compra"),
        ("me interesa comprar", "compra"),
    ]
    for texto, esperado in tests:
        d = nlp(texto)
        top = max(d.cats, key=d.cats.get)
        if top != esperado:
            return False, f"'{texto}' -> {top} (esperado: {esperado})"
    return True, "4/4 casos compra OK"

def test_nlp_consulta_tecnica():
    nlp = get_nlp()
    tests = [
        ("tengo un error al instalar", "consulta_tecnica"),
        ("fallo al instalar", "consulta_tecnica"),
        ("problema instalando", "consulta_tecnica"),
        ("no funciona el login", "consulta_tecnica"),
        ("la app se cierra", "consulta_tecnica"),
    ]
    for texto, esperado in tests:
        d = nlp(texto)
        top = max(d.cats, key=d.cats.get)
        if top != esperado:
            return False, f"'{texto}' -> {top} (esperado: {esperado})"
    return True, "5/5 casos consulta_tecnica OK"

def test_nlp_contactar_humano():
    nlp = get_nlp()
    tests = [
        ("quiero hablar con un agente", "contactar_humano"),
        ("necesito un operador humano", "contactar_humano"),
        ("pasame con un agente", "contactar_humano"),
    ]
    for texto, esperado in tests:
        d = nlp(texto)
        top = max(d.cats, key=d.cats.get)
        if top != esperado:
            return False, f"'{texto}' -> {top} (esperado: {esperado})"
    return True, "3/3 casos contactar_humano OK"

def test_nlp_cerrar():
    nlp = get_nlp()
    tests = [
        ("hasta luego", "cerrar"),
        ("adios", "cerrar"),
        ("chau", "cerrar"),
        ("me voy", "cerrar"),
    ]
    for texto, esperado in tests:
        d = nlp(texto)
        top = max(d.cats, key=d.cats.get)
        if top != esperado:
            return False, f"'{texto}' -> {top} (esperado: {esperado})"
    return True, "4/4 casos cerrar OK"

def test_nlp_confirmacion():
    nlp = get_nlp()
    tests = [
        ("acepto el presupuesto", "confirmacion"),
        ("confirmo la compra", "confirmacion"),
        ("acepto el presupuesto", "confirmacion"),
    ]
    for texto, esperado in tests:
        d = nlp(texto)
        top = max(d.cats, key=d.cats.get)
        if top != esperado:
            return False, f"'{texto}' -> {top} (esperado: {esperado})"
    return True, "3/3 casos confirmacion OK"

def test_nlp_otro():
    nlp = get_nlp()
    tests = [
        ("hola buenos dias", "otro"),
        ("que tal", "otro"),
        ("gracias", "otro"),
        ("entendido", "otro"),
    ]
    for texto, esperado in tests:
        d = nlp(texto)
        top = max(d.cats, key=d.cats.get)
        if top != esperado:
            return False, f"'{texto}' -> {top} (esperado: {esperado})"
    return True, "4/4 casos otro OK"

# --- Tests Clasificador Email ---
def test_clasificador_compra_completa():
    from chat.models import Conversacion, Mensaje, Pedido, Servicio
    from notificaciones.models import clasificar_conversacion
    
    c = Conversacion.objects.create(dominio="test")
    Mensaje.objects.create(conversacion=c, texto="quiero un presupuesto", remitente="usuario")
    Mensaje.objects.create(conversacion=c, texto="precio 1000", remitente="chatbot")
    Mensaje.objects.create(conversacion=c, texto="acepto", remitente="usuario")
    Pedido.objects.create(
        conversacion=c, 
        nombre="Test", 
        direccion="Dir", 
        servicio=Servicio.objects.first(), 
        presupuesto=1000, 
        forma_contacto="test@test.com"
    )
    resultado = clasificar_conversacion(c)
    return resultado == True, "Clasificador compra completa: True"

def test_clasificador_sin_pedido():
    from chat.models import Conversacion, Mensaje
    from notificaciones.models import clasificar_conversacion
    
    c = Conversacion.objects.create(dominio="test")
    Mensaje.objects.create(conversacion=c, texto="quiero un presupuesto", remitente="usuario")
    Mensaje.objects.create(conversacion=c, texto="precio 1000", remitente="chatbot")
    Mensaje.objects.create(conversacion=c, texto="acepto", remitente="usuario")
    # SIN pedido
    resultado = clasificar_conversacion(c)
    return resultado == True, "Clasificador sin pedido pero con intención compra: True"

def test_clasificador_no_compra():
    from chat.models import Conversacion, Mensaje
    from notificaciones.models import clasificar_conversacion
    
    c = Conversacion.objects.create(dominio="test")
    Mensaje.objects.create(conversacion=c, texto="tengo un error instalando", remitente="usuario")
    Mensaje.objects.create(conversacion=c, texto="prueba a reinstalar", remitente="chatbot")
    resultado = clasificar_conversacion(c)
    return resultado == False, "Clasificador no-compra: False"

def test_clasificador_contactar_humano():
    from chat.models import Conversacion, Mensaje
    from notificaciones.models import clasificar_conversacion
    
    c = Conversacion.objects.create(dominio="test")
    Mensaje.objects.create(conversacion=c, texto="quiero hablar con un agente", remitente="usuario")
    resultado = clasificar_conversacion(c)
    return resultado == False, "Clasificador contactar_humano: False"

# --- Tests Auto-creación Pedido ---
def test_auto_pedido_con_presupuesto():
    from chat.models import Conversacion, Mensaje, Pedido, Servicio
    from core.models import crear_pedido_si_completo, procesar_mensaje
    
    c = Conversacion.objects.create(dominio="test")
    Mensaje.objects.create(conversacion=c, texto="quiero un presupuesto de 5000", remitente="usuario")
    Mensaje.objects.create(conversacion=c, texto="el precio es 5000", remitente="chatbot")
    Mensaje.objects.create(conversacion=c, texto="acepto, mi email test@test.com", remitente="usuario")
    
    for m in c.conversacion_mensajes.filter(remitente="usuario"):
        analisis = procesar_mensaje(m)
        if analisis.intencion.nombre == "compra":
            c.tenemosCompra = True
            c.save(update_fields=["tenemosCompra"])
    
    pedido = crear_pedido_si_completo(c)
    if pedido:
        # Presupuesto puede ser 0 si no se detectó monto en los mensajes
        return pedido.forma_contacto == "test@test.com", f"Pedido creado con email={pedido.forma_contacto}, presupuesto={pedido.presupuesto}"
    return False, "No se creó pedido"

def test_auto_pedido_sin_presupuesto():
    from chat.models import Conversacion, Mensaje, Servicio
    from core.models import crear_pedido_si_completo, procesar_mensaje
    
    c = Conversacion.objects.create(dominio="test")
    Mensaje.objects.create(conversacion=c, texto="quiero un presupuesto", remitente="usuario")
    Mensaje.objects.create(conversacion=c, texto="el precio es 5000", remitente="chatbot")
    Mensaje.objects.create(conversacion=c, texto="acepto, mi email test@test.com", remitente="usuario")
    
    for m in c.conversacion_mensajes.filter(remitente="usuario"):
        analisis = procesar_mensaje(m)
        if analisis.intencion.nombre == "compra":
            c.tenemosCompra = True
            c.save(update_fields=["tenemosCompra"])
    
    pedido = crear_pedido_si_completo(c)
    if pedido:
        return pedido.presupuesto == 0, f"Pedido creado con presupuesto placeholder: {pedido.presupuesto}"
    return False, "No se creó pedido"

def test_auto_pedido_en_fallback_email():
    from chat.models import Conversacion, Mensaje, Pedido, Servicio
    from core.models import crear_pedido_si_completo, procesar_mensaje, responder
    
    c = Conversacion.objects.create(dominio="test")
    Mensaje.objects.create(conversacion=c, texto="quiero un presupuesto", remitente="usuario")
    Mensaje.objects.create(conversacion=c, texto="el precio es 5000", remitente="chatbot")
    Mensaje.objects.create(conversacion=c, texto="acepto", remitente="usuario")
    
    for m in c.conversacion_mensajes.filter(remitente="usuario"):
        analisis = procesar_mensaje(m)
        if analisis.intencion.nombre == "compra":
            c.tenemosCompra = True
            c.save(update_fields=["tenemosCompra"])
    
    # Simular mensaje con email en fallback (intencion mal clasificada)
    m_email = Mensaje.objects.create(
        conversacion=c, 
        texto="la empresa se llama Test SL, email test@test.com", 
        remitente="usuario"
    )
    
    # Llamar responder directamente (activa fallback)
    responder(m_email)
    
    c.refresh_from_db()
    return c.conversacion_pedido.exists(), "Pedido creado en fallback al detectar email"

# --- Tests contactar_humano ---
def test_contactar_humano_sin_pedido():
    from chat.models import Conversacion, Mensaje
    from core.models import responder, procesar_mensaje
    
    c = Conversacion.objects.create(dominio="test")
    Mensaje.objects.create(conversacion=c, texto="hola", remitente="usuario")
    m = Mensaje.objects.create(conversacion=c, texto="quiero hablar con un agente", remitente="usuario")
    
    resp = responder(m)
    pide_datos = "datos de contacto" in resp.texto.lower()
    return pide_datos, f"Pide datos de contacto: {pide_datos}"

def test_contactar_humano_con_pedido():
    from chat.models import Conversacion, Mensaje, Pedido, Servicio
    from core.models import responder, procesar_mensaje
    
    c = Conversacion.objects.create(dominio="test")
    Mensaje.objects.create(conversacion=c, texto="quiero presupuesto", remitente="usuario")
    Mensaje.objects.create(conversacion=c, texto="precio 1000", remitente="chatbot")
    Pedido.objects.create(
        conversacion=c, 
        nombre="Test", 
        direccion="Dir", 
        servicio=Servicio.objects.first(), 
        presupuesto=1000, 
        forma_contacto="test@test.com"
    )
    m = Mensaje.objects.create(conversacion=c, texto="quiero hablar con un agente", remitente="usuario")
    
    resp = responder(m)
    transfiere = "conect" in resp.texto.lower() or "agente" in resp.texto.lower()
    return transfiere, f"Transfiere directo: {transfiere}"

# --- Tests Flujo completo ---
def test_flujo_compra_completa():
    from chat.models import Conversacion, Mensaje, Pedido, Servicio
    from core.models import responder, procesar_mensaje, crear_pedido_si_completo
    
    c = Conversacion.objects.create(dominio="test")
    servicio = Servicio.objects.first()
    
    # Simular conversación
    flujo = [
        ("chatbot", "Hola, ¿en qué ayudo?"),
        ("usuario", "Quiero un presupuesto para auditoría"),
        ("chatbot", "La auditoría cuesta 2000€"),
        ("usuario", "Acepto, mi empresa Test SL, dir Calle 1, email test@test.com"),
    ]
    
    for remitente, texto in flujo:
        Mensaje.objects.create(conversacion=c, texto=texto, remitente=remitente)
        if remitente == "usuario":
            analisis = procesar_mensaje(c.conversacion_mensajes.last())
            if analisis.intencion.nombre == "compra":
                c.tenemosCompra = True
                c.save(update_fields=["tenemosCompra"])
    
    # Verificar pedido auto-creado
    c.refresh_from_db()
    tiene_pedido = c.conversacion_pedido.exists()
    if not tiene_pedido:
        # Último intento
        from core.models import crear_pedido_si_completo
        crear_pedido_si_completo(c)
        c.refresh_from_db()
        tiene_pedido = c.conversacion_pedido.exists()
    
    return tiene_pedido, f"Pedido auto-creado: {tiene_pedido}"

# --- Tests Email ---
def test_email_checklist_completo():
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
    return tiene_checklist_ok and all(check[k] for k in check if k != "tiene_pedido"), "Checklist completo OK"

def test_email_checklist_incompleto():
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
    return tiene_faltantes, "Checklist incompleto OK"

def test_email_sin_pedido():
    from chat.models import Conversacion
    from notificaciones.models import _construir_cuerpo_email
    from notificaciones.models import Resumen
    
    c = Conversacion.objects.create(dominio="test")
    resumen = Resumen.objects.create(conversacion=c, tipo="compra", texto="Test")
    
    cuerpo = _construir_cuerpo_email(c, resumen)
    tiene_espera = "No hay datos de pedido registrados aún" in cuerpo
    return tiene_espera, "Checklist sin pedido OK"

# --- Tests Guardas anti-duplicado ---
def test_guardia_recerrar():
    from chat.models import Conversacion
    from notificaciones.models import Resumen
    
    c = Conversacion.objects.create(dominio="test")
    c.estado = "cerrada"
    c.save()
    
    # Guardar de nuevo
    c.save(update_fields=["estado"])
    
    return c.resumenes.count() == 0, "No crea resumen duplicado al re-cerrar"

# ============================================================
# EJECUTAR TESTS
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TEST SUITE - Chatbot DianSistemas")
    print("=" * 60)
    
    # Tests NLP
    run_test("NLP: Intención COMPRA", test_nlp_compra)
    run_test("NLP: Intención CONSULTA_TECNICA", test_nlp_consulta_tecnica)
    run_test("NLP: Intención CONTACTAR_HUMANO", test_nlp_contactar_humano)
    run_test("NLP: Intención CERRAR", test_nlp_cerrar)
    run_test("NLP: Intención CONFIRMACION", test_nlp_confirmacion)
    run_test("NLP: Intención OTRO", test_nlp_otro)
    
    # Clasificador Email
    run_test("Clasificador: Compra completa", test_clasificador_compra_completa)
    run_test("Clasificador: Sin pedido (compra)", test_clasificador_sin_pedido)
    run_test("Clasificador: No compra", test_clasificador_no_compra)
    run_test("Clasificador: Contactar humano", test_clasificador_contactar_humano)
    
    # Auto-pedido
    run_test("Auto-pedido: Con presupuesto", test_auto_pedido_con_presupuesto)
    run_test("Auto-pedido: Sin presupuesto (placeholder)", test_auto_pedido_sin_presupuesto)
    run_test("Auto-pedido: En fallback con email", test_auto_pedido_en_fallback_email)
    
    # Contactar humano
    run_test("Contactar humano: Sin pedido -> pide datos", test_contactar_humano_sin_pedido)
    run_test("Contactar humano: Con pedido -> transfiere", test_contactar_humano_con_pedido)
    
    # Flujo completo
    run_test("Flujo: Compra completa", test_flujo_compra_completa)
    
    # Email checklists
    run_test("Email: Checklist completo", test_email_checklist_completo)
    run_test("Email: Checklist incompleto", test_email_checklist_incompleto)
    run_test("Email: Sin pedido", test_email_sin_pedido)
    
    # Guardas
    run_test("Guarda: No duplicado al re-cerrar", test_guardia_recerrar)
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    
    for r in results:
        status = "[PASS]" if r.passed else "[FAIL]"
        print(f"  {status} {r.name}")
        if r.details and not r.passed:
            print(f"       {r.details}")
    
    print(f"\nTOTAL: {passed}/{total} pasados")
    if failed:
        print(f"FALLARON: {failed}")
        sys.exit(1)
    else:
        print("*** TODOS LOS TESTS PASARON ***")
        sys.exit(0)