"""Remove unique_active_session constraint to allow multiple sessions per chatbot/user."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbots', '0008_remove_documentacion'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterModelOptions(
                    name='chatsession',
                    options={
                        'ordering': ['-updated_at'],
                        'verbose_name': 'sesión de chat',
                        'verbose_name_plural': 'sesiones de chat',
                    },
                ),
                migrations.AlterIndexTogether(
                    name='chatsession',
                    index_together=set(),
                ),
                migrations.AddIndex(
                    model_name='chatsession',
                    index=models.Index(
                        fields=['chatbot', 'user', 'updated_at'],
                        name='cs_chatbot_user_upd_idx'
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
