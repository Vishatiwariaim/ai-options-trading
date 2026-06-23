"""Networking helpers.

Corporate machines often sit behind an SSL-inspection proxy whose root CA is
trusted by the OS but unknown to Python's bundled `certifi`. That makes every
HTTPS call (yfinance, NSE) fail with CERTIFICATE_VERIFY_FAILED. `truststore`
lets Python verify against the OS trust store instead, which fixes it.

Call `enable_os_trust_store()` once, early, before any HTTPS request.
"""
from __future__ import annotations

_injected = False


def enable_os_trust_store() -> bool:
    """Make Python use the operating-system trust store for TLS. Best-effort."""
    global _injected
    if _injected:
        return True
    try:
        import truststore

        truststore.inject_into_ssl()
        _injected = True
    except Exception:
        # truststore missing or injection failed — keep going with certifi.
        pass
    return _injected
