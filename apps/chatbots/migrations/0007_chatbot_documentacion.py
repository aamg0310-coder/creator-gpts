# Migration for documentacion field restoration
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('chatbots', '0006_chatsession_user_nullable'),
    ]
    operations = [
        migrations.AddField(
            model_name='chatbot',
            name='documentacion',
            field=models.TextField(blank=True, default='', verbose_name='documentación'),
        ),
    ]
