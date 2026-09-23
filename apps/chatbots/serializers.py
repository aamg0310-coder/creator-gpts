"""Serializers for chatbots app."""
from rest_framework import serializers
from .models import Chatbot, ChatSession, ChatMessage, GeneralChatbot, ChatbotDocument, ChatbotTemplate
from apps.core.constants import FREE_MODELS


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for ChatMessage model."""
    role = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['id', 'contenido', 'is_user', 'role', 'timestamp']
        read_only_fields = ['id', 'timestamp']

    def get_role(self, obj):
        return 'user' if obj.is_user else 'assistant'


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for ChatSession model."""
    messages = ChatMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ['id', 'chatbot', 'user', 'messages', 'message_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()


class ChatSessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing sessions."""
    message_count = serializers.SerializerMethodField()
    chatbot_nombre = serializers.CharField(source='chatbot.nombre', read_only=True)
    chatbot_slug = serializers.CharField(source='chatbot.slug', read_only=True)
    preview = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ['id', 'chatbot', 'chatbot_nombre', 'chatbot_slug', 'user', 'message_count', 'preview', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_preview(self, obj):
        first_msg = obj.messages.filter(is_user=True).order_by('timestamp').values_list('contenido', flat=True).first()
        return (first_msg or 'Nueva conversación')[:60]


class ChatbotSerializer(serializers.ModelSerializer):
    """Serializer for Chatbot model."""
    modelo_display = serializers.CharField(source='get_modelo_display', read_only=True)
    model_tier = serializers.SerializerMethodField()
    creador_username = serializers.CharField(source='creador.username', read_only=True)
    share_url = serializers.ReadOnlyField()
    documents = serializers.SerializerMethodField()
    icon = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Chatbot
        fields = [
            'id', 'nombre', 'icon', 'descripcion', 'modelo', 'modelo_display',
            'model_tier', 'slug', 'soul', 'instructions',
            'suggestions', 'creador', 'creador_username',
            'documents', 'is_public', 'is_public_via_url', 'shared_with', 'share_url',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'creador', 'created_at', 'updated_at']


    def get_documents(self, obj):
        from .serializers import ChatbotDocumentSerializer
        return ChatbotDocumentSerializer(obj.documents.all(), many=True, read_only=True).data

    def get_model_tier(self, obj):
        return 'free' if obj.modelo in FREE_MODELS else 'paid'

    def create(self, validated_data):
        validated_data['creador'] = self.context['request'].user
        return super().create(validated_data)


class ChatbotListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing chatbots."""
    modelo_display = serializers.CharField(source='get_modelo_display', read_only=True)
    model_tier = serializers.SerializerMethodField()
    creador_username = serializers.CharField(source='creador.username', read_only=True)
    creador_id = serializers.IntegerField(source='creador.id', read_only=True)

    class Meta:
        model = Chatbot
        fields = [
            'id', 'nombre', 'icon', 'descripcion', 'modelo', 'modelo_display',
            'model_tier', 'slug', 'creador_username', 'creador_id', 'is_public',
            'is_public_via_url', 'created_at',
        ]


    def get_documents(self, obj):
        from .serializers import ChatbotDocumentSerializer
        return ChatbotDocumentSerializer(obj.documents.all(), many=True, read_only=True).data

    def get_model_tier(self, obj):
        return 'free' if obj.modelo in FREE_MODELS else 'paid'


class AskSerializer(serializers.Serializer):
    """Serializer for ask endpoint."""
    question = serializers.CharField(
        max_length=1000,
        help_text='Pregunta al chatbot (máx. 1000 caracteres).',
    )

    def validate_question(self, value):
        # Basic prompt-injection guard
        dangerous = ['ignore previous', 'system:', '<|end|>', '</system>', '<|im_start|>']
        lower = value.lower()
        for d in dangerous:
            if d in lower:
                raise serializers.ValidationError('Contenido no permitido en la pregunta.')
        return value

class GeneralChatbotSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    share_url = serializers.ReadOnlyField()

    class Meta:
        model = GeneralChatbot
        fields = ['id', 'nombre', 'slug', 'user', 'user_username', 'share_url', 'created_at', 'updated_at']
        read_only_fields = ['id', 'slug', 'user', 'created_at', 'updated_at']


class ChatbotDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.FileField(source='file', read_only=True)
    class Meta:
        model = ChatbotDocument
        fields = ['id', 'chatbot', 'file', 'file_url', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'file_url']


class ChatbotTemplateSerializer(serializers.ModelSerializer):
    """Serializer for user-created chatbot templates."""
    creador_username = serializers.CharField(source='creador.username', read_only=True)

    class Meta:
        model = ChatbotTemplate
        fields = [
            'id', 'nombre', 'icon', 'descripcion', 'soul', 'instructions',
            'modelo', 'creador', 'creador_username',
            'is_public', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'creador', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['creador'] = self.context['request'].user
        return super().create(validated_data)

