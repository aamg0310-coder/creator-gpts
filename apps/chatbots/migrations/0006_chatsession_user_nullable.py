# Generated manually for Phase 2 security fixes
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('chatbots', '0005_chatbot_docs_multiple'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatsession',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='chat_sessions', to='users.user', verbose_name='usuario'),
        ),
    ]
