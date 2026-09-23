"""URL configuration for users app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'api/users', views.UserViewSet)

urlpatterns = [
    # Template views
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # API
    path('api/', include(router.urls)),
]
