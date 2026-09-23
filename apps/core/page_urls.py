"""Page URLs for core views."""
from django.urls import path
from django.views.generic import TemplateView
from apps.core import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('mis-chatbots/', TemplateView.as_view(template_name='pages/my_chatbots.html'), name='my_chatbots'),
    path('recientes/', TemplateView.as_view(template_name='pages/recent.html'), name='recent'),
    path('buscar/', TemplateView.as_view(template_name='pages/search.html'), name='search'),
    path('lista-chatbots/', TemplateView.as_view(template_name='pages/chatbot_list.html'), name='chatbot_list'),
    path('account/', TemplateView.as_view(template_name='pages/account.html'), name='account'),
    # Chatbot editor pages
    path('crear-chatbot/', views.create_chatbot_view, name='create_chatbot'),
    path('editar-chatbot/<slug:slug>/', views.edit_chatbot_view, name='edit_chatbot'),
    path('chat/<slug:slug>/', views.chatbot_chat_view, name='chatbot_chat'),
]
