"""Views for users app."""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer


# ─── API ViewSets ────────────────────────────────────────────────────────────

class UserViewSet(viewsets.ModelViewSet):
    """API endpoint for users. Only admins can list/retrieve all users."""
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'destroy']:
            # Only admins can list or delete users
            permission_classes = [IsAuthenticated]
        elif self.action == 'update' or self.action == 'partial_update':
            # Users can only update themselves
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.is_admin:
            return User.objects.all()
        # Non-admins can only see their own profile
        return User.objects.filter(id=user.id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


# ─── Template Views ──────────────────────────────────────────────────────────

def register_view(request):
    """Register new user."""
    if request.method == 'POST':
        serializer = RegisterSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user)
            messages.success(request, '¡Cuenta creada exitosamente!')
            return redirect('home')
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    return render(request, 'pages/register.html')


def login_view(request):
    """Login user."""
    if request.method == 'POST':
        serializer = LoginSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            messages.success(request, '¡Bienvenido!')
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Credenciales inválidas.')
    return render(request, 'pages/login.html')


@login_required
def logout_view(request):
    """Logout user."""
    logout(request)
    messages.info(request, 'Has cerrado sesión.')
    return redirect('home')
