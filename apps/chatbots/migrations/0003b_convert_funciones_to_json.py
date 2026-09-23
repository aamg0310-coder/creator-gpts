# Data migration: convert funciones TextField to JSONField
from django.db import migrations


def convert_funciones_to_json(apps, schema_editor):
    Chatbot = apps.get_model('chatbots', 'Chatbot')
    for chatbot in Chatbot.objects.all():
        val = chatbot.funciones
        if isinstance(val, str):
            if not val.strip():
                chatbot.funciones = []
            else:
                # Split comma-separated or keep as single item
                items = [item.strip() for item in val.split(',') if item.strip()]
                chatbot.funciones = items
            chatbot.save(update_fields=['funciones'])
        elif val is None:
            chatbot.funciones = []
            chatbot.save(update_fields=['funciones'])


def reverse_funciones(apps, schema_editor):
    Chatbot = apps.get_model('chatbots', 'Chatbot')
    for chatbot in Chatbot.objects.all():
        if isinstance(chatbot.funciones, list):
            chatbot.funciones = ', '.join(str(f) for f in chatbot.funciones)
            chatbot.save(update_fields=['funciones'])


class Migration(migrations.Migration):
    dependencies = [
        ('chatbots', '0003_chatbot_acciones_chatbot_documentacion_and_more'),
    ]
    operations = [
        migrations.RunPython(convert_funciones_to_json, reverse_funciones),
    ]
