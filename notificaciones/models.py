import logging

from django.db import models
from chat.models import Conversacion, Pedido
from django.conf import settings
from django.core.mail import EmailMessage

from core.acceso import clasificar_texto, generar_resumen_llm


logger = logging.getLogger(__name__)


# Generamos el texto de un resumen
def generar_resumen(conversacion):
    texto_transcripcion = conversacion.transcripcion()
    try:
        texto = generar_resumen_llm(texto_transcripcion)
    except Exception:
        logger.exception("Fallo al generar el resumen de la conversación %s", conversacion.pk)
        texto = ""

    # Si el LLM falla, escribimos un mensaje de error
    if not texto:
        texto = "(No se pudo generar el resumen automático. Transcripción completa:)\n\n" + texto_transcripcion

    return texto


def clasificar_conversacion(conversacion):
    """
    Clasifica la conversación antes de generar el resumen.
    Usa el modelo spaCy entrenado para detectar intención de compra.
    Analiza CADA mensaje del CLIENTE individualmente y verifica si ALGUNO
    tiene alta confianza en 'compra' o 'confirmacion' Y contiene palabras clave de compra.
    Retorna True si hay intención de compra, False en otro caso.
    Red de seguridad: si la conversación tiene Pedido asociado -> compra.
    """
    # Red de seguridad: si hay Pedido, es compra segura
    if conversacion.conversacion_pedido.exists():
        return True
    
    # Palabras clave que indican intención real de compra (no solo cortesía)
    PALABRAS_COMPRA = {
        "compra", "presupuesto", "pedido", "contratar", "precio", "coste",
        "costo", "tarifa", "cuota", "reserva", "tarifa", "adquirir",
        "comprar", "pagar", "facturar", "contratacion", "contratación",
        "acepto", "confirmo", "confirmacion", "confirmación", "aceptar",
        "quiero", "necesito", "interesa", "interesado", "quiero comprar",
        "me interesa", "quiero contratar", "solicito", "solicitar",
        "auditoria", "auditoría", "mantenimiento", "servicio", "pack",
        "paquete", "plan", "anual", "mensual", "euros", "eur", "€",
        "coste", "precio", "importe", "total"
    }
    
    try:
        # Cargar modelo spaCy (cacheado a nivel de módulo para rendimiento).
        # Antes: spacy.load(settings.SPACY_MODEL_PATH) -> cargaba una SEGUNDA
        # copia del modelo (get_nlp() ya lo tiene cacheado) y petaba si
        # entrenamiento/spacy/ no existia, cayendo al fallback de palabras
        # clave sin que se notara.
        if not hasattr(clasificar_conversacion, "_nlp"):
            from core.acceso import get_nlp
            clasificar_conversacion._nlp = get_nlp()
        
        # Analizar CADA mensaje del cliente individualmente
        mensajes_cliente = conversacion.conversacion_mensajes.filter(remitente="usuario")
        if not mensajes_cliente.exists():
            return False
        
        # Verificar si ALGÚN mensaje tiene intención compra/confirmacion con confianza >= 0.6
        # Y contiene al menos una palabra clave de compra
        # Los máximos se recogen AQUI dentro: el log de abajo antes volvía a
        # pasar todos los mensajes por la NLP (2 llamadas extra por mensaje)
        # y logger.debug evalúa sus argumentos aunque el nivel esté apagado.
        # Resultado: 3x la NLP en cada cierre que no era compra.
        max_compra = 0.0
        max_confirm = 0.0
        for mensaje in mensajes_cliente:
            texto_lower = mensaje.texto.lower()
            # Mismo criterio que core.models.procesar_mensaje: el textcat
            # corre sobre el texto en minusculas. Aqui no hacen falta las
            # entidades, asi que es UNA sola pasada por mensaje.
            cats, _ = clasificar_texto(
                clasificar_conversacion._nlp, mensaje.texto
            )

            # Obtener confianza para compra y confirmacion
            conf_compra = cats.get("compra", 0.0)
            conf_confirmacion = cats.get("confirmacion", 0.0)
            max_compra = max(max_compra, conf_compra)
            max_confirm = max(max_confirm, conf_confirmacion)
            
            # Verificar si el mensaje contiene palabras clave de compra
            tiene_palabras_compra = any(p in texto_lower for p in PALABRAS_COMPRA)
            
            # Requiere: (confianza alta Y palabras clave) O confianza muy alta (>=0.9) para COMPRA
            if (conf_compra >= 0.6 or conf_confirmacion >= 0.6) and tiene_palabras_compra:
                top_intencion = "compra" if conf_compra >= conf_confirmacion else "confirmacion"
                confianza = max(conf_compra, conf_confirmacion)
                logger.debug(
                    "Clasificación NLP conv %s (mensaje %s): %s (%.3f) + keywords -> COMPRA",
                    conversacion.pk, mensaje.pk, top_intencion, confianza
                )
                return True
            
            # Confianza muy alta (>=0.9) SOLO para compra (no confirmacion, que da falsos positivos en mensajes corteses)
            if conf_compra >= 0.9:
                logger.debug(
                    "Clasificación NLP conv %s (mensaje %s): compra (%.3f) muy alta -> COMPRA",
                    conversacion.pk, mensaje.pk, conf_compra
                )
                return True
        
        # Log para debug: los maximos ya vienen calculados del bucle de arriba.
        # Antes se volvian a calcular aqui con 2 llamadas NLP MAS por mensaje.
        logger.debug(
            "Clasificación NLP conv %s: max compra=%.3f, max confirmacion=%.3f -> NO COMPRA",
            conversacion.pk, max_compra, max_confirm
        )
        
        return False
        
    except Exception:
        logger.exception("Error en clasificación NLP, fallback a palabras clave")
        # Fallback a método anterior por si falla el modelo
        mensajes_cliente = conversacion.conversacion_mensajes.filter(remitente="usuario")
        texto_cliente = " ".join(m.texto.lower() for m in mensajes_cliente)
        palabras_clave = [
            "compra", "presupuesto", "pedido", "servicio", "precio",
            "coste", "costo", "tarifa", "cuota", "reserva", "contratar",
            "cotización", "información sobre", "quiero", "necesito",
            "me gustaría", "disponible", "paquete"
        ]
        score = sum(1 for p in palabras_clave if p in texto_cliente)
        return score > 0


# Creamos el objeto resumen
def crear_resumen(conversacion):
    texto = generar_resumen(conversacion)
    return Resumen.objects.create(conversacion=conversacion, texto=texto)


# Comprobamos si el pedido asociado tiene los datos minimos completos
# Devuelve un diccionario con el estado de cada campo
def _comprobar_datos_pedido(conversacion):
    pedido = conversacion.conversacion_pedido.first()

    if not pedido:
        return {
            "tiene_pedido": False,
            "nombre": False,
            "direccion": False,
            "servicio": False,
            "presupuesto": False,
            "forma_contacto": False,
        }

    return {
        "tiene_pedido": True,
        "nombre": bool(pedido.nombre),
        "direccion": bool(pedido.direccion),
        "servicio": bool(pedido.servicio),
        "presupuesto": bool(pedido.presupuesto),
        "forma_contacto": bool(pedido.forma_contacto),
    }


# Cuerpo del correo: la checklist de datos va AL PRINCIPIO,
# antes de la construccion del resto del cuerpo con el resumen del LLM
def _construir_cuerpo_email(conversacion, resumen):
    estado_datos = _comprobar_datos_pedido(conversacion)

    # --- CHECKLIST AL PRINCIPIO ---
    cuerpo = ""
    if estado_datos["tiene_pedido"]:
        if all(estado_datos.values()):
            cuerpo += "✅ Todos los datos del pedido están completos.\n\n"
        else:
            faltantes = [k for k, v in estado_datos.items() if k != "tiene_pedido" and not v]
            cuerpo += f"❌ Faltan datos: {', '.join(faltantes)}.\n\n"
    else:
        cuerpo += "⏳ No hay datos de pedido registrados aún.\n\n"

    # --- RESTO DEL CUERPO ---
    fin = (
        conversacion.fecha_fin.strftime("%d/%m/%Y %H:%M")
        if conversacion.fecha_fin else "N/D"
    )
    cuerpo += (
        "╔══════════════════════════════════════════════════════╗\n"
        "║     RESUMEN DE CONVERSACIÓN - CHATBOT DIANSISTEMAS  ║\n"
        "╚═════════════════════════════════════════════════════╝\n\n"
        f"📋 Conversación Nº: {conversacion.pk}\n"
        f"🌐 Dominio: {conversacion.dominio or 'N/D'}\n"
        f"📆 Inicio: {conversacion.fecha_inicio:%d/%m/%Y %H:%M}\n"
        f"📆 Fin: {fin}\n"
        f"🏷️ Tipo: {resumen.tipo}\n\n"
        "──────────────────────────────────────────────────────────\n"
        "📝 RESUMEN DEL LLM:\n"
        "──────────────────────────────────────────────────────────\n\n"
        f"{resumen.texto}\n\n"
        "──────────────────────────────────────────────────────────\n"
        "📦 DATOS DEL PEDIDO (si existen):\n"
        "──────────────────────────────────────────────────────────\n"
    )

    pedido = conversacion.conversacion_pedido.first()

    if pedido:
        cuerpo += (
            f"   • Nombre: {pedido.nombre}\n"
            f"   • Dirección: {pedido.direccion}\n"
            f"   • Servicio: {pedido.servicio}\n"
            f"   • Presupuesto: €{pedido.presupuesto}\n"
            f"   • Contacto: {pedido.forma_contacto}\n"
        )
    else:
        cuerpo += "   • No hay datos de pedido registrados aún.\n"

    cuerpo += (
        "──────────────────────────────────────────────────────────\n"
        "⚠️ CHECKLIST DE DATOS (detalle):\n"
        "──────────────────────────────────────────────────────────\n"
    )

    if pedido:
        campos_faltantes = []
        if not pedido.nombre:
            campos_faltantes.append("nombre")
        if not pedido.direccion:
            campos_faltantes.append("dirección")
        if not pedido.servicio:
            campos_faltantes.append("servicio")
        if not pedido.presupuesto:
            campos_faltantes.append("presupuesto")
        if not pedido.forma_contacto:
            campos_faltantes.append("forma de contacto")

        if campos_faltantes:
            cuerpo += f"   ❌ Faltan: {', '.join(campos_faltantes)}\n"
        else:
            cuerpo += "   ✅ Todos los datos completos.\n"
    else:
        cuerpo += "   ⏳ Aún no se ha iniciado el proceso de pedido.\n"

    cuerpo += (
        "──────────────────────────────────────────────────────────\n"
        "💡 SIGUIENTE PASO RECOMENDADO:\n"
        "──────────────────────────────────────────────────────────\n"
        "   → Contactar al cliente para confirmar los detalles del pedido.\n"
    )

    return cuerpo

# Resumen para mandar por correo
class Resumen(models.Model):

    # Relacion con la conversacion
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name="resumenes")

    # Texto del resumen
    texto = models.TextField(blank=True, null=True)

    # Tipo de resumen
    tipo_choices = [
        ("sin_categoria", "Sin categoría"),
        ("consulta_tecnica", "Consulta técnica"),
        ("compra", "Compra")
    ]

    tipo = models.CharField(max_length=20, choices=tipo_choices, default="sin_categoria")    

    
    # Enviar el resumen por correo
    # Devuelve True si se ha mandado bien
    # Delegamos en la funcion del modulo para no tener dos versiones del cuerpo
    def enviar_resumen(self):
        return enviar_resumen(self)
    
    # Traduccimos en español
    class Meta:
        verbose_name = "Resumen"
        verbose_name_plural = "Resúmenes"

    def __str__(self):
        return f"Resumen Nº{self.pk}"
    
def enviar_resumen(resumen):
    """
    Envía el resumen de una conversación por correo al administrador.
    El cuerpo lo construye _construir_cuerpo_email, que pone la checklist
    de datos AL PRINCIPIO, antes del resumen del LLM.
    Devuelve True si se ha enviado.
    """
    destinatarios = getattr(settings, "RESUMEN_EMAIL_DESTINATARIOS", [])
    if not destinatarios:
        logger.warning("RESUMEN_EMAIL_DESTINATARIOS vacío; no se envía el resumen %s", resumen.pk)
        return False

    conversacion = resumen.conversacion
    asunto = f"[Chatbot] Compra - Conversación Nº{conversacion.pk}"
    cuerpo = _construir_cuerpo_email(conversacion, resumen)

    try:
        email = EmailMessage(
            subject=asunto,
            body=cuerpo,
            from_email=settings.EMAIL_HOST_USER or "chatbot@localhost",
            to=destinatarios,
        )
        email.send(fail_silently=False)
        logger.info("Resumen %s enviado exitosamente a %s", resumen.pk, destinatarios)
        return True
    except Exception:
        logger.exception("Error al enviar el resumen %s", resumen.pk)
        return False
