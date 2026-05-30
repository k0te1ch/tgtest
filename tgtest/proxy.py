"""Parse a proxy URL into a normalized, framework-agnostic config.

Keeping this pure (no Telethon import) makes it unit-testable. The translation
into Telethon client kwargs happens in ``client.py``.

Supported URL schemes:
  - ``socks5://``  / ``socks5h://``   (SOCKS5; ``h`` = resolve DNS via proxy)
  - ``socks4://``  / ``socks4a://``   (SOCKS4 / 4a)
  - ``http://``    / ``https://``     (HTTP CONNECT proxy)
  - ``mtproxy://`` / ``mtproto://``   (Telegram MTProxy)

Examples:
  socks5://127.0.0.1:9050
  socks5://user:pass@host:1080
  http://proxy.local:3128
  mtproxy://SECRET@host:443        (secret in the userinfo)
  mtproxy://host:443?secret=SECRET (secret in the query)
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

# URL scheme -> normalized SOCKS/HTTP kind understood by python-socks/Telethon.
_KIND_BY_SCHEME = {
    "socks5": "socks5",
    "socks5h": "socks5",
    "socks4": "socks4",
    "socks4a": "socks4",
    "http": "http",
    "https": "http",
}
# Schemes that resolve DNS remotely (through the proxy).
_REMOTE_DNS_SCHEMES = {"socks5h", "socks4a", "http", "https"}
_MTPROXY_SCHEMES = {"mtproxy", "mtproto", "mtp"}


@dataclass
class ProxyConfig:
    """Normalized proxy settings. ``kind`` is one of socks5/socks4/http/mtproxy."""

    kind: str
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    secret: str | None = None  # MTProxy only
    rdns: bool = True


def parse_proxy(url: str | None) -> ProxyConfig | None:
    """Parse a proxy URL. Returns None for empty input; raises ValueError on
    malformed input so misconfiguration fails fast and clearly."""
    if not url or not url.strip():
        return None

    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    if not scheme:
        raise ValueError(
            f"proxy URL must include a scheme, e.g. socks5://host:port (got {url!r})"
        )

    host = parsed.hostname
    port = parsed.port

    if scheme in _MTPROXY_SCHEMES:
        secret = parsed.username or parse_qs(parsed.query).get("secret", [None])[0]
        if not host or not port or not secret:
            raise ValueError(
                "mtproxy URL must be mtproxy://SECRET@host:port "
                "or mtproxy://host:port?secret=SECRET"
            )
        return ProxyConfig(kind="mtproxy", host=host, port=port, secret=unquote(secret))

    kind = _KIND_BY_SCHEME.get(scheme)
    if kind is None:
        raise ValueError(
            f"unsupported proxy scheme {scheme!r}; "
            "use socks5, socks5h, socks4, socks4a, http, https, or mtproxy"
        )
    if not host or not port:
        raise ValueError(f"proxy URL must include host and port (got {url!r})")

    return ProxyConfig(
        kind=kind,
        host=host,
        port=port,
        username=unquote(parsed.username) if parsed.username else None,
        password=unquote(parsed.password) if parsed.password else None,
        rdns=scheme in _REMOTE_DNS_SCHEMES,
    )
