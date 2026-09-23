# Manual migration for backend adjustments: icons, docs, functions, suggestions, general bot
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('chatbots', '0003b_convert_funciones_to_json'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatbot',
            name='icon',
            field=models.ImageField(blank=True, default='', help_text='Imagen representativa del chatbot (subida por el usuario).', null=True, upload_to='chat_icons/', verbose_name='icono'),
        ),
        migrations.AlterField(
            model_name='chatbot',
            name='documentacion',
            field=models.FileField(blank=True, help_text='Archivos de documentación subidos por el usuario (pdf, json, docx, txt).', null=True, upload_to='chat_docs/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'json', 'docx', 'txt', 'doc'])], verbose_name='documentación'),
        ),
        migrations.AlterField(
            model_name='chatbot',
            name='funciones',
            field=models.JSONField(blank=True, default=list, help_text='Lista de funciones habilitadas: búsqueda en internet, lienzo, generación de imágenes, intérprete de código, análisis de datos.', verbose_name='funciones'),
        ),
        migrations.AddField(
            model_name='chatbot',
            name='suggestions',
            field=models.JSONField(blank=True, default=list, help_text='Sugerencias para iniciar la conversación.', verbose_name='sugerencias'),
        ),
        migrations.CreateModel(
            name='GeneralChatbot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(default='Asistente General', max_length=200, verbose_name='nombre')),
                ('slug', models.SlugField(blank=True, default='asistente-general', unique=True, verbose_name='slug')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='última actualización')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='general_chatbot', to='users.user', verbose_name='usuario')),
            ],
            options={
                'verbose_name': 'chatbot general',
                'verbose_name_plural': 'chatbots generales',
                'ordering': ['-created_at'],
            },
        ),
    ]
