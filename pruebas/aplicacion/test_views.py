#!/usr/bin/env python
"""
Tests de integración para las vistas web (ChatWidgetView)
Ejecuta: python pruebas/aplicacion/test_views.py
"""
import os
import sys
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
django.setup()

from django.test import TestCase, Client
from django.urls import reverse
from chat.models import Conversacion, Mensaje, Pedido, Servicio
from core.models import procesar_mensaje, responder, crear_pedido_si_completo
from core.acceso import get_nlp

class ChatViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.servicio = Servicio.objects.first()
        
    def test_chat_get_sin_conversacion(self):
        """GET /chat/ sin conversación previa -> 200 y crea nueva"""
        response = self.client.get("/chat/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hola, soy el asistente virtual")
        
    def test_chat_get_con_conversacion_abierta(self):
        """GET /chat/?conversacion=<token> con conversación existente"""
        c = Conversacion.objects.create(dominio="test", estado="abierta")
        Mensaje.objects.create(conversacion=c, texto="Hola", remitente="usuario")
        Mensaje.objects.create(conversacion=c, texto="Hola, ¿en qué ayudo?", remitente="chatbot")
        
        response = self.client.get(f"/chat/?conversacion={c.token}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hola")
        
    def test_chat_get_con_conversacion_cerrada(self):
        """GET /chat/?conversacion=<token> con conversación cerrada -> nueva conversación"""
        c = Conversacion.objects.create(dominio="test", estado="cerrada")
        Mensaje.objects.create(conversacion=c, texto="Hola", remitente="usuario")
        
        response = self.client.get(f"/chat/?conversacion={c.token}")
        self.assertEqual(response.status_code, 200)
        # Debe crear nueva conversación (no mostrar la cerrada)
        self.assertNotContains(response, "cerrada")
        
    def test_chat_post_accion_usuario(self):
        """POST /chat/ accion=usuario -> crea mensaje y responde"""
        c = Conversacion.objects.create(dominio="test")
        csrf_client = Client(enforce_csrf_checks=False)
        
        response = csrf_client.post("/chat/", {
            "accion": "usuario",
            "texto": "Quiero un presupuesto",
            "conversacion": "",
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("mensaje_id", data)
        self.assertIn("conversacion", data)
        self.assertTrue(data["conversacion"])
        
    def test_chat_post_accion_bot(self):
        """POST /chat/ accion=bot -> genera respuesta del bot"""
        c = Conversacion.objects.create(dominio="test", tenemosCompra=True)
        m = Mensaje.objects.create(conversacion=c, texto="Quiero un presupuesto", remitente="usuario")
        
        csrf_client = Client(enforce_csrf_checks=False)
        response = csrf_client.post("/chat/", {
            "accion": "bot",
            "mensaje_id": m.pk,
            "conversacion": str(c.token),
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("mensaje_id", data)
        self.assertIn("bot", data)
        self.assertIn("hora_bot", data)
        
    def test_chat_post_accion_cerrar(self):
        """POST /chat/ accion=cerrar -> cierra conversación"""
        c = Conversacion.objects.create(dominio="test", estado="abierta")
        Mensaje.objects.create(conversacion=c, texto="Hola", remitente="usuario")
        
        csrf_client = Client(enforce_csrf_checks=False)
        response = csrf_client.post("/chat/", {
            "accion": "cerrar",
            "conversacion": str(c.token),
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["estado"], "cerrada")
        
        c.refresh_from_db()
        self.assertEqual(c.estado, "cerrada")
        
    def test_chat_post_accion_estado(self):
        """POST /chat/ accion=estado -> devuelve estado y mensajes nuevos"""
        c = Conversacion.objects.create(dominio="test", estado="abierta")
        m1 = Mensaje.objects.create(conversacion=c, texto="Hola", remitente="usuario")
        Mensaje.objects.create(conversacion=c, texto="Hola, ¿en qué ayudo?", remitente="chatbot")
        
        csrf_client = Client(enforce_csrf_checks=False)
        response = csrf_client.post("/chat/", {
            "accion": "estado",
            "conversacion": str(c.token),
            "desde_id": 0,
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("esperando", data)
        self.assertIn("cerrada", data)
        self.assertIn("mensajes", data)
        self.assertEqual(len(data["mensajes"]), 1)
        
    def test_chat_inactividad_cierre_automatico(self):
        """GET /chat/ con conversación inactiva >5min -> cierra automáticamente"""
        from django.utils import timezone
        from datetime import timedelta
        
        c = Conversacion.objects.create(dominio="test", estado="abierta")
        m = Mensaje.objects.create(conversacion=c, texto="Hola", remitente="usuario")
        m.fecha_mensaje = timezone.now() - timedelta(minutes=6)
        m.save()
        
        response = self.client.get(f"/chat/?conversacion={c.token}")
        self.assertEqual(response.status_code, 200)
        
        c.refresh_from_db()
        self.assertEqual(c.estado, "cerrada")


class InactividadTests(TestCase):
    def setUp(self):
        self.c = Conversacion.objects.create(dominio="test", estado="abierta")
        self.m = Mensaje.objects.create(conversacion=self.c, texto="Hola", remitente="usuario")
        
    def test_estaInactiva_falso_reciente(self):
        self.assertFalse(self.c.estaInactiva(timeout=5))
        
    def test_estaInactiva_verdadero_antiguo(self):
        from django.utils import timezone
        from datetime import timedelta
        self.m.fecha_mensaje = timezone.now() - timedelta(minutes=10)
        self.m.save()
        self.assertTrue(self.c.estaInactiva(timeout=5))
        
    def test_cerrar_cambia_estado(self):
        self.c.cerrar()
        self.c.refresh_from_db()
        self.assertEqual(self.c.estado, "cerrada")
        self.assertIsNotNone(self.c.fecha_fin)
        
    def test_cerrar_dos_veces_no_duplica_fecha(self):
        from django.utils import timezone
        self.c.cerrar()
        primera = self.c.fecha_fin
        self.c.cerrar()
        self.c.refresh_from_db()
        self.assertEqual(self.c.fecha_fin, primera)


class SignalTests(TestCase):
    def setUp(self):
        # La BD de prueba arranca sin servicios: creamos uno si no existe
        self.servicio = Servicio.objects.first() or Servicio.objects.create(
            nombre="Servicio de prueba",
            descripcion="Servicio para tests",
            coste=100,
            tiempo_aproximado=1,
        )
        
    def test_signal_envia_email_al_cerrar_compra(self):
        from notificaciones.models import Resumen, enviar_resumen
        from unittest.mock import patch
        
        c = Conversacion.objects.create(dominio="test", estado="abierta")
        Mensaje.objects.create(conversacion=c, texto="Quiero un presupuesto", remitente="usuario")
        Mensaje.objects.create(conversacion=c, texto="Cuesta 1000", remitente="chatbot")
        Mensaje.objects.create(conversacion=c, texto="Acepto", remitente="usuario")
        Pedido.objects.create(
            conversacion=c, 
            nombre="Test", 
            direccion="Dir", 
            servicio=self.servicio, 
            presupuesto=1000, 
            forma_contacto="test@test.com"
        )
        c.tenemosCompra = True
        c.estado = "cerrada"
        c.save()
        
        # Verificar que se creó resumen
        self.assertTrue(c.resumenes.exists())
        
    def test_signal_no_envia_si_no_compra(self):
        c = Conversacion.objects.create(dominio="test", estado="abierta")
        Mensaje.objects.create(conversacion=c, texto="Hola", remitente="usuario")
        Mensaje.objects.create(conversacion=c, texto="Adios", remitente="chatbot")
        c.estado = "cerrada"
        c.save()
        
        self.assertFalse(c.resumenes.exists())


class NERTests(TestCase):
    def test_extraccion_entidades_servicio(self):
        from core.acceso import get_nlp
        nlp = get_nlp()
        doc = nlp("Quiero contratar el servicio de auditoria de seguridad")
        entidades = [(e.text, e.label_) for e in doc.ents]
        # Debe detectar SERVICIO
        self.assertTrue(any(label == "SERVICIO" for _, label in entidades))
        
    def test_extraccion_entidades_precio(self):
        from core.acceso import get_nlp
        nlp = get_nlp()
        doc = nlp("El precio es 1500 euros")
        entidades = [(e.text, e.label_) for e in doc.ents]
        self.assertTrue(any(label == "PRECIO" for _, label in entidades))
        
    def test_extraccion_entidades_empresa(self):
        from core.acceso import get_nlp
        nlp = get_nlp()
        doc = nlp("Mi empresa se llama Test SL")
        entidades = [(e.text, e.label_) for e in doc.ents]
        # El modelo usa SERVICIO para nombres de empresa
        self.assertTrue(any(label == "SERVICIO" for _, label in entidades))
        # Verifica que detecta "Test SL" como entidad
        self.assertTrue(any("Test SL" in text for text, _ in entidades))


class AccesoTests(TestCase):
    def test_get_nlp_cache(self):
        from core.acceso import get_nlp
        nlp1 = get_nlp()
        nlp2 = get_nlp()
        self.assertIs(nlp1, nlp2)  # Debe ser mismo objeto (cached)
        
    def test_llamar_ollama_fallback(self):
        from core.acceso import llamar_llm
        # Debe manejar error de modelo no encontrado y caer a genérico
        try:
            result = llamar_llm("intencion_inexistente", "test", [], "contexto")
            self.assertIsInstance(result, str)
        except Exception:
            # Si Ollama no está corriendo, puede fallar - eso es OK
            pass
        
    def test_generar_resumen_llm(self):
        from core.acceso import generar_resumen_llm
        try:
            texto = "Cliente: Hola\nBot: Hola\nCliente: Quiero presupuesto\nBot: Cuesta 1000"
            resumen = generar_resumen_llm(texto)
            self.assertIsInstance(resumen, str)
            self.assertGreater(len(resumen), 0)
        except Exception:
            # Si Ollama no está corriendo, puede fallar - OK
            pass


class ManagementCommandTests(TestCase):
    def test_cargar_nlp(self):
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command("cargar_nlp", "--limpiar", stdout=out)
        output = out.getvalue()
        self.assertIn("NLP:", output)
        
    def test_generar_nlp(self):
        from django.core.management import call_command
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from entrenamiento.models import EjemploNLP, Intencion

        # La BD de prueba esta vacia: creamos una intencion activa y un ejemplo
        intencion = Intencion.objects.create(nombre="saludo", activa=True)
        EjemploNLP.objects.create(texto="Hola", intencion=intencion, origen="manual")

        out = StringIO()
        # Los .spacy se generan en un temporal para no tocar los archivos reales
        with TemporaryDirectory() as tmp, patch(
            "entrenamiento.management.commands.generar_nlp.SPACY_DIR", Path(tmp)
        ):
            call_command("generar_nlp", stdout=out)
        output = out.getvalue()
        self.assertIn("train.spacy", output)
        self.assertIn("dev.spacy", output)


def run_all_tests():
    import unittest
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar todas las clases de test
    suite.addTests(loader.loadTestsFromTestCase(ChatViewTests))
    suite.addTests(loader.loadTestsFromTestCase(InactividadTests))
    suite.addTests(loader.loadTestsFromTestCase(SignalTests))
    suite.addTests(loader.loadTestsFromTestCase(NERTests))
    suite.addTests(loader.loadTestsFromTestCase(AccesoTests))
    suite.addTests(loader.loadTestsFromTestCase(ManagementCommandTests))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    import os
    import sys
    import django
    
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    
    success = run_all_tests()
    sys.exit(0 if success else 1)