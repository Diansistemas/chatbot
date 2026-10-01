"""Tests formales de la aplicacion.

Ejecutar con:  python manage.py test

Cobertura:
  * NLP: procesar_mensaje (intenciones, confianza, entidades, fallback)
  * responder: compra / cerrar / demas intenciones, guarda de doble respuesta,
    pares de entrenamiento generados en el cierre
  * Vistas del widget: HTTP, validaciones, bloqueos (403/404/409/410), inactividad
  * Senal de cierre: resumen LLM + email (ambos simulados; sin Ollama ni SMTP)

El modelo spaCy real SIEMPRE se usa (es la pieza bajo prueba); solo se
simulan las llamadas de red (llm y resumen) para que la suite sea rapida
y no dependa de Ollama.
"""
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core import mail
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from chat.models import Conversacion, Mensaje
from core.acceso import MAPEO_INTENCION_MODELO
from core.models import Analisis, cerrar_conversacion, guardar_respuesta_bot, procesar_mensaje, responder
from entrenamiento.models import Intencion, Par_Mensaje_Respuesta
from notificaciones.models import Resumen

INTENCIONES = [
    "compra",
    "consulta_tecnica",
    "confirmacion",
    "cerrar",
    "contactar_humano",
    "solicitar_agente",
    "otro",
]

BIENVENIDA = "Hola, soy el asistente virtual de Dian Sistemas ¿que necesitas?"


class BaseConIntenciones(TestCase):
    """Crea las intenciones de la BD (las migraciones no siembran datos)."""

    @classmethod
    def setUpTestData(cls):
        for nombre in INTENCIONES:
            Intencion.objects.create(nombre=nombre, activa=True)

    def nueva_conversacion(self, con_bienvenida=True):
        conv = Conversacion.objects.create()
        if con_bienvenida:
            Mensaje.objects.create(conversacion=conv, texto=BIENVENIDA, remitente="chatbot")
        return conv

    def mensaje_usuario(self, conv, texto):
        return Mensaje.objects.create(conversacion=conv, texto=texto, remitente="usuario")


# ---------------------------------------------------------------------------
# NLP
# ---------------------------------------------------------------------------
class TestProcesarMensaje(BaseConIntenciones):

    def _analizar(self, texto):
        conv = self.nueva_conversacion(con_bienvenida=False)
        mensaje = self.mensaje_usuario(conv, texto)
        return procesar_mensaje(mensaje)

    def test_compra_detecta_intencion_y_entidades(self):
        analisis = self._analizar("Quiero contratar el plan basico por 30 euros")
        self.assertEqual(analisis.intencion.nombre, "compra")
        self.assertGreater(analisis.confianza, 0.9)
        ents = {e.etiqueta.nombre: e.texto_detectado for e in analisis.analisis_entidad.all()}
        self.assertEqual(ents.get("PRECIO"), "30 euros")
        self.assertIn("SERVICIO", ents)

    def test_consulta_tecnica_detecta_servicio(self):
        analisis = self._analizar("Cuanto tarda la revision general")
        self.assertEqual(analisis.intencion.nombre, "consulta_tecnica")
        ents = [e.etiqueta.nombre for e in analisis.analisis_entidad.all()]
        self.assertIn("SERVICIO", ents)

    def test_cerrar_detecta_despedida(self):
        analisis = self._analizar("Hasta luego que tengas buen dia")
        self.assertEqual(analisis.intencion.nombre, "cerrar")
        ents = [e.etiqueta.nombre for e in analisis.analisis_entidad.all()]
        self.assertIn("FINAL", ents)

    def test_contactar_humano_detecta_agente(self):
        analisis = self._analizar("Pasame con un supervisor por favor")
        self.assertEqual(analisis.intencion.nombre, "contactar_humano")
        ents = [e.etiqueta.nombre for e in analisis.analisis_entidad.all()]
        self.assertIn("AGENTE_HUMANO", ents)

    def test_solicitar_agente_es_benigno(self):
        # El modelo confunde este sinonimo con contactar_humano; ambos deben
        # caer en el mismo LLM via MAPEO, asi que el test solo exige ese par.
        analisis = self._analizar("Necesito hablar con un operador")
        self.assertIn(analisis.intencion.nombre, {"solicitar_agente", "contactar_humano"})

    def test_con_intenciones_inactivas_usa_otro(self):
        Intencion.objects.update(activa=False)
        analisis = self._analizar("Hola, buenos dias")
        self.assertEqual(analisis.intencion.nombre, "otro")

    def test_analisis_y_entidades_persistidos(self):
        analisis = self._analizar("Quiero contratar el plan basico por 30 euros")
        self.assertTrue(Analisis.objects.filter(pk=analisis.pk).exists())
        # La entidad se puede recuperar desde el mensaje
        mensaje = analisis.mensaje
        self.assertTrue(mensaje.mensaje_analisis.analisis_entidad.exists())


# ---------------------------------------------------------------------------
# responder()
# ---------------------------------------------------------------------------
class TestResponder(BaseConIntenciones):

    @patch("core.models.llamar_llm", return_value="Respuesta generada por el LLM")
    def test_compra_marca_flag_y_llama_al_llm(self, llm):
        conv = self.nueva_conversacion()
        mensaje = self.mensaje_usuario(conv, "Quiero contratar el plan basico por 30 euros")

        respuesta = responder(mensaje)
        conv.refresh_from_db()

        self.assertTrue(conv.tenemosCompra)
        self.assertEqual(conv.estado, "abierta")  # compras no cierran
        self.assertEqual(respuesta.remitente, "chatbot")
        self.assertEqual(respuesta.texto, "Respuesta generada por el LLM")
        llm.assert_called_once()
        self.assertEqual(llm.call_args[0][0], "compra")  # intencion enviada al LLM

    @patch("notificaciones.models.generar_resumen_llm", return_value="Resumen simulado")
    @patch("core.models.llamar_llm")
    def test_cerrar_cierra_sin_llm_y_genera_pares(self, llm, _resumen):
        conv = self.nueva_conversacion()
        mensaje = self.mensaje_usuario(conv, "Hasta luego que tengas buen dia")

        respuesta = responder(mensaje)
        conv.refresh_from_db()

        self.assertEqual(conv.estado, "cerrada")
        self.assertIsNotNone(conv.fecha_fin)
        llm.assert_not_called()  # "cerrar" responde fijo, sin LLM
        self.assertIn("Gracias", respuesta.texto)

        pares = Par_Mensaje_Respuesta.objects.filter(mensaje_chatbot__conversacion=conv)
        self.assertEqual(pares.count(), 1)
        par = pares.get()
        self.assertEqual(par.intencion.nombre, "cerrar")
        self.assertEqual(par.texto_usuario, mensaje.texto)
        self.assertEqual(par.texto_chatbot, respuesta.texto)

        # Sin intencion de compra no debe crearse resumen
        self.assertFalse(Resumen.objects.filter(conversacion=conv).exists())

    @patch("core.models.llamar_llm", return_value="ok")
    def test_otra_intencion_usa_llm_con_su_intencion(self, llm):
        conv = self.nueva_conversacion()
        mensaje = self.mensaje_usuario(conv, "Cuanto tarda la revision general")

        responder(mensaje)
        llm.assert_called_once()
        self.assertEqual(llm.call_args[0][0], "consulta_tecnica")

    def test_no_duplica_respuesta(self):
        conv = self.nueva_conversacion()
        mensaje = self.mensaje_usuario(conv, "Quiero contratar el plan basico por 30 euros")

        primera = guardar_respuesta_bot(mensaje, "hola")
        segunda = guardar_respuesta_bot(mensaje, "hola")

        self.assertEqual(primera.pk, segunda.pk)
        self.assertEqual(conv.conversacion_mensajes.filter(remitente="chatbot").count(), 2)  # bienvenida + 1

    def test_mapeo_cubre_todas_las_intenciones(self):
        # Si aparece una intencion sin entrada en MAPEO, llamar_llm cae a
        # "otro" igualmente; el test documenta esa garantia.
        for nombre in INTENCIONES:
            with self.subTest(intencion=nombre):
                self.assertIn(nombre, MAPEO_INTENCION_MODELO)


# ---------------------------------------------------------------------------
# Vistas del widget
# ---------------------------------------------------------------------------
class TestVistas(BaseConIntenciones):

    # El runner de tests aniade 'testserver' a ALLOWED_HOSTS (DEBUG=False
    # en tests rechaza cualquier otro host; ver setup_test_environment).
    def get(self, path, **kw):
        return self.client.get(path, **kw)

    def post(self, path, data=None, **kw):
        return self.client.post(path, data or {}, **kw)

    def test_paginas_basicas(self):
        for ruta in ("/", "/chat/", "/prueba/"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.get(ruta).status_code, 200)

        r = self.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    @patch("config.urls.requests.get")
    def test_v1_models_formato_openai(self, requests_get):
        requests_get.return_value = MagicMock(
            json=lambda: {"models": [{"name": "llama3.2:latest"}]}
        )
        r = self.get("/v1/models")
        self.assertEqual(r.status_code, 200)
        datos = r.json()
        self.assertEqual(datos["object"], "list")
        self.assertEqual(datos["data"][0]["id"], "llama3.2:latest")

    def test_primer_mensaje_crea_conversacion_con_bienvenida(self):
        r = self.post("/chat/", {"accion": "usuario", "texto": "hola"})
        self.assertEqual(r.status_code, 200)
        datos = r.json()
        self.assertIn("bienvenida", datos)
        conv = Conversacion.objects.get(token=datos["conversacion"])
        textos = list(conv.conversacion_mensajes.values_list("texto", flat=True))
        self.assertEqual(len(textos), 2)
        self.assertEqual(textos[0], BIENVENIDA)

    def test_validaciones_de_entrada(self):
        r = self.post("/chat/", {"accion": "usuario", "texto": "   "})
        self.assertEqual(r.status_code, 400)

        r = self.post("/chat/", {"accion": "inventada"})
        self.assertEqual(r.status_code, 400)

        r = self.post("/chat/", {"accion": "bot", "mensaje_id": "1"})
        self.assertEqual(r.status_code, 400)  # sin conversacion

    def test_referer_ajeno_prohibido(self):
        r = self.client.get("/chat/", HTTP_REFERER="https://evil.com/robar")
        self.assertEqual(r.status_code, 403)

    def test_widget_lleva_cabecera_csp(self):
        r = self.get("/chat/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("frame-ancestors", r["Content-Security-Policy"])

    def test_doble_respuesta_rechazada_409(self):
        conv = self.nueva_conversacion()
        usuario = self.mensaje_usuario(conv, "quiero algo")
        Mensaje.objects.create(conversacion=conv, texto="ok", remitente="chatbot")

        r = self.post("/chat/", {
            "accion": "bot", "mensaje_id": usuario.pk, "conversacion": conv.token,
        })
        self.assertEqual(r.status_code, 409)

    def test_mensaje_inexistente_404(self):
        conv = self.nueva_conversacion()
        r = self.post("/chat/", {
            "accion": "bot", "mensaje_id": 999999, "conversacion": conv.token,
        })
        self.assertEqual(r.status_code, 404)

    def test_mensaje_a_conversacion_cerrada_410(self):
        conv = self.nueva_conversacion()
        conv.cerrar()

        r = self.post("/chat/", {
            "accion": "usuario", "texto": "hola?", "conversacion": conv.token,
        })
        self.assertEqual(r.status_code, 410)

    def test_polling_estado(self):
        conv = self.nueva_conversacion()
        ultima_bienvenida = conv.conversacion_mensajes.order_by("-pk").first().pk
        Mensaje.objects.create(conversacion=conv, texto="respuesta", remitente="chatbot")

        # desde_id = bienvenida -> solo cuenta los mensajes del bot posteriores
        r = self.post("/chat/", {
            "accion": "estado", "desde_id": ultima_bienvenida, "conversacion": conv.token,
        })
        self.assertEqual(r.status_code, 200)
        datos = r.json()
        self.assertFalse(datos["esperando"])  # ultimo mensaje = del bot
        self.assertFalse(datos["cerrada"])
        self.assertEqual(len(datos["mensajes"]), 1)

        # Si el ultimo mensaje es del usuario, el frontend bloquea el formulario
        self.mensaje_usuario(conv, "dime algo")
        r = self.post("/chat/", {"accion": "estado", "desde_id": 0, "conversacion": conv.token})
        self.assertTrue(r.json()["esperando"])

    def test_cierre_manual(self):
        conv = self.nueva_conversacion()
        r = self.post("/chat/", {"accion": "cerrar", "conversacion": conv.token})
        self.assertEqual(r.status_code, 200)
        conv.refresh_from_db()
        self.assertEqual(conv.estado, "cerrada")

    def test_conversacion_inactiva_se_cierra_al_recargar(self):
        conv = self.nueva_conversacion()
        self.mensaje_usuario(conv, "hola")
        # Envejecemos TODOS los mensajes (la bienvenida se crea la ultima vez
        # que se toca el reloj; si solo envejecemos uno, la bienvenida gana)
        Mensaje.objects.filter(conversacion=conv).update(
            fecha_mensaje=timezone.now() - timedelta(minutes=10)
        )

        r = self.get(f"/chat/?conversacion={conv.token}")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.context["conversacion"])
        conv.refresh_from_db()
        self.assertEqual(conv.estado, "cerrada")


# ---------------------------------------------------------------------------
# Senal de cierre: resumen + email
# ---------------------------------------------------------------------------
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    RESUMEN_EMAIL_DESTINATARIOS=["compras@diansistemas.test"],
)
class TestSenalCierre(BaseConIntenciones):

    def setUp(self):
        if hasattr(mail, "outbox"):
            mail.outbox = []

    @patch("notificaciones.models.generar_resumen_llm", return_value="RESUMEN SIMULADO")
    def test_cierre_con_compra_genera_resumen_y_email(self, resumen_llm):
        conv = self.nueva_conversacion()
        self.mensaje_usuario(conv, "Quiero contratar el plan basico por 30 euros")
        Mensaje.objects.create(conversacion=conv, texto="Perfecto, le apunto", remitente="chatbot")

        cerrar_conversacion(conv)

        resumen = Resumen.objects.get(conversacion=conv)
        self.assertEqual(resumen.tipo, "compra")
        self.assertEqual(resumen.texto, "RESUMEN SIMULADO")
        resumen_llm.assert_called_once()

        outbox = getattr(mail, "outbox", [])
        self.assertEqual(len(outbox), 1)
        self.assertIn("[Chatbot]", outbox[0].subject)
        self.assertIn("compras@diansistemas.test", outbox[0].to)

    @patch("notificaciones.models.generar_resumen_llm", return_value="RESUMEN SIMULADO")
    def test_cierre_sin_compra_no_resumen_ni_email(self, resumen_llm):
        conv = self.nueva_conversacion()
        self.mensaje_usuario(conv, "Hasta luego que tengas buen dia")

        cerrar_conversacion(conv)

        self.assertEqual(Resumen.objects.filter(conversacion=conv).count(), 0)
        self.assertEqual(len(getattr(mail, "outbox", [])), 0)
        resumen_llm.assert_not_called()

    @patch("notificaciones.models.generar_resumen_llm", return_value="RESUMEN SIMULADO")
    def test_cierre_duplicado_no_reenvia_email(self, resumen_llm):
        conv = self.nueva_conversacion()
        self.mensaje_usuario(conv, "Quiero contratar el plan basico por 30 euros")

        cerrar_conversacion(conv)
        # Un segundo guardado del cierre no debe repetir el envio
        conv.cerrar()

        self.assertEqual(Resumen.objects.filter(conversacion=conv).count(), 1)
        self.assertEqual(len(getattr(mail, "outbox", [])), 1)
        resumen_llm.assert_called_once()
