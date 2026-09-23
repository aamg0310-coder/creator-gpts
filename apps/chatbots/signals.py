"""Signals to auto-create GeneralChatbot for users and sync RAG memory on document changes."""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.users.models import User
from .models import GeneralChatbot, ChatbotDocument, Chatbot
from .memory_service import ChatbotMemoryService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_general_chatbot(sender, instance, created, **kwargs):
    """Auto-create a GeneralChatbot when a new user is registered."""
    if created:
        GeneralChatbot.objects.get_or_create(user=instance, defaults={
            'nombre': 'Asistente General',
            'slug': f"asistente-{instance.username or instance.pk}"
        })


@receiver(post_save, sender=Chatbot)
def sync_memory_on_chatbot_save(sender, instance, created, **kwargs):
    """Rebuild RAG memory (AGENTS.md) when a chatbot is saved.

    This ensures soul, instructions, funciones, etc. are always synced
    to the vector DB so the LLM retrieves them on every query.
    """
    try:
        ChatbotMemoryService.sync_memory(
            instance,
            user_id=str(instance.creador.id) if instance.creador else None
        )
    except Exception as e:
        logger.warning(f"Memory sync on chatbot save failed for {instance.nombre}: {e}")


@receiver(post_save, sender=ChatbotDocument)
def sync_memory_on_document_upload(sender, instance, created, **kwargs):
    """Rebuild RAG memory when a document is uploaded."""
    if created:
        try:
            ChatbotMemoryService.sync_memory(
                instance.chatbot,
                user_id=str(instance.chatbot.creador.id) if instance.chatbot.creador else None
            )
        except Exception as e:
            logger.warning(f"Memory sync on doc upload failed: {e}")


@receiver(post_delete, sender=ChatbotDocument)
def sync_memory_on_document_delete(sender, instance, **kwargs):
    """Rebuild RAG memory when a document is deleted."""
    try:
        ChatbotMemoryService.sync_memory(
            instance.chatbot,
            user_id=str(instance.chatbot.creador.id) if instance.chatbot.creador else None
        )
    except Exception as e:
        logger.warning(f"Memory sync on doc delete failed: {e}")
