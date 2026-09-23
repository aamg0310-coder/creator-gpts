from django.db import migrations, models
import django.core.validators

class Migration(migrations.Migration):
    dependencies = [
        ('chatbots', '0004_manual_updates'),
    ]
    operations = [
        migrations.RemoveField(
            model_name='chatbot',
            name='documentacion',
        ),
        migrations.CreateModel(
            name='ChatbotDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(blank=True, help_text='Archivo de documentación (pdf, json, docx, doc, txt, works, rtf, etc.).', upload_to='chat_docs/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'json', 'docx', 'txt', 'doc', 'rtf', 'works'])], verbose_name='archivo')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='fecha de subida')),
                ('chatbot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='chatbots.chatbot', verbose_name='chatbot')),
            ],
            options={
                'verbose_name': 'documento de chatbot',
                'verbose_name_plural': 'documentos de chatbots',
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
