"""Centralized SSL context for OpenRouter / InsForge HTTPS calls.
Avoids CERTIFICATE_VERIFY_FAILED on Windows and ensures certifi is used.
"""
import ssl
import os
import sys
import logging

logger = logging.getLogger(__name__)


def get_ssl_context() -> ssl.SSLContext:
    """Build an SSL context that loads correct CA certs (certifi → Windows fallback)."""
    # Avoid ssl.create_default_context() which can hang in some container/envs
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    # Strategy 1: certifi (standard on Linux/mac; good practice everywhere)
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
        logger.debug("SSL: loaded certifi CA bundle")
    except Exception as e:
        logger.debug("SSL: certifi unavailable (%s)", e)

    # Strategy 2: Windows common paths (when certifi not installed or incomplete)
    for cert_path in [
        os.path.join(sys.prefix, 'Lib', 'site-packages', 'certifi', 'cacert.pem'),
        os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages', 'certifi', 'cacert.pem'),
    ]:
        if os.path.exists(cert_path):
            try:
                ctx.load_verify_locations(cert_path)
                logger.debug("SSL: loaded Windows CA bundle from %s", cert_path)
                break
            except Exception:
                pass
    return ctx


# Module-level singleton — call once, reuse everywhere
# Note: creation is deferred to first call to avoid import-time hangs in some envs.
_ssl_context = None

def _get_ssl_context():
    global _ssl_context
    if _ssl_context is None:
        _ssl_context = get_ssl_context()
    return _ssl_context
