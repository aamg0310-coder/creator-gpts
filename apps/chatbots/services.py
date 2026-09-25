"""
RAG Service for chatbot responses.
Retrieval Augmented Generation pipeline using pgvector and OpenRouter.
Includes conversation history and automatic context compaction.
"""
import os
import json
import logging
import ssl
from typing import List, Dict
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
from .insforge_client import InsForgeClient

from apps.core.utils.ssl import _get_ssl_context as get_ssl_ctx

# Ensure .env.local is loaded (Django may not load it for all paths)
_base_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_base_dir / '.env.local')
load_dotenv(_base_dir / '.env')

# Model context window sizes (tokens)
MODEL_CONTEXT_LIMITS = {
    'meta-llama/llama-3.1-8b-instruct': 8192,
    'meta-llama/llama-3.2-3b-instruct': 8192,
    'google/gemma-2-9b-it': 8192,
    'google/gemma-2-2b-it': 8192,
    'mistralai/mistral-7b-instruct': 8192,
    'qwen/qwen-2-7b-instruct': 8192,
    'deepseek/deepseek-chat': 16384,
    'openai/gpt-4o-mini': 128000,
    'openai/gpt-4o': 128000,
    'anthropic/claude-3-5-sonnet': 200000,
    'anthropic/claude-3-haiku': 200000,
    'google/gemini-2.0-flash-001': 1000000,
    'google/gemini-pro': 32000,
    'meta-llama/llama-3.1-70b-instruct': 8192,
    'mistralai/mixtral-8x7b-instruct': 32768,
    'qwen/qwen-2-72b-instruct': 32768,
    'cohere/command-r-plus': 128000,
}
DEFAULT_CONTEXT_LIMIT = 8192
# Use 75% of context limit to leave room for response
CONTEXT_USAGE_THRESHOLD = 0.75


def estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token for Spanish/English."""
    if not text:
        return 0
    return len(text) // 4


def simple_web_search(query: str) -> str:
    """Internet access disabled — only user-uploaded documents allowed."""
    return ""
    try:
        import urllib.parse
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10, context=get_ssl_ctx()) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        snippets = []
        for line in html.split('\n'):
            if 'class="result__snippet"' in line:
                text = line.replace('<a', '').replace('</a>', '').replace('<b>', '').replace('</b>', '').strip()
                text = ''.join(text.split('>')[-1:])
                if text and len(text) > 10 and len(text) < 500:
                    snippets.append(text)
            if len(snippets) >= 3:
                break
        if snippets:
            return "\n".join(snippets[:3])
    except Exception as e:
        logger.info(f"Web search fallback error: {e}")
    return ""


class RagService:
    """
    RAG pipeline service with conversation history and context compaction.
    """

    @staticmethod
    def retrieve_documents(chatbot_id: int, question: str, top_k: int = 5) -> list:
        """
        Retrieve relevant documents from InsForge pgvector via Edge Function.
        """
        try:
            docs = InsForgeClient.retrieve_documents(chatbot_id, question, top_k)
            if docs:
                logger.info(f"InsForge RAG: retrieved {len(docs)} docs for chatbot {chatbot_id}")
            else:
                logger.info("InsForge RAG: no docs retrieved (empty or error)")
            return docs
        except Exception as e:
            logger.error(f"Error retrieving documents from InsForge: {e}")
            return []

    @classmethod
    def load_conversation_history(cls, session) -> List[Dict[str, str]]:
        """
        Load conversation history from a ChatSession.
        Returns list of messages in OpenRouter format: [{"role": "user/assistant", "content": "..."}]
        """
        from .models import ChatMessage
        messages = ChatMessage.objects.filter(
            session=session
        ).order_by('timestamp')

        history = []
        for msg in messages:
            role = "user" if msg.is_user else "assistant"
            history.append({"role": role, "content": msg.contenido})

        logger.info(f"Loaded {len(history)} messages from session {session.id}")
        return history

    @classmethod
    def compact_history(cls, history: List[Dict], system_prompt: str,
                        documents_context: str, model: str) -> List[Dict]:
        """
        Compact conversation history when it exceeds context limits.
        Strategy: Keep the last N messages and summarize older ones.
        """
        context_limit = MODEL_CONTEXT_LIMITS.get(model, DEFAULT_CONTEXT_LIMIT)
        max_tokens = int(context_limit * CONTEXT_USAGE_THRESHOLD)

        # Estimate current usage
        system_tokens = estimate_tokens(system_prompt + documents_context)
        history_tokens = sum(estimate_tokens(m['content']) for m in history)

        total_tokens = system_tokens + history_tokens
        logger.info(f"Context check: {total_tokens}/{max_tokens} tokens "
                    f"(system={system_tokens}, history={history_tokens})")

        if total_tokens <= max_tokens:
            return history  # No compaction needed

        # Need compaction — keep last 4 messages, summarize the rest
        logger.info(f"Context overflow ({total_tokens}>{max_tokens}), compacting history...")

        if len(history) <= 4:
            # Too few messages to compact, just truncate the oldest
            return history[-4:]

        # Split: messages to summarize (all but last 4) and recent (last 4)
        to_summarize = history[:-4]
        recent = history[-4:]

        # Build a summary of old messages
        summary_parts = []
        for msg in to_summarize:
            role = "Usuario" if msg['role'] == 'user' else "Asistente"
            # Truncate each message to save tokens
            content = msg['content'][:200]
            summary_parts.append(f"{role}: {content}")

        summary_text = (
            "[Resumen de conversación anterior]\n" +
            "\n".join(summary_parts) +
            "\n[Fin del resumen]"
        )

        # Rebuild history: summary + recent messages
        compacted = [{"role": "assistant", "content": summary_text}] + recent

        compacted_tokens = system_tokens + sum(estimate_tokens(m['content']) for m in compacted)
        logger.info(f"After compaction: {compacted_tokens} tokens "
                    f"(saved {total_tokens - compacted_tokens} tokens)")

        return compacted

    @classmethod
    def generate_response_stream(cls, question: str, documents: list,
                                 history: List[Dict[str, str]] = None,
                                 soul: str = '', instructions: str = '',
                                 model: str = 'meta-llama/llama-3.1-8b-instruct',
                                 bot_memory: str = ''):
        """
        Streaming generator for OpenRouter responses.
        Yields text tokens as they arrive.
        bot_memory: The bot's instructions/soul from vector DB (AGENTS.md equivalent).
        """
        api_key = os.getenv('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')
        if not api_key:
            yield "Lo siento, el servicio de IA no está configurado."
            return

        # Build same context as generate_response
        documents_context = ""
        if documents:
            documents_context = "\n\nDocumentos relevantes:\n"
            for i, doc in enumerate(documents, 1):
                documents_context += f"{i}. {doc.get('content', '')}\n"

        # Bot memory (AGENTS.md / Instrucciones del Chatbot) — CONTEXTO PRINCIPAL
        # Siempre debe ser leído y seguido. Se inyecta primero.
        memory_text = bot_memory or ""
        if memory_text:
            system_prompt = f"[INSTRUCCIONES DEL CHATBOT — Lee y sigue estas instrucciones siempre]\n\n{memory_text}\n\n"
        else:
            system_prompt = "[INSTRUCCIONES DEL CHATBOT — Lee y sigue estas instrucciones siempre]\n\nNo hay memoria del bot cargada. Usa solo los documentos y tu conocimiento base.\n\n"
        if instructions:
            system_prompt += f"Instrucciones adicionales:\n{instructions}\n\n"
        if soul:
            system_prompt += f"Alma / personalidad:\n{soul}\n\n"
        if documents_context:
            system_prompt += f"\n\nUsa la siguiente información (documentos subidos por el usuario) para responder:\n{documents_context}"
        # STRICT: NO internet — only user-uploaded docs + bot memory + base knowledge
        system_prompt += "\n\n[REGLA ESTRICTA] NO tienes acceso a búsqueda en internet. SOLO puedes usar la información de los documentos listados arriba, tu memoria del chatbot (instrucciones + alma) y tu conocimiento base. Si la información no está en ninguna fuente, di claramente que no tienes esa información. NUNCA inventes datos ni busques en internet."

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            compacted_history = cls.compact_history(
                history, system_prompt, documents_context, model
            )
            messages.extend(compacted_history)
        messages.append({"role": "user", "content": question})

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://chatbot-creator.local",
            "X-Title": "Chatbot Creator"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 2048,
            "stream": True,
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=120, context=get_ssl_ctx()) as response:
                for line in response:
                    line = line.decode('utf-8', errors='ignore').strip()
                    if line.startswith('data: '):
                        chunk_str = line[6:]
                        if chunk_str == '[DONE]':
                            break
                        try:
                            chunk = json.loads(chunk_str)
                            delta = chunk.get('choices', [{}])[0].get('delta', {})
                            if 'content' in delta and delta['content']:
                                yield delta['content']
                        except Exception:
                            continue
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='ignore')[:200]
            logger.error(f"OpenRouter stream error: {e.code} {e.reason} — {error_body}")
            yield f"Error del servicio de IA (código {e.code})."
        except Exception as e:
            logger.error(f"OpenRouter stream exception: {type(e).__name__}: {e}")
            yield "Lo siento, hubo un error al procesar tu pregunta."

    @classmethod
    def generate_response(
        cls,
        question: str,
        documents: list,
        history: List[Dict[str, str]] = None,
        soul: str = '',
        instructions: str = '',
        funciones: str = '',
        model: str = 'meta-llama/llama-3.1-8b-instruct',
        bot_memory: str = ''
    ) -> str:
        """
        Generate response using OpenRouter LLM with conversation history.
        Automatically compacts history when context exceeds model limits.
        bot_memory: The bot's instructions/soul from vector DB (AGENTS.md equivalent).
        """
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            return "Lo siento, el servicio de IA no está configurado. Por favor, contacta al administrador."

        # Build context from documents
        documents_context = ""
        if documents:
            documents_context = "\n\nDocumentos relevantes:\n"
            for i, doc in enumerate(documents, 1):
                documents_context += f"{i}. {doc.get('content', '')}\n"

        # Bot memory (AGENTS.md / Instrucciones del Chatbot) — CONTEXTO PRINCIPAL
        # Siempre debe ser leído y seguido. Se inyecta primero.
        memory_text = bot_memory or ""
        if memory_text:
            system_prompt = f"[INSTRUCCIONES DEL CHATBOT — Lee y sigue estas instrucciones siempre]\n\n{memory_text}\n\n"
        else:
            system_prompt = "[INSTRUCCIONES DEL CHATBOT — Lee y sigue estas instrucciones siempre]\n\nNo hay memoria del bot cargada. Usa solo los documentos y tu conocimiento base.\n\n"
        if instructions:
            system_prompt += f"Instrucciones adicionales:\n{instructions}\n\n"
        if soul:
            system_prompt += f"Alma / personalidad:\n{soul}\n\n"

        if documents_context:
            system_prompt += f"\n\nUsa la siguiente información (documentos subidos por el usuario) para responder:\n{documents_context}"

        # STRICT: NO internet — only user-uploaded docs + bot memory + base knowledge
        system_prompt += "\n\n[REGLA ESTRICTA] NO tienes acceso a búsqueda en internet. SOLO puedes usar la información de los documentos listados arriba, tu memoria del chatbot (instrucciones + alma) y tu conocimiento base. Si la información no está en ninguna fuente, di claramente que no tienes esa información. NUNCA inventes datos ni busques en internet."

        # Build messages with history
        messages = [{"role": "system", "content": system_prompt}]

        if history:
            # Compact history if it exceeds context limits
            compacted_history = cls.compact_history(
                history, system_prompt, documents_context, model
            )
            messages.extend(compacted_history)

        # Add current question
        messages.append({"role": "user", "content": question})

        logger.info(f"OpenRouter request: model={model}, messages={len(messages)}, "
                    f"total_est_tokens={estimate_tokens(system_prompt) + sum(estimate_tokens(m['content']) for m in messages)}")

        # Call OpenRouter API
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://chatbot-creator.local",
                "X-Title": "Chatbot Creator"
            }
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 2048,
            }

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')

            with urllib.request.urlopen(req, timeout=60, context=get_ssl_ctx()) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result['choices'][0]['message']['content']
                return content or "Lo siento, no pude generar una respuesta."

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='ignore')[:1000]
            logger.error(f"OpenRouter API error: {e.code} {e.reason} — body: {error_body}")
            if e.code == 404:
                return f"Error: El modelo '{model}' no está disponible en OpenRouter."
            elif e.code == 401:
                return "Error: La API key de OpenRouter no es válida."
            elif e.code == 402:
                return "Error: No tienes créditos suficientes en OpenRouter."
            else:
                return f"Error del servicio de IA (código {e.code}). Por favor, intenta de nuevo."
        except Exception as e:
            logger.error(f"Error generating response: {type(e).__name__}: {e}")
            return "Lo siento, hubo un error al procesar tu pregunta. Por favor, intenta de nuevo."

    @classmethod
    def answer(cls, chatbot, question: str, session=None) -> str:
        """
        Main RAG pipeline using InsForge Edge Function's `ask` action.
        
        This delegates the RAG pipeline (memory retrieval + semantic search + 
        strict prompt building) to the Edge Function, which enforces:
        - Temperature: 0 (via strict prompt instructions)
        - Anti-hallucination rules: "SOLO usa contexto, NUNCA inventes"
        - Internet blocking: NO web search unless explicitly permitted
        - AGENTS.md memory injection: Always retrieved from vector DB
        """
        logger.info(f"RAG answer() called: chatbot={chatbot.nombre} (id={chatbot.id})")

        # 1. Load conversation history from session (for context)
        history = []
        if session:
            history = cls.load_conversation_history(session)

        # 2. Call InsForge Edge Function `ask` action
        # This handles: memory retrieval + semantic search + strict prompt building
        user_id = str(session.user.id) if session and session.user else None
        ask_result = InsForgeClient.ask(
            chatbot_id=chatbot.id,
            question=question,
            top_k=5,
            user_id=user_id
        )

        if "error" in ask_result:
            logger.error(f"InsForge ask error: {ask_result['error']}")
            return "Lo siento, hubo un error al procesar tu pregunta. Por favor, intenta de nuevo."

        # 3. Get the strict prompt from Edge Function (includes memory + context + rules)
        strict_prompt = ask_result.get("answer", "")
        context_chunks = ask_result.get("context_chunks", [])
        system_prompt = ask_result.get("system_prompt", "")

        if not strict_prompt:
            logger.warning("Empty prompt from InsForge ask")
            return "Lo siento, no pude generar una respuesta."

        # 4. Log context info
        logger.info(f"InsForge context chunks: {len(context_chunks)}")
        logger.info(f"System prompt length: {len(system_prompt)}")
        if context_chunks:
            logger.info(f"Relevant docs: {[c.get('filename') for c in context_chunks]}")

        # 5. Send the strict prompt to LLM with temperature: 0
        # The prompt already includes ALL anti-hallucination rules
        model = getattr(chatbot, 'modelo', '') or os.getenv('LLM_MODEL', 'openai/gpt-4o-mini')
        
        response = cls.generate_response_from_prompt(
            prompt=strict_prompt,
            model=model,
            history=history,
        )

        return response

    @classmethod
    def generate_response_from_prompt(cls, prompt: str, model: str, history: list = None) -> str:
        """
        Send a pre-built strict prompt to OpenRouter with temperature: 0.
        The prompt already contains all anti-hallucination rules.
        """
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            return "Lo siento, el servicio de IA no está configurado. Por favor, contacta al administrador."

        # Build messages - the prompt IS the system prompt + user question
        messages = [
            {"role": "system", "content": prompt}
        ]

        # Add history if available (compact if needed)
        if history:
            # For simplicity, add recent history
            for msg in history[-4:]:  # Last 4 messages for context
                messages.append(msg)

        logger.info(f"OpenRouter request: model={model}, messages={len(messages)}")

        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://chatbot-creator.local",
                "X-Title": "Chatbot Creator"
            }
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0,  # CRÍTICO: Previene alucinaciones
                "max_tokens": 2048,
            }

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')

            with urllib.request.urlopen(req, timeout=60, context=get_ssl_ctx()) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result['choices'][0]['message']['content']
                return content or "Lo siento, no pude generar una respuesta."

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='ignore')[:1000]
            logger.error(f"OpenRouter API error: {e.code} {e.reason} — body: {error_body}")
            if e.code == 404:
                return f"Error: El modelo '{model}' no está disponible en OpenRouter."
            elif e.code == 401:
                return "Error: La API key de OpenRouter no es válida."
            elif e.code == 402:
                return "Error: No tienes créditos suficientes en OpenRouter."
            else:
                return f"Error del servicio de IA (código {e.code}). Por favor, intenta de nuevo."
        except Exception as e:
            logger.error(f"Error generating response: {type(e).__name__}: {e}")
            return "Lo siento, hubo un error al procesar tu pregunta. Por favor, intenta de nuevo."
