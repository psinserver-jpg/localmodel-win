"""HTTPS that works out of the box.

python.org's Python on macOS ships WITHOUT root certificates until the user runs "Install Certificates.command",
so every https:// request fails with CERTIFICATE_VERIFY_FAILED (login, web search, updates, skill installs).
We keep verification ON and just find a CA bundle: Python's own, else certifi, else the system's.
"""

from __future__ import annotations

import os
import ssl
import urllib.request
from typing import Optional

_BUNDLES = ("/etc/ssl/cert.pem", "/private/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt",
            "/etc/pki/tls/certs/ca-bundle.crt", "/usr/local/etc/openssl/cert.pem", "/opt/homebrew/etc/ca-certificates/cert.pem")
_ctx: Optional[ssl.SSLContext] = None


def _has_roots(ctx: ssl.SSLContext) -> bool:
    try:
        return ctx.cert_store_stats().get("x509_ca", 0) > 0
    except Exception:
        return True  # cannot tell: assume fine


def ssl_context() -> ssl.SSLContext:
    global _ctx
    if _ctx is not None:
        return _ctx
    ctx = ssl.create_default_context()
    if not _has_roots(ctx):
        candidates = []
        try:
            import certifi  # type: ignore
            candidates.append(certifi.where())
        except Exception:
            pass
        candidates += [os.environ.get("SSL_CERT_FILE", "")] + list(_BUNDLES)
        for path in candidates:
            if path and os.path.isfile(path):
                try:
                    ctx = ssl.create_default_context(cafile=path)
                    if _has_roots(ctx):
                        break
                except (ssl.SSLError, OSError):
                    continue
    _ctx = ctx
    return ctx


def urlopen(req, timeout: float = 30):
    """urllib.request.urlopen with a working certificate bundle (https only; http is unaffected)."""
    url = req if isinstance(req, str) else req.full_url
    if url.lower().startswith("https://"):
        return urllib.request.urlopen(req, timeout=timeout, context=ssl_context())
    return urllib.request.urlopen(req, timeout=timeout)
