"""Extraer texto de archivos subidos para RAG."""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

# Extensions supported for text extraction
TEXT_EXTENSIONS = {'.txt', '.json', '.rtf', '.csv', '.md', '.log'}
# .doc (legacy binary Word) is NOT supported — users must convert to .docx


def extract_text(file_path: str) -> str:
    """Extract text content from a file for RAG indexing."""
    ext = Path(file_path).suffix.lower()

    # Plain text files
    if ext in TEXT_EXTENSIONS:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Failed to read text file {file_path}: {e}")
            return ''

    # PDF files
    if ext == '.pdf':
        if PdfReader is None:
            logger.warning("PyPDF2 not installed — cannot extract PDF text")
            return ''
        try:
            reader = PdfReader(file_path)
            parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
            return '\n'.join(parts)
        except Exception as e:
            logger.warning(f"Failed to extract PDF text from {file_path}: {e}")
            return ''

    # DOCX files (modern Word format)
    if ext == '.docx':
        if docx is None:
            logger.warning("python-docx not installed — cannot extract DOCX text")
            return ''
        try:
            d = docx.Document(file_path)
            return '\n'.join(p.text for p in d.paragraphs)
        except Exception as e:
            logger.warning(f"Failed to extract DOCX text from {file_path}: {e}")
            return ''

    # Legacy .doc format — not supported
    if ext == '.doc':
        logger.info(f".doc format not supported for {file_path}. Please convert to .docx.")
        return ''

    # Fallback: try reading as text
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # If content looks like binary, return empty
            if '\x00' in content:
                return ''
            return content
    except Exception:
        return ''
