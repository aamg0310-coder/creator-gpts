"""Views for chatbots app."""
import json
import logging
from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

from .models import Chatbot, ChatSession, ChatMessage, GeneralChatbot, ChatbotTemplate
from .serializers import (
    ChatbotSerializer, ChatbotListSerializer,
    ChatSessionSerializer, ChatSessionListSerializer,
    ChatMessageSerializer, AskSerializer, ChatbotTemplateSerializer
)
from .permissions import IsCreatorOrReadOnlyIfShared
from django.http import StreamingHttpResponse
from .services import RagService

logger = logging.getLogger(__name__)


def chatbot_share_view(request, slug):
    """Shareable view for any chatbot (public or private by URL)."""
    chatbot = get_object_or_404(Chatbot, slug=slug)
    return render(request, 'pages/chatbot_share.html', {'chatbot': chatbot})


@api_view(['POST'])
@permission_classes([AllowAny])
def home_ask(request):
    """Concierge endpoint for the home chat (GeneralChatbot or anonymous)."""
    serializer = AskSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    question = serializer.validated_data['question']

    if request.user.is_authenticated:
        try:
            chatbot = request.user.general_chatbot
        except GeneralChatbot.DoesNotExist:
            chatbot, _ = GeneralChatbot.objects.get_or_create(
                user=request.user,
                defaults={'nombre': 'Asistente General'}
            )
            if not chatbot.slug or chatbot.slug == 'asistente-general':
                chatbot.save()
            chatbot.refresh_from_db()

        # GeneralChatbot uses a different model, so session/messages
        # must be handled separately (or skipped for simplicity).
        if type(chatbot).__name__ == 'GeneralChatbot':
            answer = RagService.answer(chatbot, question, session=None)
            return Response({'answer': answer, 'session_id': None})

        session, _ = ChatSession.objects.get_or_create(chatbot=chatbot, user=request.user)
        ChatMessage.objects.create(session=session, contenido=question, is_user=True)
        answer = RagService.answer(chatbot, question, session=session)
        if not answer:
            answer = "Lo siento, hubo un error al procesar tu pregunta. Por favor, intenta de nuevo."
        ChatMessage.objects.create(session=session, contenido=answer, is_user=False)
        session.save(update_fields=['updated_at'])
        return Response({'answer': answer, 'session_id': session.id})

    # Anonymous: generic concierge message
    return Response({
        'answer': (
            "Soy el Asistente General de GPT Creator. Puedo ayudarte a crear chatbots de IA, "
            "explorar modelos (GPT-4o, Claude, Llama, Gemini, DeepSeek), usar RAG con documentos "
            "y buscar chatbots públicos. Inicia sesión o regístrate para acceder a tu asistente personalizado."
        ),
        'session_id': None,
    })


class ChatbotViewSet(viewsets.ModelViewSet):
    """
    API endpoint for chatbots.

    list:
    - Public: returns public chatbots
    - Authenticated: returns own + shared + public chatbots

    create:
    - Requires can_create_chatbot permission
    """
    lookup_field = 'slug'

    def get_queryset(self):
        user = self.request.user
        search_query = self.request.query_params.get('search', '').strip()
        if user.is_authenticated:
            qs = Chatbot.objects.filter(
                Q(creador=user) |
                Q(shared_with=user) |
                Q(is_public=True)
            ).distinct().select_related('creador').prefetch_related('shared_with')
        else:
            qs = Chatbot.objects.filter(is_public=True).select_related('creador')
        if search_query:
            qs = qs.filter(nombre__icontains=search_query)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return ChatbotListSerializer
        return ChatbotSerializer

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [AllowAny]
        elif self.action == 'ask':
            # Allow anonymous users to ask on public chatbots
            permission_classes = [AllowAny]
        elif self.action == 'retrieve':
            permission_classes = [IsAuthenticated, IsCreatorOrReadOnlyIfShared]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated, IsCreatorOrReadOnlyIfShared]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        # Signal (sync_memory_on_chatbot_save) handles memory sync automatically
        serializer.save(creador=self.request.user)


    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        # Signal (sync_memory_on_chatbot_save) handles memory sync automatically
        chatbot = serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def share(self, request, slug=None):
        """Share chatbot with other users."""
        chatbot = self.get_object()
        shared_with_ids = request.data.get('shared_with', [])
        is_public = request.data.get('is_public', chatbot.is_public)

        if shared_with_ids:
            from apps.users.models import User
            users = User.objects.filter(id__in=shared_with_ids)
            chatbot.shared_with.set(users)

        chatbot.is_public = is_public
        chatbot.save()

        serializer = ChatbotSerializer(chatbot, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def ask(self, request, slug=None):
        """Ask a question to the chatbot."""
        chatbot = self.get_object()

        # Verify the user has access to this chatbot
        if not chatbot.is_public:
            if not request.user.is_authenticated:
                return Response(
                    {'detail': 'Se requiere autenticación para este chatbot.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if (chatbot.creador != request.user
                    and not request.user.is_admin
                    and request.user not in chatbot.shared_with.all()):
                return Response(
                    {'detail': 'No tienes acceso a este chatbot.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = AskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data['question']

        # Get or create session
        user_for_session = request.user if request.user.is_authenticated else None
        session_id = request.data.get('session_id')

        if session_id and request.user.is_authenticated:
            try:
                # Filter by user to enforce session privacy
                session = ChatSession.objects.get(
                    id=session_id, chatbot=chatbot, user=user_for_session
                )
            except ChatSession.DoesNotExist:
                session = self._get_or_create_session(chatbot, user_for_session)
        else:
            session = self._get_or_create_session(chatbot, user_for_session)

        # Save user message. Skip when this is a retry of an unanswered
        # question (e.g. after an interrupted stream) to avoid duplicates.
        if not self._is_unanswered_retry(session, question):
            ChatMessage.objects.create(
                session=session,
                contenido=question,
                is_user=True,
            )

        # Get RAG response (with conversation history)
        answer = RagService.answer(chatbot, question, session=session)

        # Ensure answer is never None (NOT NULL constraint on ChatMessage)
        if not answer:
            answer = "Lo siento, hubo un error al procesar tu pregunta. Por favor, intenta de nuevo."

        # Save assistant message
        ChatMessage.objects.create(
            session=session,
            contenido=answer,
            is_user=False,
        )

        # Touch session to update updated_at (keeps it at top of sidebar)
        session.save(update_fields=['updated_at'])

        return Response({
            'answer': answer,
            'session_id': session.id,
        })

    @action(detail=True, methods=['post'])
    def ask_stream(self, request, slug=None):
        """Streaming SSE endpoint for chatbot questions."""
        chatbot = self.get_object()

        if not chatbot.is_public:
            if not request.user.is_authenticated:
                return Response(
                    {'detail': 'Se requiere autenticación para este chatbot.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if (chatbot.creador != request.user
                    and not request.user.is_admin
                    and request.user not in chatbot.shared_with.all()):
                return Response(
                    {'detail': 'No tienes acceso a este chatbot.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = AskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.validated_data['question']

        user_for_session = request.user if request.user.is_authenticated else None
        session_id = request.data.get('session_id')

        if session_id and request.user.is_authenticated:
            try:
                session = ChatSession.objects.get(
                    id=session_id, chatbot=chatbot, user=user_for_session
                )
            except ChatSession.DoesNotExist:
                session = self._get_or_create_session(chatbot, user_for_session)
        else:
            session = self._get_or_create_session(chatbot, user_for_session)

        # Save user message (same dedupe rule as the non-streaming endpoint)
        if not self._is_unanswered_retry(session, question):
            ChatMessage.objects.create(
                session=session, contenido=question, is_user=True,
            )

        history = RagService.load_conversation_history(session)
        documents = RagService.retrieve_documents(chatbot.id, question)

        # Retrieve bot memory from vector DB (AGENTS.md equivalent)
        from .insforge_client import InsForgeClient
        bot_memory = InsForgeClient.retrieve_bot_memory(chatbot.id)

        model = getattr(chatbot, 'modelo', '') or 'meta-llama/llama-3.1-8b-instruct'
        soul = getattr(chatbot, 'soul', '') or ''
        instructions = getattr(chatbot, 'instructions', '') or ''
        # Internet disabled: only user-uploaded documents + bot memory allowed

        full_answer = []

        def event_stream():
            saved = False
            try:
                for token in RagService.generate_response_stream(
                    question=question,
                    documents=documents,
                    history=history,
                    soul=soul,
                    instructions=instructions,
                    model=model,
                    bot_memory=bot_memory,
                ):
                    full_answer.append(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"
                # Normal completion: persist the answer BEFORE signalling done
                assistant_text = ''.join(full_answer).strip()
                if assistant_text:
                    ChatMessage.objects.create(
                        session=session, contenido=assistant_text, is_user=False,
                    )
                    saved = True
                session.save(update_fields=['updated_at'])
                yield f"data: {json.dumps({'done': True, 'session_id': session.id})}\n\n"
            finally:
                # Client disconnected or the stream failed mid-way: persist
                # whatever was generated so the answer survives a refresh.
                # (No yield allowed here — GeneratorExit would raise.)
                if not saved:
                    assistant_text = ''.join(full_answer).strip()
                    if assistant_text:
                        try:
                            ChatMessage.objects.create(
                                session=session, contenido=assistant_text, is_user=False,
                            )
                            session.save(update_fields=['updated_at'])
                        except Exception as exc:
                            logger.error(
                                f"Could not save partial answer for session {session.id}: {exc}"
                            )

        response = StreamingHttpResponse(
            event_stream(), content_type='text/event-stream',
        )
        # Lets the client recover the session id even if the body fails
        # mid-stream (used by the non-streaming fallback to stay in-session)
        response['X-Session-ID'] = str(session.id)
        return response

    def _get_or_create_session(self, chatbot, user):
        """Create a session for this chatbot.

        Called when the client sends no (valid) session_id: either the first
        message of a conversation or "Nueva conversación". Always creates a
        NEW session so every conversation is preserved separately in the
        history sidebar. Anonymous users get their own isolated session.
        """
        return ChatSession.objects.create(chatbot=chatbot, user=user)

    @staticmethod
    def _is_unanswered_retry(session, question):
        """True when the last message is an identical, unanswered user message.

        Happens when a previous attempt (e.g. an interrupted stream) saved the
        question but no assistant reply was stored — retrying must not create
        a duplicate row.
        """
        last = (
            ChatMessage.objects
            .filter(session=session)
            .order_by('-timestamp', '-id')
            .first()
        )
        return bool(last and last.is_user and last.contenido == question)

    @action(detail=True, methods=['post'])
    def export_session(self, request, slug=None):
        """Export chat session as Markdown or JSON."""
        chatbot = self.get_object()
        session_id = request.data.get('session_id')
        fmt = request.data.get('format', 'markdown')

        if not session_id:
            return Response({'error': 'session_id requerido'}, status=400)

        try:
            session = ChatSession.objects.get(id=session_id, chatbot=chatbot)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Sesión no encontrada'}, status=404)

        messages = ChatMessage.objects.filter(session=session).order_by('timestamp')

        if fmt == 'json':
            data = {
                'chatbot': chatbot.nombre,
                'model': chatbot.get_modelo_display(),
                'created': session.created_at.isoformat(),
                'messages': [
                    {'role': 'user' if m.is_user else 'assistant', 'content': m.contenido, 'timestamp': m.timestamp.isoformat()}
                    for m in messages
                ]
            }
            return Response(data)

        # Markdown format
        lines = [
            f'# Conversación con {chatbot.nombre}',
            f'**Modelo:** {chatbot.get_modelo_display()}',
            f'**Fecha:** {session.created_at.strftime("%d/%m/%Y %H:%M")}',
            '',
            '---',
            '',
        ]
        for m in messages:
            role = '**Tú**' if m.is_user else f'**{chatbot.nombre}**'
            lines.append(f'{role}:')
            lines.append(m.contenido)
            lines.append('')

        md = '\n'.join(lines)
        return Response({'markdown': md, 'filename': f'{chatbot.slug}-{session.id}.md'})

    @action(detail=True, methods=['delete'], url_path='delete_session')
    def delete_session(self, request, slug=None):
        """Delete a chat session and its messages."""
        chatbot = self.get_object()
        session_id = request.data.get('session_id') or request.query_params.get('session_id')

        if not session_id:
            return Response({'error': 'session_id requerido'}, status=400)

        try:
            session = ChatSession.objects.get(id=session_id, chatbot=chatbot, user=request.user)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Sesión no encontrada'}, status=404)

        session.delete()
        return Response({'success': True})

    @action(detail=True, methods=['post'])
    def upload_document(self, request, slug=None):
        """Upload a document for RAG indexing."""
        chatbot = self.get_object()
        
        # Handle both JSON (legacy) and multipart/form-data
        if 'file' in request.FILES:
            # New multipart/form-data approach
            uploaded_file = request.FILES['file']
            filename = uploaded_file.name
            
            # Extract text from file
            from .document_extract import extract_text
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            
            try:
                content = extract_text(tmp_path)
            finally:
                os.unlink(tmp_path)
            
            if not content:
                return Response(
                    {'error': 'No se pudo extraer texto del archivo. Formatos soportados: PDF, DOCX, TXT, JSON, CSV, RTF, MD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Legacy JSON approach
            filename = request.data.get('filename')
            content = request.data.get('content')
            
            if not filename or not content:
                return Response(
                    {'error': 'Se requieren filename y content (o file en multipart).'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            from .insforge_client import InsForgeClient
            user_id = str(request.user.id) if request.user.is_authenticated else None
            result = InsForgeClient.upload_documents(
                chatbot_id=chatbot.id,
                filename=filename,
                content=content,
                user_id=user_id,
            )
            if 'error' in result:
                return Response({'error': result['error']}, status=status.HTTP_502_BAD_GATEWAY)
            return Response({
                'success': True,
                'chunks_created': result.get('chunks_created', 0),
            })
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Document upload failed: {e}")
            return Response(
                {'error': 'Error al subir el documento.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['delete'], url_path='delete_documents')
    def delete_documents(self, request, slug=None):
        """Delete all RAG documents for this chatbot."""
        chatbot = self.get_object()
        try:
            from .insforge_client import InsForgeClient
            success = InsForgeClient.delete_documents(chatbot.id)
            if success:
                return Response({'success': True})
            return Response({'error': 'Error al eliminar documentos'}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Document delete failed: {e}")
            return Response({'error': 'Error al eliminar documentos'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatSessionViewSet(viewsets.ModelViewSet):
    """API endpoint for chat sessions."""
    serializer_class = ChatSessionSerializer

    def get_queryset(self):
        qs = ChatSession.objects.filter(
            user=self.request.user
        ).select_related('chatbot').prefetch_related('messages')
        # Support filtering by chatbot slug
        chatbot_slug = self.request.query_params.get('chatbot')
        if chatbot_slug:
            qs = qs.filter(chatbot__slug=chatbot_slug)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        # Support ?limit=N for sidebar (bypass pagination)
        limit = request.query_params.get('limit')
        if limit and limit.isdigit():
            qs = qs[:int(limit)]
            serializer = self.get_serializer(qs, many=True)
            return Response(serializer.data)
        # Normal paginated list
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action == 'list':
            return ChatSessionListSerializer
        return ChatSessionSerializer

    def get_permissions(self):
        return [IsAuthenticated()]


class ChatMessageViewSet(viewsets.ModelViewSet):
    """API endpoint for chat messages."""
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        session_id = self.kwargs.get('session_pk')
        return ChatMessage.objects.filter(
            session_id=session_id,
            session__user=self.request.user,
        ).select_related('session')

    def get_permissions(self):
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        session_id = self.kwargs.get('session_pk')
        session = get_object_or_404(
            ChatSession,
            id=session_id,
            user=self.request.user,
        )
        serializer.save(session=session)


class ChatbotTemplateViewSet(viewsets.ModelViewSet):
    """API endpoint for user-created chatbot templates."""
    serializer_class = ChatbotTemplateSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return ChatbotTemplate.objects.filter(
                Q(creador=user) | Q(is_public=True)
            ).select_related('creador')
        return ChatbotTemplate.objects.filter(is_public=True).select_related('creador')

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(creador=self.request.user)

    @action(detail=False, methods=['get'])
    def my_templates(self, request):
        """List only the current user's templates."""
        templates = ChatbotTemplate.objects.filter(
            creador=request.user
        ).order_by('-created_at')
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)
