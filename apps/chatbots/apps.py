from django.apps import AppConfig


class ChatbotsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.chatbots'
    verbose_name = 'Chatbots'

    def ready(self):
        import apps.chatbots.signals  # noqa
