from django.db import models, transaction

from chat.models import Mensaje, Conversacion, Servicio, Pedido
from entrenamiento.models import Intencion, EtiquetaEntidad, EjemploNLP, SpanEntidad, Par_Mensaje_Respuesta
from .acceso import get_nlp, llamar_llm

import logging
logger = logging.getLogger(__name__)

#Analisis de cada mensaje
class Analisis(models.Model):

    # Que mensaje
    mensaje = models.OneToOneField(Mensaje, on_delete = models.CASCADE, related_name="mensaje_analisis")

    # Que intecion hemos detectado
    intencion = models.ForeignKey(Intencion, on_delete = models.SET_NULL, null=True, blank=True, related_name="intencion_analisis")

    # Cuanta confianza tenemos en que el analisis es correcto
    confianza  = models.FloatField(null=True, blank=True)

    # Como detectamos los servicios en el analisis.
    # Es mas para debuggear que para otra cosa.
    # Existe como pillar el objeto "real", no la instancia del servicio
    def detectar_servicio(self):

        entidad_servicio = self.analisis_entidad.filter(etiqueta__nombre="SERVICIO").first()
        if not entidad_servicio:
            return None
    
        return Servicio.objects.filter(nombre__icontains=entidad_servicio.texto_detectado).first()
    
    class Meta:
        verbose_name = "Analisis de Mensaje"
        verbose_name_plural = "Analisis de Mensajes"

    def __str__(self):
        return f"Analisis: {self.mensaje}"

# Entidades y etiquetas detectadas en el analsis
class EntidadDetectada(models.Model):

    # A que analisis pertenece
    analisis = models.ForeignKey(Analisis, on_delete=models.CASCADE, related_name="analisis_entidad")

    # Que etiqueta hemos detectado
    etiqueta = models.ForeignKey(EtiquetaEntidad, on_delete=models.PROTECT, related_name="etiqueta_entidad")

    # Que texto tiene esta etiqueta
    texto_detectado = models.TextField()

    # Donde empieza la etiqueta
    inicio = models.PositiveSmallIntegerField()

    # Donde acaba la etiqueta
    fin = models.PositiveSmallIntegerField()
    
    class Meta:
        verbose_name = "Entidad Detectada"
        verbose_name_plural = "Entidades Detectadas"

    def __str__(self):
        return f"Entidad {self.etiqueta.nombre}: {self.texto_detectado}"

# Creamos los pares desde una conversacion
# Lo mantenemos en core porque es funcionalidad interna del chatbot para comunicar conversacion y entrenamiento
def generar_pares_desde_conversacion(conversacion):
    mensajes = list(conversacion.conversacion_mensajes.order_by("fecha_mensaje"))

    # Ignoramos el mensaje de introducción (hardcodeado, siempre el primero)
    mensajes = mensajes[1:]

    # Por si acaso el analisis ha fallado y no tenemos una intencion
    intencion_otro = Intencion.objects.get(nombre="otro")

    # Que par de mensaje - usar zip para evitar index out of range
    pares = []
    usuarios = mensajes[::2]      # indices pares: 0, 2, 4...
    chatbots = mensajes[1::2]     # indices impares: 1, 3, 5...

    for mensaje_usuario, mensaje_chatbot in zip(usuarios, chatbots):
        analisis = getattr(mensaje_usuario, "mensaje_analisis", None)
        intencion = analisis.intencion if (analisis and analisis.intencion) else intencion_otro

        pares.append(Par_Mensaje_Respuesta(
            intencion=intencion,
            mensaje_usuario=mensaje_usuario,
            texto_usuario=mensaje_usuario.texto,
            mensaje_chatbot=mensaje_chatbot,
            texto_chatbot=mensaje_chatbot.texto,
        ))

    return Par_Mensaje_Respuesta.objects.bulk_create(pares)

# Cerramos una conversacion y guardamos los mensajes en pares
# Cambiamos el estado y poco mas
# TODO: Llamarla cuando una conversacione este inactiva
def cerrar_conversacion(conversacion):

    conversacion.estado = "cerrada"
    conversacion.fecha_fin = conversacion.conversacion_mensajes.order_by("-fecha_mensaje").first().fecha_mensaje
    conversacion.save()
    generar_pares_desde_conversacion(conversacion)

# Donde comprobamos que estamos cerrando una conversacion
# Solo lo llamamos si detectamos que el usuario quiere cerrar conversacion
# TODO: Confirmamos que quiere cerrar y si detecta que si, cerramos
# TODO: Logica interna del chatbot para cerrar conversaciones
def confirmamos_cierre(conversacion):
    cerrar_conversacion(conversacion)

# Procesa un mensaje que el chat bot acaba de recibir
def procesar_mensaje(mensaje_recibido):

    # Pillamos los modelos y el mensaje recibido
    nlp = get_nlp()
    doc = nlp(mensaje_recibido.texto)

    # Intencion y confianza 
    intencion = None
    confianza = None

    if doc.cats:
        nombre_intencion = max(doc.cats, key=doc.cats.get)
        confianza = doc.cats[nombre_intencion]
        intencion = Intencion.objects.filter(nombre=nombre_intencion, activa=True).first()
        if intencion is None:
            logger.warning("Intención '%s' no existe o no está activa. Pipeline: %s",
                           nombre_intencion, nlp.pipe_names)
    else:
        logger.warning("doc.cats vacío. Pipeline cargado: %s", nlp.pipe_names)

    # Si no hemos podido detectar nada, usamos "otro"
    if intencion is None:
        intencion = Intencion.objects.filter(nombre="otro").first()

    analisis = Analisis.objects.create(mensaje=mensaje_recibido, intencion=intencion, confianza=confianza)

    entidades = []
    for entidad in doc.ents:
        etiqueta, _ = EtiquetaEntidad.objects.get_or_create(nombre=entidad.label_)
        entidades.append(EntidadDetectada(
            analisis=analisis,
            etiqueta=etiqueta,
            texto_detectado=entidad.text,
            inicio=entidad.start_char,
            fin=entidad.end_char,
        ))

    EntidadDetectada.objects.bulk_create(entidades)

    logger.info(
        "ANALISIS mensaje_id=%s intencion=%s confianza=%s entidades=%s texto=%r",
        mensaje_recibido.pk,
        intencion.nombre if intencion else "ninguna",
        f"{confianza:.2f}" if confianza is not None else "n/a",
        [e.etiqueta.nombre for e in entidades],
        mensaje_recibido.texto[:80],
    )

    return analisis

# Como "respondemos", en concreto lo combinamos con acceso para decidir a que instancia del llm llamamos
def generar_respuesta_llm(mensaje, analisis, servicio): 

    # A que conversacion estamos respondiendo
    conversacion = mensaje.conversacion

    # De que estamos hablando
    if analisis.intencion:    
        intencion = analisis.intencion.nombre

    # Si no sabemos, vamos a un modelo generico
    else:
        intencion = "otro"

    # De que servicio estamos hablando
    # Si el NER no ha detectado nada no mandamos "None" al LLM
    if servicio:
        contexto = f"Servicio del que habla el usuario: {servicio}"
    else:
        contexto = "No se ha identificado ningun servicio concreto en el mensaje"

    # Generamos el historico excluyendo el mensaje que genera la respuesta
    historico = [
        {"role": "user" if mensaje.remitente == "usuario" else "assistant", "content": mensaje.texto}
        for mensaje in conversacion.conversacion_mensajes.exclude(pk=mensaje.pk).order_by("fecha_mensaje")
    ]

    # Llamamos al modelo (con el dominio de la conversacion, si lo tiene)
    texto = llamar_llm(
        intencion,
        mensaje.texto,
        historico,
        contexto,
        dominio=conversacion.dominio or None,
    )
    return texto.strip()

# Solo permitimos una respuesta por mensaje
def guardar_respuesta_bot(mensaje_usuario, texto):

    conversacion = mensaje_usuario.conversacion

    with transaction.atomic():
        Conversacion.objects.select_for_update().get(pk=conversacion.pk)

        ultimo = conversacion.ultimoMensaje()
        if ultimo.pk != mensaje_usuario.pk:
            return ultimo

        return Mensaje.objects.create(
            conversacion=conversacion,
            texto=texto,
            remitente="chatbot"
        )

# Extraer y crear Pedido automáticamente si hay datos suficientes
def crear_pedido_si_completo(conversacion):
    """
    Intenta crear Pedido si la conversación tiene intención de compra
    y hay información suficiente en los mensajes.
    """
    from chat.models import Pedido, Servicio
    
    # Si ya existe pedido, no hacer nada
    if conversacion.conversacion_pedido.exists():
        return None
    
    # Solo para conversaciones con intención de compra
    if not conversacion.tenemosCompra:
        return None
    
    # Analizar mensajes del cliente para extraer datos
    mensajes_cliente = conversacion.conversacion_mensajes.filter(remitente="usuario")
    if not mensajes_cliente.exists():
        return None
    
    # Usar NLP para extraer entidades de los mensajes
    from core.acceso import get_nlp
    nlp = get_nlp()
    
    datos_extraidos = {
        "nombre": None,
        "direccion": None,
        "servicio": None,
        "presupuesto": None,
        "forma_contacto": None,
    }
    
    # Buscar servicio detectado en análisis
    servicio_detectado = None
    for mensaje in conversacion.conversacion_mensajes.all():
        analisis = getattr(mensaje, "mensaje_analisis", None)
        if analisis and analisis.intencion and analisis.intencion.nombre == "compra":
            servicio_detectado = analisis.detectar_servicio()
            if servicio_detectado:
                datos_extraidos["servicio"] = servicio_detectado
                break
    
    # Si no hay servicio detectado, usar el primero disponible
    if not datos_extraidos["servicio"]:
        datos_extraidos["servicio"] = Servicio.objects.first()
    
    # Extraer presupuesto de los mensajes
    import re
    for mensaje in mensajes_cliente:
        texto = mensaje.texto
        # Buscar montos en euros (con o sin espacio antes de €)
        montos = re.findall(r'(\d[\d.,]*)\s*€', texto)
        # También buscar formato "5000 euros" o "5000 eur"
        if not montos:
            montos = re.findall(r'(\d[\d.,]*)\s*(?:euros?|eur\b)', texto, re.IGNORECASE)
        if montos:
            try:
                # Tomar el último monto mencionado
                monto_str = montos[-1].replace('.', '').replace(',', '.')
                datos_extraidos["presupuesto"] = float(monto_str)
            except:
                pass
        
        # Buscar email
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', texto)
        if emails:
            datos_extraidos["forma_contacto"] = emails[-1]
        
        # Buscar teléfono
        telefonos = re.findall(r'(\+?\d[\d\s\-]{8,})', texto)
        if telefonos and not datos_extraidos["forma_contacto"]:
            datos_extraidos["forma_contacto"] = telefonos[-1].strip()
        
        # Buscar nombre de empresa (patrones comunes)
        if not datos_extraidos["nombre"]:
            # Buscar "empresa X", "mi empresa X", "nombre X"
            for pattern in [r'empresa\s+([A-Za-zÁÉÍÓÚáéíóúñÑ0-9\s]+)', r'mi empresa\s+([A-Za-zÁÉÍÓÚáéíóúñÑ0-9\s]+)', r'nombre\s+([A-Za-zÁÉÍÓÚáéíóúñÑ0-9\s]+)']:
                match = re.search(pattern, texto, re.IGNORECASE)
                if match:
                    datos_extraidos["nombre"] = match.group(1).strip()[:100]
                    break
        
        # Buscar dirección
        if not datos_extraidos["direccion"]:
            for pattern in [r'direcci[oó]n\s+([^,]+)', r'ubicad[ao]\s+([^,]+)', r'calle\s+([^,]+)']:
                match = re.search(pattern, texto, re.IGNORECASE)
                if match:
                    datos_extraidos["direccion"] = match.group(1).strip()[:100]
                    break
    
    # Si tenemos lo mínimo (servicio + presupuesto), crear pedido
    # Contacto es opcional (usamos placeholder si no hay)
    # Nombre y dirección usan placeholders si no están
    if datos_extraidos["servicio"]:
        nombre = datos_extraidos["nombre"] or "Cliente potencial"
        direccion = datos_extraidos["direccion"] or "Por confirmar"
        forma_contacto = datos_extraidos["forma_contacto"] or "Por facilitar"
        presupuesto = datos_extraidos["presupuesto"] or 0
        
        try:
            pedido = Pedido.objects.create(
                conversacion=conversacion,
                nombre=nombre,
                direccion=direccion,
                servicio=datos_extraidos["servicio"],
                presupuesto=presupuesto,
                forma_contacto=forma_contacto,
            )
            logger.info(f"Pedido auto-creado #{pedido.pk} para conversación {conversacion.pk}")
            return pedido
        except Exception as e:
            logger.warning(f"Error auto-creando pedido: {e}")
    
    return None


# Verifica si el pedido tiene todos los datos mínimos requeridos
def _pedido_tiene_datos_minimos(conversacion):
    """Verifica si el pedido tiene los campos mínimos requeridos (presupuesto y contacto)"""
    if not conversacion.conversacion_pedido.exists():
        return False
    pedido = conversacion.conversacion_pedido.first()
    # Verificar que tiene presupuesto (>0) y forma de contacto
    tiene_presupuesto = pedido.presupuesto and pedido.presupuesto > 0
    tiene_contacto = pedido.forma_contacto and pedido.forma_contacto != "Por facilitar"
    return tiene_presupuesto and tiene_contacto


# Funcion a llamar para generar una respuesta
def responder(mensaje, analisis=None):
    if analisis is None:
        analisis = procesar_mensaje(mensaje)
    nombre = analisis.intencion.nombre if (analisis.intencion and analisis.intencion.nombre) else "otro"
    logger.info("RESPONDER mensaje_id=%s intencion=%s", mensaje.pk, nombre)

    # Intentar crear pedido automáticamente si no existe aún.
    # Lo hacemos si ya hay intención de compra marcada o si la intención
    # del mensaje es de las que pueden generar un pedido.
    intenciones_con_pedido = {"compra", "contactar_humano", "confirmacion"}
    hay_intencion_compra = (
        mensaje.conversacion.tenemosCompra or nombre in intenciones_con_pedido
    )
    if hay_intencion_compra and not mensaje.conversacion.conversacion_pedido.exists():
        crear_pedido_si_completo(mensaje.conversacion)

    if nombre == "compra":
        mensaje.conversacion.tenemosCompra = True
        mensaje.conversacion.save(update_fields=["tenemosCompra"])
        # Sin return: marcamos la compra y seguimos abajo para generar la
        # respuesta con el llm (antes devolvia None y la view petaba).

    elif nombre == "cerrar":
        respuesta = guardar_respuesta_bot(mensaje, "¡Gracias por contactar con nosotros! Hasta pronto.")
        confirmamos_cierre(mensaje.conversacion)   # cerramos DESPUÉS de guardar la respuesta

        # El resumen y su correo los gestiona el signal al_cerrar_conversacion (notificaciones)
        return respuesta

    elif nombre == "contactar_humano":
        # ANTES de derivar a humano, verificar si tenemos TODOS los datos requeridos
        conversacion = mensaje.conversacion

        # Intentar crear/actualizar pedido con datos disponibles
        crear_pedido_si_completo(conversacion)

        # Verificar si el pedido tiene TODOS los datos mínimos
        if not _pedido_tiene_datos_minimos(conversacion):
            # Faltan datos, pedirlos antes de derivar
            pedido = conversacion.conversacion_pedido.first() if conversacion.conversacion_pedido.exists() else None
            faltantes = []
            if not pedido or not (pedido.presupuesto and pedido.presupuesto > 0):
                faltantes.append("presupuesto")
            if not pedido or not pedido.forma_contacto or pedido.forma_contacto == "Por facilitar":
                faltantes.append("email o teléfono de contacto")
            if not pedido or not pedido.direccion or pedido.direccion == "Por confirmar":
                faltantes.append("dirección")

            mensaje_faltantes = ", ".join(faltantes)
            respuesta = guardar_respuesta_bot(
                mensaje,
                (
                    "Para ponerle en contacto con un agente humano, necesito sus datos de contacto.\n"
                    f"Faltan los siguientes datos: {mensaje_faltantes}.\n\n"
                    "Por favor, proporcióneme:\n"
                    "- Nombre de la empresa o su nombre\n"
                    "- Email o teléfono de contacto\n"
                    "- Dirección (opcional)\n"
                    "- Presupuesto estimado\n\n"
                    "Una vez tenga estos datos, le conectaré con un agente humano."
                ),
            )
            return respuesta
        else:
            # Ya tenemos todos los datos, derivar directamente
            respuesta = guardar_respuesta_bot(
                mensaje,
                "Le conecto con un agente humano. Un momento por favor."
            )
            # Marcar para transferencia (la view manejará el estado)
            return respuesta

    # Cualquier otra intencion (incluida "compra") se responde con el llm
    servicio = analisis.detectar_servicio()

    # Timeout más largo para LLM y mejor manejo de error
    try:
        texto_respuesta = generar_respuesta_llm(mensaje, analisis, servicio)
        if not texto_respuesta:
            raise ValueError("LLM devolvió respuesta vacía")
    except Exception as e:
        logger.error(f"Error generando respuesta LLM: {e}")
        # Respuesta de fallback según intención
        fallbacks = {
            "compra": "Entendido. Para darle un presupuesto preciso, necesito algunos datos más. ¿Podría indicarme el nombre de su empresa, dirección y un email o teléfono de contacto?",
            "consulta_tecnica": "Le agradezco su consulta. Para ayudarle mejor, ¿podría indicarme su email o teléfono para que nuestro equipo técnico le contacte?",
            "contactar_humano": "Para conectarle con un agente, necesito su email o teléfono de contacto.",
            "otro": "Gracias por su mensaje. ¿En qué más puedo ayudarle?",
        }
        texto_respuesta = fallbacks.get(nombre, "Ha habido un error procesando su mensaje. ¿Podría intentarlo de nuevo?")

    return guardar_respuesta_bot(mensaje, texto_respuesta)


# Promovemos nuestros mensajes a ejemplos
def promover_analisis_a_ejemplo(analisis, origen="chatbot"):

    # El nuevo ejemplo
    ejemplo = EjemploNLP.objects.create(
        mensaje=analisis.mensaje,
        intencion=analisis.intencion,
        origen=origen,
    )

    # Las etiquetas
    spans = [
        SpanEntidad(
            ejemplo=ejemplo,
            etiqueta=entidad.etiqueta,
            inicio=entidad.inicio,
            fin=entidad.fin,
        )
        for entidad in analisis.analisis_entidad.all()
    ]

    # Guardamos los datos
    SpanEntidad.objects.bulk_create(spans)
    return ejemplo
