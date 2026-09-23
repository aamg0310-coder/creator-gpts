"""URL configuration for chatbots app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'chatbots', views.ChatbotViewSet, basename='chatbot')
router.register(r'sessions', views.ChatSessionViewSet, basename='session')
router.register(r'templates', views.ChatbotTemplateViewSet, basename='chatbot-template')

urlpatterns = [
    path('', include(router.urls)),
    path('home/ask/', views.home_ask, name='home_ask'),
    # Nested messages under sessions
    path(
        'sessions/<int:session_pk>/messages/',
        views.ChatMessageViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='session-messages'
    ),
]
