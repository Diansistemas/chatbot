from django.apps import AppConfig


class NotificacionesConfig(AppConfig):
    name = 'notificaciones'

    # Cargamos los signals de la app
    def ready(self):
        from notificaciones import signals  # noqa: F401
