"""Remove the unique_active_session constraint from the database."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chatbots', '0009_remove_unique_active_session'),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP INDEX IF EXISTS unique_active_session;",
            reverse_sql="-- no-op",
        ),
    ]
