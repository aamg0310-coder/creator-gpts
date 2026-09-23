"""Remove acciones field and add ChatbotTemplate model."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chatbots', '0010_drop_unique_constraint'),
    ]

    operations = [
        # Remove acciones field from Chatbot
        migrations.RemoveField(
            model_name='chatbot',
            name='acciones',
        ),
        # Add ChatbotTemplate model
        migrations.CreateModel(
            name='ChatbotTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200, verbose_name='nombre', help_text='Nombre de la plantilla.')),
                ('icon', models.CharField(default='🤖', max_length=10, verbose_name='icono', help_text='Emoji representativo.')),
                ('descripcion', models.TextField(blank=True, default='', verbose_name='descripción')),
                ('soul', models.TextField(blank=True, default='', verbose_name='alma')),
                ('instructions', models.TextField(blank=True, default='', verbose_name='instrucciones')),
                ('funciones', models.JSONField(blank=True, default=list, verbose_name='funciones')),
                ('modelo', models.CharField(default='openai/gpt-4o-mini', max_length=100, verbose_name='modelo')),
                ('is_public', models.BooleanField(default=False, verbose_name='es público', help_text='Si es público, otros usuarios pueden usarla.')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='última actualización')),
                ('creador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chatbot_templates', to=settings.AUTH_USER_MODEL, verbose_name='creador')),
            ],
            options={
                'verbose_name': 'plantilla de chatbot',
                'verbose_name_plural': 'plantillas de chatbots',
                'ordering': ['-created_at'],
            },
        ),
    ]
