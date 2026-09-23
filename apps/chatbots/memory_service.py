"""Servicio para sincronizar memoria/contexto del chatbot a InsForge vector DB.

This functions as the chatbot's AGENTS.md — a persistent set of instructions
that the LLM retrieves from the vector DB on every query, ensuring it always
knows its identity, capabilities, and behavioral rules.
"""
from .models import Chatbot
from .insforge_client import InsForgeClient
import os

class ChatbotMemoryService:
    """Sincroniza soul, instructions, funciones, suggestions y docs con InsForge RAG.

    The memory file acts as an AGENTS.md: it is stored in the vector DB and
    retrieved on every query to guide the LLM's behavior before conversation.
    """

    @staticmethod
    def build_memory_content(chatbot: Chatbot) -> str:
        """Build a structured AGENTS.md-like document for the chatbot.

        This document is uploaded to the vector DB and retrieved on every
        query. The LLM reads it FIRST, before processing any user question.
        """
        parts = []

        # Header — identifies this as the bot's core instructions
        parts.append(f"# AGENTS.MD — Instrucciones del Chatbot: {chatbot.nombre}")
        parts.append(f"slug: {chatbot.slug}")
        parts.append(f"modelo: {chatbot.get_modelo_display()}")
        parts.append(f"creador: {chatbot.creador.username}")
        parts.append("")

        # SOUL — personality and identity
        if chatbot.soul:
            parts.append("## Identidad y Personalidad (Soul)")
            parts.append(chatbot.soul)
            parts.append("")

        # INSTRUCTIONS — technical rules and constraints
        if chatbot.instructions:
            parts.append("## Instrucciones Técnicas")
            parts.append("Estas instrucciones son OBLIGATORIAS. Síguelas en cada respuesta:")
            parts.append(chatbot.instructions)
            parts.append("")

        # CAPABILITIES
        if chatbot.funciones:
            funcs = ', '.join(str(f) for f in chatbot.funciones) if isinstance(chatbot.funciones, list) else str(chatbot.funciones)
            parts.append("## Capacidades")
            parts.append(f"Capacidades habilitadas: {funcs}")
            parts.append("")

        # SUGGESTIONS
        if chatbot.suggestions:
            sugg = ', '.join(str(s) for s in chatbot.suggestions) if isinstance(chatbot.suggestions, list) else str(chatbot.suggestions)
            parts.append("## Sugerencias para Iniciar")
            parts.append(sugg)
            parts.append("")

        # DOCUMENTATION
        docs = chatbot.documents.all()
        if docs.exists():
            doc_list = '\n'.join(f"- {d.file.name} (subido {d.uploaded_at})" for d in docs)
            parts.append("## Documentación Disponible")
            parts.append(doc_list)
        else:
            parts.append("## Documentación Disponible")
            parts.append("Sin documentos adicionales.")
        parts.append("")

        # DESCRIPTION
        parts.append("## Descripción")
        parts.append(chatbot.descripcion or 'Sin descripción.')

        return "\n".join(parts)

    @staticmethod
    def sync_memory(chatbot: Chatbot, user_id: str = None) -> dict:
        """Sync chatbot memory to InsForge vector DB.

        This uploads the AGENTS.md-like document that the LLM will retrieve
        on every query to know its identity and instructions.
        """
        from .document_extract import extract_text
        # 1. Clear previous RAG docs for this chatbot
        ChatbotMemoryService.delete_memory(chatbot.id)

        # 2. Subir memoria del chatbot (metadatos + instrucciones)
        content = ChatbotMemoryService.build_memory_content(chatbot)
        filename = f"memory_{chatbot.slug}.txt"
        result = InsForgeClient.upload_documents(
            chatbot_id=chatbot.id,
            filename=filename,
            content=content,
            user_id=user_id or (str(chatbot.creador.id) if chatbot.creador else None)
        )

        # 3. Subir contenido real de cada archivo de documentación
        for doc in chatbot.documents.all():
            file_path = doc.file.path if doc.file else None
            if file_path and os.path.exists(file_path):
                text = extract_text(file_path)
                if text:
                    InsForgeClient.upload_documents(
                        chatbot_id=chatbot.id,
                        filename=os.path.basename(doc.file.name),
                        content=text,
                        user_id=user_id or (str(chatbot.creador.id) if chatbot.creador else None)
                    )
        return result

    @staticmethod
    def delete_memory(chatbot_id: int) -> bool:
        return InsForgeClient.delete_documents(chatbot_id)
