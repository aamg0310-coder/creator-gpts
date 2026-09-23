"""Share URLs for public chatbot views."""
from django.urls import path
from .views import chatbot_share_view

urlpatterns = [
    path('<str:slug>/', chatbot_share_view, name='chatbot_share'),
]
