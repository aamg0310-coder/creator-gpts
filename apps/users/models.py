"""Custom User model for chatbot-creator."""
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.validators import validate_file_size


class User(AbstractUser):
    """
    Custom User model with email login and role-based access.
    """
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('creator', 'Creador'),
        ('user', 'Usuario'),
    ]

    email = models.EmailField(
        'correo electrónico',
        unique=True,
        help_text='Se usa como identificador de login.'
    )
    role = models.CharField(
        'rol',
        max_length=10,
        choices=ROLE_CHOICES,
        default='user',
    )
    bio = models.TextField(
        'biografía',
        blank=True,
        default='',
    )
    avatar = models.ImageField(
        'avatar',
        upload_to='avatars/',
        blank=True,
        null=True,
        validators=[validate_file_size],
    )
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('última actualización', auto_now=True)

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    @property
    def is_creator(self):
        """Check if user has creator or admin role."""
        return self.role in ('creator', 'admin')

    @property
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'

    @property
    def can_create_chatbot(self):
        """Check if user can create chatbots."""
        return self.role in ('creator', 'admin')
