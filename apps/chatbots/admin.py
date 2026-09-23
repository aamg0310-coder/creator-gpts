"""Admin configuration for chatbots app."""
from django.contrib import admin
from .models import Chatbot, ChatSession, ChatMessage, ChatbotTemplate


@admin.register(Chatbot)
class ChatbotAdmin(admin.ModelAdmin):
    """Chatbot admin."""
    list_display = ('nombre', 'modelo', 'creador', 'is_public', 'created_at')
    list_filter = ('modelo', 'is_public', 'created_at')
    search_fields = ('nombre', 'descripcion')
    prepopulated_fields = {'slug': ('nombre',)}
    raw_id_fields = ('creador',)
    filter_horizontal = ('shared_with',)
    readonly_fields = ('slug', 'created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('nombre', 'slug', 'descripcion')
        }),
        ('Modelo', {
            'fields': ('modelo', 'instructions')
        }),
        ('Permisos', {
            'fields': ('creador', 'is_public', 'shared_with')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class ChatMessageInline(admin.TabularInline):
    """Inline for chat messages."""
    model = ChatMessage
    extra = 0
    readonly_fields = ('contenido', 'is_user', 'timestamp')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """Chat session admin."""
    list_display = ('chatbot', 'user', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    raw_id_fields = ('chatbot', 'user')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Chat message admin."""
    list_display = ('session', 'is_user', 'contenido_short', 'timestamp')
    list_filter = ('is_user', 'timestamp')
    raw_id_fields = ('session',)
    readonly_fields = ('timestamp',)
    search_fields = ('contenido',)

    def contenido_short(self, obj):
        return obj.contenido[:100] + '...' if len(obj.contenido) > 100 else obj.contenido
    contenido_short.short_description = 'Contenido'


@admin.register(ChatbotTemplate)
class ChatbotTemplateAdmin(admin.ModelAdmin):
    """Chatbot template admin."""
    list_display = ('nombre', 'icon', 'creador', 'modelo', 'is_public', 'created_at')
    list_filter = ('is_public', 'modelo', 'created_at')
    search_fields = ('nombre', 'descripcion')
    raw_id_fields = ('creador',)
    readonly_fields = ('created_at', 'updated_at')
