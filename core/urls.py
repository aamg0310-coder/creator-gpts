"""
URL configuration for core project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.core.views import health_check, stats_view

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Health check & stats
    path('health/', health_check, name='health_check'),
    path('api/stats/', stats_view, name='stats'),

    # Pages - MAIN PAGE SHOULD COME FIRST
    path('', include('apps.core.page_urls')),

    # Auth
    path('', include('apps.users.urls')),

    # API
    path('api/', include('apps.chatbots.urls')),
]

# Shareable chatbot URLs (MUST come AFTER all other routes)
urlpatterns += [
    path('', include('apps.chatbots.share_urls')),
]

# Media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
