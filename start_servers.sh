#!/bin/bash
# ============================================================
# Script para ejecutar servidores del proyecto Chatbot
# Solo backend — front no modificado
# ============================================================

# --- Configuración ---
DJANGO_PORT=8000
MEDIA_PORT=9000
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Servidor 1: Django (backend, API, chatbots, memoria InsForge) ---
echo "🚀 Iniciando Django backend (port $DJANGO_PORT)..."
echo "   URL: http://localhost:$DJANGO_PORT"
echo "   Admin: http://localhost:$DJANGO_PORT/admin"
echo ""

# Ejecutar Django en background
python3 manage.py runserver 0.0.0.0:$DJANGO_PORT > /tmp/django_server.log 2>&1 &
DJANGO_PID=$!
echo "   PID Django: $DJANGO_PID"
sleep 2

# Verificar que Django levantó
if kill -0 $DJANGO_PID 2>/dev/null; then
    echo "   ✅ Django corriendo (PID $DJANGO_PID)"
else
    echo "   ❌ Django falló al iniciar. Ver /tmp/django_server.log"
fi

# --- Servidor 2: Python HTTP para media / archivos subidos ---
echo ""
echo "📁 Iniciando servidor de archivos (media/chat_icons, chat_docs) en port $MEDIA_PORT..."
echo "   URL: http://localhost:$MEDIA_PORT"
echo ""

# Usar el directorio media del proyecto como raíz de archivos
python3 -m http.server $MEDIA_PORT --directory "$PROJECT_DIR/media" > /tmp/media_server.log 2>&1 &
MEDIA_PID=$!
echo "   PID Media: $MEDIA_PID"
sleep 1

if kill -0 $MEDIA_PID 2>/dev/null; then
    echo "   ✅ Servidor de archivos corriendo (PID $MEDIA_PID)"
else
    echo "   ❌ Media server falló"
fi

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  SERVIDORES ACTIVOS"
echo "══════════════════════════════════════════════════════════════"
echo "  1. Django (API + chatbots + memoria InsForge) :: localhost:$DJANGO_PORT"
echo "  2. Archivos (media / docs / icons)              :: localhost:$MEDIA_PORT"
echo ""
echo "  Test rápido de memoria vectorial (requiere clave InsForge real):"
echo "    python3 -c \"from apps.chatbots.memory_service import ChatbotMemoryService; print('Servicio OK')\""
echo ""
echo "  Para detener:"
echo "    kill $DJANGO_PID $MEDIA_PID"
echo "    o: bash $0 stop"
echo "══════════════════════════════════════════════════════════════"

# --- Comando stop opcional ---
if [[ "$1" == "stop" ]]; then
    echo "Deteniendo servidores..."
    kill $DJANGO_PID $MEDIA_PID 2>/dev/null || true
    echo "Detenido."
fi

# --- Mantener script vivo para que los bg processes no se cierren ---
# El usuario puede presionar Ctrl+C o llamar con 'stop'
if [[ "$1" != "stop" ]]; then
    echo "Presiona Ctrl+C para detener (o ejecute: bash $0 stop)"
    wait $DJANGO_PID 2>/dev/null || true
fi
