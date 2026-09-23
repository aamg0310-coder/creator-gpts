"""Core views - health check, stats, and page views."""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.chatbots.models import Chatbot, ChatSession, ChatMessage
from apps.core.constants import FREE_MODELS


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint."""
    return Response({'status': 'healthy'})


@api_view(['GET'])
@permission_classes([AllowAny])
def stats_view(request):
    """Stats endpoint - returns basic platform statistics."""
    from apps.chatbots.models import ChatSession, ChatMessage
    from apps.users.models import User

    stats = {
        'total_users': User.objects.count(),
        'total_chatbots': Chatbot.objects.count(),
        'public_chatbots': Chatbot.objects.filter(is_public=True).count(),
        'total_sessions': ChatSession.objects.count(),
        'total_messages': ChatMessage.objects.count(),
    }
    return Response(stats)


# ─── Page Views ─────────────────────────────────────────────────────────────

def home_view(request):
    """Home page with concierge chat context."""
    general_slug = ''
    try:
        if request.user.is_authenticated and hasattr(request.user, 'general_chatbot'):
            general_slug = request.user.general_chatbot.slug
    except Exception:
        pass
    return render(request, 'pages/home.html', {
        'general_chatbot_slug': general_slug,
        'user_is_authenticated': request.user.is_authenticated,
    })


@login_required
def create_chatbot_view(request):
    """Page for creating a new chatbot."""
    return render(request, 'pages/create_chatbot.html')


@login_required
def edit_chatbot_view(request, slug):
    """Page for editing an existing chatbot."""
    chatbot = get_object_or_404(Chatbot, slug=slug)

    # Check permission
    if chatbot.creador != request.user and not request.user.is_admin:
        messages.error(request, 'No tienes permiso para editar este chatbot.')
        return redirect('my_chatbots')

    chatbot_is_free = chatbot.modelo in FREE_MODELS
    return render(request, 'pages/edit_chatbot.html', {
        'chatbot': chatbot,
        'chatbot_is_free': chatbot_is_free,
        'free_models': FREE_MODELS,
    })


@login_required
def chatbot_chat_view(request, slug):
    """Dedicated page for chatting with a chatbot."""
    chatbot = get_object_or_404(Chatbot, slug=slug)

    # Check access: creator, shared users, or public
    if not chatbot.is_public:
        if chatbot.creador != request.user and not request.user.is_admin:
            if request.user not in chatbot.shared_with.all():
                messages.error(request, 'No tienes acceso a este chatbot.')
                return redirect('my_chatbots')

    chatbot_is_free = chatbot.modelo in FREE_MODELS

    # Load all past sessions for this chatbot (history sidebar)
    past_sessions = []
    if request.user.is_authenticated:
        sessions_qs = (
            ChatSession.objects
            .filter(chatbot=chatbot, user=request.user)
            .order_by('-updated_at')
        )
        for s in sessions_qs[:20]:  # Limit to 20 most recent
            first_msg = (
                ChatMessage.objects
                .filter(session=s, is_user=True)
                .order_by('timestamp')
                .values_list('contenido', flat=True)
                .first()
            )
            msg_count = ChatMessage.objects.filter(session=s).count()
            past_sessions.append({
                'id': s.id,
                'preview': (first_msg or 'Nueva conversación')[:60],
                'message_count': msg_count,
                'updated_at': s.updated_at,
            })

    # Load existing session and messages
    existing_session = None
    existing_messages = []

    # Support ?session=ID to load a specific session
    session_id_param = request.GET.get('session')
    if session_id_param and request.user.is_authenticated:
        try:
            specific_session = ChatSession.objects.get(
                id=session_id_param, chatbot=chatbot, user=request.user
            )
            existing_session = specific_session
        except (ChatSession.DoesNotExist, ValueError):
            pass

    if not existing_session:
        session = (
            ChatSession.objects
            .filter(chatbot=chatbot, user=request.user)
            .order_by('-updated_at')
            .first()
        )
        if session:
            existing_session = session

    if existing_session:
        existing_messages = list(
            ChatMessage.objects.filter(session=existing_session)
            .order_by('timestamp')
            .values('contenido', 'is_user', 'timestamp')
        )

    return render(request, 'pages/chatbot_chat.html', {
        'chatbot': chatbot,
        'chatbot_is_free': chatbot_is_free,
        'existing_session_id': existing_session.id if existing_session else None,
        'existing_messages': existing_messages,
        'past_sessions': past_sessions,
    })
