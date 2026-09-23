"""Models for chatbots app."""
import uuid
from django.db import models
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
from apps.users.models import User
from apps.core.validators import validate_file_size


class Chatbot(models.Model):
    """
    Chatbot model with RAG capabilities.
    """
    MODEL_CHOICES = [
        # 🟢 Modelos gratuitos (OpenRouter)
        ('meta-llama/llama-3.1-8b-instruct', 'Llama 3.1 8B'),
        ('meta-llama/llama-3.2-3b-instruct', 'Llama 3.2 3B'),
        ('google/gemma-2-9b-it', 'Gemma 2 9B'),
        ('google/gemma-2-2b-it', 'Gemma 2 2B'),
        ('mistralai/mistral-7b-instruct', 'Mistral 7B'),
        ('qwen/qwen-2-7b-instruct', 'Qwen 2 7B'),
        ('deepseek/deepseek-chat', 'DeepSeek Chat'),
    ]

    nombre = models.CharField(
        'nombre',
        max_length=200,
        help_text='Nombre del chatbot.'
    )
    icon = models.ImageField(
        'icono',
        upload_to='chat_icons/',
        blank=True,
        null=True,
        default='',
        validators=[validate_file_size],
        help_text='Imagen representativa del chatbot (subida por el usuario).'
    )
    descripcion = models.TextField(
        'descripción',
        blank=True,
        default='',
        help_text='Descripción del chatbot.'
    )
    modelo = models.CharField(
        'modelo',
        max_length=100,
        choices=MODEL_CHOICES,
        default='meta-llama/llama-3.1-8b-instruct',
        help_text='Modelo LLM a utilizar.'
    )
    slug = models.SlugField(
        'slug',
        unique=True,
        blank=True,
        help_text='URL amigable generada automáticamente.'
    )
    soul = models.TextField(
        'alma',
        blank=True,
        default='',
        help_text='La personalidad y esencia del chatbot. ¿Quién es? ¿Cómo se comporta?'
    )
    instructions = models.TextField(
        'instrucciones',
        blank=True,
        default='',
        help_text='Instrucciones técnicas: cómo formatear respuestas, límites, reglas.'
    )
    suggestions = models.JSONField(
        'sugerencias',
        default=list,
        blank=True,
        help_text='Sugerencias para iniciar la conversación.'
    )

    creador = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chatbots_creados',
        verbose_name='creador'
    )
    is_public = models.BooleanField(
        'es público',
        default=False,
        help_text='Si es público, cualquiera puede chatear y aparecer en directorios.'
    )
    is_public_via_url = models.BooleanField(
        'visible vía URL',
        default=False,
        help_text='Si es visible vía URL, el chatbot es accesible mediante su slugaunque no sea público general. Las conversaciones siguen estando aisladas por usuario.'
    )
    shared_with = models.ManyToManyField(
        User,
        blank=True,
        related_name='chatbots_compartidos',
        verbose_name='compartido con'
    )
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('última actualización', auto_now=True)

    class Meta:
        verbose_name = 'chatbot'
        verbose_name_plural = 'chatbots'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['creador']),
            models.Index(fields=['is_public']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.get_modelo_display()})'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nombre)
            slug = base_slug
            counter = 1
            while Chatbot.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def share_url(self):
        """Return the shareable URL path."""
        return f'/{self.slug}/'


class ChatSession(models.Model):
    """
    Chat session - one active session per (chatbot, user) pair.
    """
    chatbot = models.ForeignKey(
        Chatbot,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name='chatbot'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        verbose_name='usuario',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('última actualización', auto_now=True)

    class Meta:
        verbose_name = 'sesión de chat'
        verbose_name_plural = 'sesiones de chat'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['chatbot', 'user']),
            models.Index(fields=['chatbot', 'user', 'updated_at'], name='cs_chatbot_user_upd_idx'),
        ]

    def __str__(self):
        return f'Sesión: {self.user.username} - {self.chatbot.nombre}'


class ChatMessage(models.Model):
    """
    Chat message within a session.
    """
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='sesión'
    )
    contenido = models.TextField(
        'contenido',
        help_text='Contenido del mensaje.'
    )
    is_user = models.BooleanField(
        'es usuario',
        default=True,
        help_text='True si es mensaje del usuario, False si es del asistente.'
    )
    timestamp = models.DateTimeField('marca de tiempo', auto_now_add=True)

    class Meta:
        verbose_name = 'mensaje de chat'
        verbose_name_plural = 'mensajes de chat'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['session', 'timestamp']),
        ]

    def __str__(self):
        role = 'Usuario' if self.is_user else 'Asistente'
        return f'{role}: {self.contenido[:50]}...'


class GeneralChatbot(models.Model):
    """Chatbot general automático por usuario. Solo crea/consulta chatbots propios o compartidos; nunca modifica otros."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='general_chatbot',
        verbose_name='usuario'
    )
    nombre = models.CharField('nombre', max_length=200, default='Asistente General')
    slug = models.SlugField('slug', unique=True, blank=True, default='asistente-general')
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('última actualización', auto_now=True)

    class Meta:
        verbose_name = 'chatbot general'
        verbose_name_plural = 'chatbots generales'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.nombre} ({self.user.username})'

    def save(self, *args, **kwargs):
        if not self.slug or self.slug == 'asistente-general':
            base_slug = f"asistente-{self.user.username}" if self.user.username else "asistente"
            slug = base_slug
            counter = 1
            while GeneralChatbot.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def share_url(self):
        return f'/{self.slug}/'


class ChatbotDocument(models.Model):
    """Archivo de documentación subido por el usuario al chatbot."""
    chatbot = models.ForeignKey(
        Chatbot,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='chatbot'
    )
    file = models.FileField(
        'archivo',
        upload_to='chat_docs/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'json', 'txt', 'docx', 'rtf', 'doc']),
            validate_file_size,
        ],
        help_text='Archivo de documentación (pdf, json, docx, doc, txt, works, rtf, etc.).'
    )
    uploaded_at = models.DateTimeField('fecha de subida', auto_now_add=True)

    class Meta:
        verbose_name = 'documento de chatbot'
        verbose_name_plural = 'documentos de chatbots'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.file.name} ({self.chatbot.nombre})"


class ChatbotTemplate(models.Model):
    """Plantilla personalizada creada por el usuario para reutilizar configuración de chatbots."""
    nombre = models.CharField('nombre', max_length=200, help_text='Nombre de la plantilla.')
    icon = models.CharField('icono', max_length=10, default='🤖', help_text='Emoji representativo.')
    descripcion = models.TextField('descripción', blank=True, default='')
    soul = models.TextField('alma', blank=True, default='')
    instructions = models.TextField('instrucciones', blank=True, default='')
    modelo = models.CharField('modelo', max_length=100, default='meta-llama/llama-3.1-8b-instruct')

    creador = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chatbot_templates',
        verbose_name='creador'
    )
    is_public = models.BooleanField('es público', default=False,
        help_text='Si es público, otros usuarios pueden usarla.')
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('última actualización', auto_now=True)

    class Meta:
        verbose_name = 'plantilla de chatbot'
        verbose_name_plural = 'plantillas de chatbots'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nombre} ({self.icon})"

