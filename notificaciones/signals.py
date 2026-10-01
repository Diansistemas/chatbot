import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from chat.models import Conversacion
from notificaciones.models import clasificar_conversacion, crear_resumen, enviar_resumen

logger = logging.getLogger(__name__)


# Se lanza cada vez que se guarda una conversacion
# Nos fijamos en los cierres: si hay intencion de compra,
# clasificamos, generamos el resumen y lo mandamos por correo
@receiver(post_save, sender=Conversacion)
def al_cerrar_conversacion(sender, instance, created, update_fields, **kwargs):

    # Una conversacion recien creada aun no esta cerrada
    if created:
        return

    # Solo nos interesa el cierre
    if instance.estado != "cerrada":
        return

    try:
        # Evitamos duplicados: si ya tiene resumen, no repetimos el envio
        if instance.resumenes.exists():
            return

        # 1) Clasificamos ANTES de generar nada
        if not clasificar_conversacion(instance):
            logger.info(
                "Conversacion %s cerrada sin intencion de compra; no se envia resumen",
                instance.pk,
            )
            return

        # 2) Generamos el resumen y lo marcamos como compra
        resumen = crear_resumen(instance)
        resumen.tipo = "compra"
        resumen.save(update_fields=["tipo"])

        # 3) Lo mandamos por correo
        if enviar_resumen(resumen):
            logger.info("Resumen de la conversacion %s enviado", instance.pk)
        else:
            logger.warning("No se pudo enviar el resumen de la conversacion %s", instance.pk)

    except Exception:
        # Un fallo en el correo no debe romper el cierre de la conversacion
        logger.exception("Error generando el resumen de la conversacion %s", instance.pk)
