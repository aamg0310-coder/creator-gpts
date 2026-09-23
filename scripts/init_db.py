#!/usr/bin/env python
"""
Initialize database with sample data.
Run: python scripts/init_db.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()


def init_database():
    """Initialize database with sample data."""
    from apps.users.models import User
    from apps.chatbots.models import Chatbot

    import secrets
    import string

    def generate_password(length=16):
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    # Create superuser if not exists
    if not User.objects.filter(username='admin').exists():
        admin_password = generate_password()
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password=admin_password,
            role='admin',
        )
        print(f'✅ Superuser created: admin / {admin_password}')
    else:
        print('ℹ️  Superuser already exists')

    # Create creator user
    if not User.objects.filter(username='creator').exists():
        creator_password = generate_password()
        creator = User.objects.create_user(
            username='creator',
            email='creator@example.com',
            password=creator_password,
            role='creator',
        )
        print(f'✅ Creator user created: creator / {creator_password}')
    else:
        print('ℹ️  Creator user already exists')

    # Create regular user
    if not User.objects.filter(username='user').exists():
        user_password = generate_password()
        user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password=user_password,
            role='user',
        )
        print(f'✅ Regular user created: user / {user_password}')
    else:
        print('ℹ️  Regular user already exists')

    # Create sample chatbot
    creator = User.objects.get(username='creator')
    if not Chatbot.objects.filter(slug='chatbot-de-ejemplo').exists():
        chatbot = Chatbot.objects.create(
            nombre='Chatbot de Ejemplo',
            descripcion='Un chatbot de ejemplo para probar la plataforma.',
            modelo='openai/gpt-4o-mini',
            instructions='Eres un asistente útil y amigable. Responde en español.',
            creador=creator,
            is_public=True,
        )
        print(f'✅ Sample chatbot created: {chatbot.share_url}')
    else:
        print('ℹ️  Sample chatbot already exists')

    print('\n🎉 Database initialization complete!')
    print('\n📊 Users:')
    for user in User.objects.all():
        print(f'   - {user.username} ({user.role})')
    print(f'\n🤖 Chatbots: {Chatbot.objects.count()}')


if __name__ == '__main__':
    init_database()
