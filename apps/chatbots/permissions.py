"""Custom permissions for chatbots app."""
from rest_framework import permissions


class IsCreatorOrReadOnlyIfShared(permissions.BasePermission):
    """
    - Creator can do anything on their chatbots.
    - Shared users can read private chatbots (via URL or API).
    - Public chatbots readable by any authenticated user.
    - Private chatbots readable only by creator / shared / URL.
    - Never allows modification for anyone except creator/admin.
    """

    def has_object_permission(self, request, view, obj):
        # Must be authenticated to see any chatbot
        if not request.user or not request.user.is_authenticated:
            return False

        # Write methods: only creator or admin (or ask on public chatbots)
        if request.method not in permissions.SAFE_METHODS:
            if getattr(view, 'action', None) == 'ask' and obj.is_public:
                return True
            return (
                obj.creador == request.user
                or request.user.is_admin
            )

        # Safe methods (read)
        # Owner always
        if obj.creador == request.user:
            return True

        # Shared users can read (private)
        if request.user in obj.shared_with.all():
            return True

        # Admin
        if request.user.is_admin:
            return True

        # Public: any authenticated user can read
        if obj.is_public:
            return True

        return False
