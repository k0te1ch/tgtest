"""Unit tests for proxy URL parsing (no network, safe for CI)."""
import pytest

from tgtest.proxy import parse_proxy


def test_empty_returns_none():
    assert parse_proxy(None) is None
    assert parse_proxy("") is None
    assert parse_proxy("   ") is None


def test_socks5_basic():
    cfg = parse_proxy("socks5://127.0.0.1:9050")
    assert (cfg.kind, cfg.host, cfg.port) == ("socks5", "127.0.0.1", 9050)
    assert cfg.username is None and cfg.password is None
    assert cfg.rdns is False  # plain socks5 = local DNS


def test_socks5h_uses_remote_dns():
    cfg = parse_proxy("socks5h://host:1080")
    assert cfg.kind == "socks5"
    assert cfg.rdns is True


def test_socks5_with_auth_and_encoding():
    cfg = parse_proxy("socks5://user:p%40ss@host:1080")
    assert cfg.username == "user"
    assert cfg.password == "p@ss"  # percent-decoded


def test_socks4():
    cfg = parse_proxy("socks4://host:1080")
    assert cfg.kind == "socks4"


def test_http_proxy_remote_dns():
    cfg = parse_proxy("http://proxy.local:3128")
    assert cfg.kind == "http"
    assert cfg.rdns is True


def test_mtproxy_secret_in_userinfo():
    cfg = parse_proxy("mtproxy://deadbeef@host:443")
    assert cfg.kind == "mtproxy"
    assert (cfg.host, cfg.port, cfg.secret) == ("host", 443, "deadbeef")


def test_mtproxy_secret_in_query():
    cfg = parse_proxy("mtproto://host:443?secret=cafe")
    assert cfg.kind == "mtproxy"
    assert cfg.secret == "cafe"


def test_mtproxy_requires_secret():
    with pytest.raises(ValueError):
        parse_proxy("mtproxy://host:443")


def test_missing_scheme_raises():
    with pytest.raises(ValueError):
        parse_proxy("127.0.0.1:9050")


def test_unsupported_scheme_raises():
    with pytest.raises(ValueError):
        parse_proxy("ftp://host:21")


def test_missing_port_raises():
    with pytest.raises(ValueError):
        parse_proxy("socks5://host")
