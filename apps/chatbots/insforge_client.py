"""
InsForge client for RAG operations.
Calls InsForge Edge Functions via REST API using SDK patterns.
"""
import os
import json
import logging
import ssl
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Ensure .env.local is loaded
_base_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_base_dir / '.env.local')
load_dotenv(_base_dir / '.env')


from apps.core.utils.ssl import _get_ssl_context as get_ssl_ctx


def _get_insforge_config():
    """Read InsForge config from env at request time (not import time)."""
    project_id = os.getenv('INSFORGE_PROJECT_ID')
    base_url = os.getenv('INSFORGE_BASE_URL') or (
        f"https://{project_id}.insforge.dev" if project_id else None
    )
    anon_key = os.getenv('INSFORGE_ANON_KEY')
    return base_url, anon_key


class InsForgeClient:
    """Client for InsForge Edge Functions (RAG pipeline)."""

    @staticmethod
    def _make_request(endpoint: str, payload: dict) -> dict:
        base_url, anon_key = _get_insforge_config()
        if not base_url:
            logger.error("INSFORGE_BASE_URL not configured")
            return {"error": "INSFORGE_BASE_URL not configured"}
        if not anon_key:
            logger.error("INSFORGE_ANON_KEY not configured")
            return {"error": "INSFORGE_ANON_KEY not configured"}

        url = f"{base_url}/functions/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {anon_key}",
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')

        try:
            with urllib.request.urlopen(req, timeout=30, context=get_ssl_ctx()) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='ignore')[:500]
            logger.error(f"InsForge API error: {e.code} — {body}")
            return {"error": f"InsForge API error: {e.code} — {body}"}
        except Exception as e:
            logger.error(f"InsForge request error: {e}")
            return {"error": str(e)}

    @staticmethod
    def upload_documents(chatbot_id: int, filename: str, content: str, user_id: str = None) -> dict:
        return InsForgeClient._make_request("rag", {
            "action": "upload",
            "chatbot_id": chatbot_id,
            "filename": filename,
            "content": content,
            "user_id": user_id,
        })

    @staticmethod
    def retrieve_documents(chatbot_id: int, question: str, top_k: int = 5) -> list:
        result = InsForgeClient._make_request("rag", {
            "action": "retrieve",
            "chatbot_id": chatbot_id,
            "query": question,
            "top_k": top_k,
        })
        return result.get("documents", []) if "error" not in result else []

    @staticmethod
    def retrieve_bot_memory(chatbot_id: int) -> str:
        """
        Retrieve the bot's own memory (instructions, soul)
        from InsForge vector DB. This is the 'AGENTS.md' equivalent —
        always injected into context before answering.
        """
        result = InsForgeClient._make_request("rag", {
            "action": "retrieve_memory",
            "chatbot_id": chatbot_id,
        })
        if "error" in result:
            logger.warning(f"Failed to retrieve bot memory: {result['error']}")
            return ""
        docs = result.get("documents", [])
        if docs:
            # Concatenate all memory chunks, sorted by chunk_index
            docs_sorted = sorted(docs, key=lambda d: d.get("chunk_index", 0))
            return "\n".join(d.get("content", "") for d in docs_sorted)
        return ""

    @staticmethod
    def delete_documents(chatbot_id: int) -> bool:
        result = InsForgeClient._make_request("rag", {
            "action": "delete",
            "chatbot_id": chatbot_id,
        })
        return result.get("success", False)

    @staticmethod
    def ask(chatbot_id: int, question: str, top_k: int = 5, user_id: str = None) -> dict:
        """
        Full RAG pipeline: retrieves bot memory + relevant docs, builds prompt,
        returns the system prompt ready for LLM with temperature: 0.
        """
        result = InsForgeClient._make_request("rag", {
            "action": "ask",
            "chatbot_id": chatbot_id,
            "query": question,
            "top_k": top_k,
            "user_id": user_id,
        })
        if "error" in result:
            logger.warning(f"Ask failed for chatbot {chatbot_id}: {result['error']}")
            return {"error": result['error']}
        return result
