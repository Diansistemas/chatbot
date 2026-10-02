#!/usr/bin/env python
"""
Tests de funcionamiento: flujos completos de la aplicacion.
Ejecuta: python manage.py test pruebas.aplicacion.test_flujo

NOTA: hay que ejecutarlo con manage.py test; si se lanza el archivo
directamente usa la BD de desarrollo y las intenciones ya existentes
provocan "UNIQUE constraint failed: entrenamiento_intencion.nombre".

Cobertura nueva (ademas de tests.py, test_views.py y test_comprehensive.py):
  * crear_pedido_si_completo: extraccion de datos del cliente y auto-pedido
  * responder: la rama contactar_humano (pide datos o deriva al agente)
  * clasificar_conversacion: la decision de resumen/email en el cierre
  * _comprobar_datos_pedido: el checklist del email de resumen
  * Analisis.detectar_servicio y promover_analisis_a_ejemplo
  * Flujos por la vista del widget: bienvenida -> turnos -> compra -> cierre
    con resumen y email, cierre por intencion y derivacion a humano

Solo se simulan llm y resumen (sin Ollama ni SMTP); el modelo spaCy real
se usa siempre, es la pieza bajo prueba.
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
django.setup()

from unittest.mock import patch

from django.core import mail
from django.test import override_settings

from chat.models import Conversacion, Pedido, Servicio
from core.models import (
    Analisis,
    EntidadDetectada,
    crear_pedido_si_completo,
    promover_analisis_a_ejemplo,
    responder,
)
from entrenamiento.models import EtiquetaEntidad, Intencion
from notificaciones.models import Resumen, _comprobar_datos_pedido, clasificar_conversacion
from pruebas.aplicacion.tests import BaseConIntenciones


class BaseConServicio(BaseConIntenciones):
    """Ademas de las intenciones, crea un Servicio (la BD de prueba no trae datos)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.servicio = Servicio.objects.create(
            nombre="Revision general",
            descripcion="Revision del vehiculo",
            coste=50,
            tiempo_aproximado=1,
        )


# ---------------------------------------------------------------------------
# Pedido automatico (crear_pedido_si_completo)
# ---------------------------------------------------------------------------
class TestPedidoAutomatico(BaseConServicio):

    def _conv_en_compra(self):
        conv = self.nueva_conversacion()
        conv.tenemosCompra = True
        conv.save(update_fields=["tenemosCompra"])
        return conv

    def test_extrae_todos_los_datos_del_mensaje(self):
        conv = self._conv_en_compra()
        self.mensaje_usuario(
            conv,
            "Somos la empresa Dian, direccion calle Mayor 5, "
            "presupuesto 5000 €, contacto pedidos@dian.com",
        )

        pedido = crear_pedido_si_completo(conv)

        self.assertIsNotNone(pedido)
        self.assertEqual(conv.conversacion_pedido.count(), 1)
        self.assertEqual(pedido.servicio, self.servicio)
        self.assertEqual(pedido.nombre, "Dian")
        self.assertEqual(pedido.direccion, "calle Mayor 5")
        self.assertEqual(float(pedido.presupuesto), 5000.0)
        self.assertEqual(pedido.forma_contacto, "pedidos@dian.com")

    def test_presupuesto_en_euros_textuales(self):
        conv = self._conv_en_compra()
        self.mensaje_usuario(conv, "Presupuesto aproximado de 3500 euros")

        pedido = crear_pedido_si_completo(conv)

        self.assertIsNotNone(pedido)
        self.assertEqual(float(pedido.presupuesto), 3500.0)
        # Sin datos de contacto se usa el placeholder
        self.assertEqual(pedido.forma_contacto, "Por facilitar")

    def test_sin_intencion_de_compra_no_crea_nada(self):
        conv = self.nueva_conversacion()  # tenemosCompra=False por defecto
        self.mensaje_usuario(conv, "Quiero contratar el plan basico por 30 euros")

        self.assertIsNone(crear_pedido_si_completo(conv))
        self.assertFalse(conv.conversacion_pedido.exists())

    def test_no_duplica_un_pedido_existente(self):
        conv = self._conv_en_compra()
        self.mensaje_usuario(conv, "Quiero contratar el plan basico por 30 euros")
        Pedido.objects.create(
            conversacion=conv, nombre="Ya existente", direccion="Calle 1",
            servicio=self.servicio, presupuesto=10, forma_contacto="a@b.com",
        )

        self.assertIsNone(crear_pedido_si_completo(conv))
        self.assertEqual(conv.conversacion_pedido.count(), 1)

    def test_placeholders_si_solo_hay_mensajes(self):
        conv = self._conv_en_compra()
        self.mensaje_usuario(conv, "hola buenas")

        pedido = crear_pedido_si_completo(conv)

        self.assertIsNotNone(pedido)
        self.assertEqual(pedido.nombre, "Cliente potencial")
        self.assertEqual(pedido.direccion, "Por confirmar")
        self.assertEqual(pedido.forma_contacto, "Por facilitar")
        self.assertEqual(float(pedido.presupuesto), 0.0)

    def test_sin_servicios_no_puede_crear_pedido(self):
        Servicio.objects.all().delete()
        conv = self._conv_en_compra()
        self.mensaje_usuario(conv, "Quiero contratar el plan basico por 30 euros")

        self.assertIsNone(crear_pedido_si_completo(conv))

    @patch("core.models.llamar_llm", return_value="Entendido, le apunto")
    def test_responder_lo_invoca_cuando_hay_compra_pendiente(self, llm):
        conv = self._conv_en_compra()
        mensaje = self.mensaje_usuario(conv, "Quiero contratar el plan basico por 30 euros")

        responder(mensaje)

        # responder() debe auto-crear el pedido antes de contestar
        self.assertTrue(conv.conversacion_pedido.exists())
        pedido = conv.conversacion_pedido.get()
        self.assertEqual(float(pedido.presupuesto), 30.0)
        llm.assert_called_once()
        self.assertEqual(llm.call_args[0][0], "compra")


# ---------------------------------------------------------------------------
# responder(): rama contactar_humano
# ---------------------------------------------------------------------------
class TestContactarHumano(BaseConServicio):

    def _mensaje_con_analisis(self, conv, texto):
        mensaje = self.mensaje_usuario(conv, texto)
        analisis = Analisis.objects.create(
            mensaje=mensaje,
            intencion=Intencion.objects.get(nombre="contactar_humano"),
            confianza=0.98,
        )
        return mensaje, analisis

    @patch("core.models.llamar_llm")
    def test_sin_pedido_pide_datos_de_contacto(self, llm):
        conv = self.nueva_conversacion()
        mensaje, analisis = self._mensaje_con_analisis(conv, "Pasame con un supervisor")

        respuesta = responder(mensaje, analisis=analisis)

        self.assertIn("datos de contacto", respuesta.texto)
        llm.assert_not_called()  # esta rama no llega al llm

    @patch("core.models.llamar_llm")
    def test_con_pedido_deriva_directamente(self, llm):
        conv = self.nueva_conversacion()
        Pedido.objects.create(
            conversacion=conv, nombre="Dian", direccion="Calle 1",
            servicio=self.servicio, presupuesto=100, forma_contacto="dian@dian.com",
        )
        mensaje, analisis = self._mensaje_con_analisis(conv, "Pasame con un supervisor")

        respuesta = responder(mensaje, analisis=analisis)

        self.assertIn("Le conecto con un agente humano", respuesta.texto)
        llm.assert_not_called()

    @patch("core.models.llamar_llm")
    def test_con_datos_previos_crea_pedido_y_deriva(self, llm):
        conv = self.nueva_conversacion()
        conv.tenemosCompra = True
        conv.save(update_fields=["tenemosCompra"])
        # Con email en el mensaje, el pedido auto-creado sale completo
        # (presupuesto + contacto) y la derivacion no se queda sin datos.
        self.mensaje_usuario(conv, "Quiero contratar por 30 euros, mi email es dian@dian.com")
        mensaje, analisis = self._mensaje_con_analisis(conv, "Pasame con un supervisor")

        respuesta = responder(mensaje, analisis=analisis)

        # Ultimo intento: con los datos disponibles se crea el pedido y se deriva
        self.assertTrue(conv.conversacion_pedido.exists())
        self.assertIn("Le conecto con un agente humano", respuesta.texto)
        llm.assert_not_called()


# ---------------------------------------------------------------------------
# clasificar_conversacion(): decision de resumen en el cierre
# ---------------------------------------------------------------------------
class TestClasificadorCierre(BaseConServicio):

    def test_con_pedido_es_compra_segura(self):
        conv = self.nueva_conversacion()
        Pedido.objects.create(
            conversacion=conv, nombre="Dian", direccion="Calle 1",
            servicio=self.servicio, presupuesto=100, forma_contacto="dian@dian.com",
        )
        self.assertTrue(clasificar_conversacion(conv))

    def test_sin_mensajes_del_cliente_no_es_compra(self):
        conv = self.nueva_conversacion()  # solo la bienvenida del bot
        self.assertFalse(clasificar_conversacion(conv))

    def test_mensaje_claro_de_compra(self):
        conv = self.nueva_conversacion()
        self.mensaje_usuario(conv, "Quiero contratar el plan basico por 30 euros")
        self.assertTrue(clasificar_conversacion(conv))

    def test_mensaje_social_no_es_compra(self):
        conv = self.nueva_conversacion()
        self.mensaje_usuario(conv, "Hola, buenos dias")
        self.assertFalse(clasificar_conversacion(conv))


# ---------------------------------------------------------------------------
# _comprobar_datos_pedido(): checklist del email
# ---------------------------------------------------------------------------
class TestChecklistEmail(BaseConServicio):

    def test_sin_pedido_todo_en_false(self):
        conv = self.nueva_conversacion()

        estado = _comprobar_datos_pedido(conv)

        self.assertFalse(estado["tiene_pedido"])
        for campo in ("nombre", "direccion", "servicio", "presupuesto", "forma_contacto"):
            self.assertFalse(estado[campo], campo)

    def test_pedido_completo_todo_en_true(self):
        conv = self.nueva_conversacion()
        Pedido.objects.create(
            conversacion=conv, nombre="Dian", direccion="Calle 1",
            servicio=self.servicio, presupuesto=100, forma_contacto="dian@dian.com",
        )

        estado = _comprobar_datos_pedido(conv)

        self.assertTrue(estado["tiene_pedido"])
        for campo in ("nombre", "direccion", "servicio", "presupuesto", "forma_contacto"):
            self.assertTrue(estado[campo], campo)

    def test_presupuesto_cero_cuenta_como_incompleto(self):
        # Los placeholders no vacios cuentan como completos; 0 no.
        conv = self.nueva_conversacion()
        Pedido.objects.create(
            conversacion=conv, nombre="Cliente potencial", direccion="Por confirmar",
            servicio=self.servicio, presupuesto=0, forma_contacto="Por facilitar",
        )

        estado = _comprobar_datos_pedido(conv)

        self.assertTrue(estado["tiene_pedido"])
        self.assertFalse(estado["presupuesto"])
        self.assertTrue(estado["nombre"])
        self.assertTrue(estado["forma_contacto"])


# ---------------------------------------------------------------------------
# Utilidades de Analisis
# ---------------------------------------------------------------------------
class TestAnalisisUtilidades(BaseConServicio):

    def _analisis_con_entidad(self, con_entidad=True):
        conv = self.nueva_conversacion(con_bienvenida=False)
        mensaje = self.mensaje_usuario(conv, "Cuanto tarda la revision general")
        analisis = Analisis.objects.create(
            mensaje=mensaje,
            intencion=Intencion.objects.get(nombre="consulta_tecnica"),
            confianza=0.95,
        )
        if con_entidad:
            etiqueta, _ = EtiquetaEntidad.objects.get_or_create(nombre="SERVICIO")
            EntidadDetectada.objects.create(
                analisis=analisis,
                etiqueta=etiqueta,
                texto_detectado=self.servicio.nombre,
                inicio=15,
                fin=32,
            )
        return analisis

    def test_detectar_servicio_encuentra_el_objeto(self):
        analisis = self._analisis_con_entidad()
        self.assertEqual(analisis.detectar_servicio(), self.servicio)

    def test_detectar_servicio_sin_entidades_devuelve_none(self):
        analisis = self._analisis_con_entidad(con_entidad=False)
        self.assertIsNone(analisis.detectar_servicio())

    def test_promover_analisis_crea_ejemplo_con_spans(self):
        analisis = self._analisis_con_entidad()

        ejemplo = promover_analisis_a_ejemplo(analisis, origen="manual")

        self.assertEqual(ejemplo.mensaje, analisis.mensaje)
        self.assertEqual(ejemplo.intencion, analisis.intencion)
        self.assertEqual(ejemplo.origen, "manual")
        span = ejemplo.ejemplo_spansEntidad.get()
        self.assertEqual((span.inicio, span.fin), (15, 32))
        self.assertEqual(span.etiqueta.nombre, "SERVICIO")


# ---------------------------------------------------------------------------
# Flujos multi-paso contra la vista del widget
# ---------------------------------------------------------------------------
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    RESUMEN_EMAIL_DESTINATARIOS=["compras@diansistemas.test"],
)
class TestFlujoCompletoVista(BaseConIntenciones):

    def setUp(self):
        if hasattr(mail, "outbox"):
            mail.outbox = []

    @patch("notificaciones.models.generar_resumen_llm", return_value="RESUMEN SIMULADO")
    @patch("core.models.llamar_llm", return_value="Respuesta del asistente")
    def test_bienvenida_consulta_compra_cierre(self, llm, resumen_llm):
        # Turno 1: el primer mensaje crea la conversacion con bienvenida
        r = self.client.post("/chat/", {"accion": "usuario", "texto": "hola"})
        self.assertEqual(r.status_code, 200)
        datos = r.json()
        token = datos["conversacion"]
        self.assertIn("Hola, soy el asistente virtual", datos["bienvenida"]["texto"])

        r = self.client.post("/chat/", {
            "accion": "bot", "mensaje_id": datos["mensaje_id"], "conversacion": token,
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["bot"], "Respuesta del asistente")

        # Turno 2: el usuario muestra intencion de compra
        r = self.client.post("/chat/", {
            "accion": "usuario",
            "texto": "Quiero contratar el plan basico por 30 euros",
            "conversacion": token,
        })
        self.assertEqual(r.status_code, 200)
        id_compra = r.json()["mensaje_id"]

        r = self.client.post("/chat/", {
            "accion": "bot", "mensaje_id": id_compra, "conversacion": token,
        })
        self.assertEqual(r.status_code, 200)
        conv = Conversacion.objects.get(token=token)
        self.assertTrue(conv.tenemosCompra)
        self.assertEqual(conv.estado, "abierta")  # comprar no cierra
        self.assertEqual(llm.call_args[0][0], "compra")

        # Turno 3: cierre -> resumen + email
        r = self.client.post("/chat/", {"accion": "cerrar", "conversacion": token})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["estado"], "cerrada")

        conv.refresh_from_db()
        self.assertEqual(conv.estado, "cerrada")
        resumen = Resumen.objects.get(conversacion=conv)
        self.assertEqual(resumen.tipo, "compra")
        self.assertEqual(resumen.texto, "RESUMEN SIMULADO")
        resumen_llm.assert_called_once()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("[Chatbot]", mail.outbox[0].subject)

        # Secuencia completa: bienvenida, u1, b1, u2, b2
        self.assertEqual(conv.conversacion_mensajes.count(), 5)

    @patch("notificaciones.models.generar_resumen_llm")
    @patch("core.models.llamar_llm")
    def test_cierre_por_intencion_no_deja_resumen(self, llm, resumen_llm):
        r = self.client.post("/chat/", {
            "accion": "usuario", "texto": "Hasta luego que tengas buen dia",
        })
        datos = r.json()
        token = datos["conversacion"]

        r = self.client.post("/chat/", {
            "accion": "bot", "mensaje_id": datos["mensaje_id"], "conversacion": token,
        })
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["cerrada"])

        # "cerrar" responde fijo y sin intencion de compra no hay resumen
        llm.assert_not_called()
        conv = Conversacion.objects.get(token=token)
        self.assertEqual(conv.estado, "cerrada")
        self.assertFalse(Resumen.objects.filter(conversacion=conv).exists())
        self.assertEqual(len(mail.outbox), 0)
        resumen_llm.assert_not_called()

    @patch("core.models.llamar_llm")
    def test_contactar_humano_pide_datos(self, llm):
        r = self.client.post("/chat/", {
            "accion": "usuario", "texto": "Pasame con un supervisor por favor",
        })
        datos = r.json()
        token = datos["conversacion"]

        r = self.client.post("/chat/", {
            "accion": "bot", "mensaje_id": datos["mensaje_id"], "conversacion": token,
        })
        self.assertEqual(r.status_code, 200)
        self.assertIn("datos de contacto", r.json()["bot"])
        llm.assert_not_called()


if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)
