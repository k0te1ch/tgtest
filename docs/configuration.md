# Configuration

All configuration is provided through environment variables (optionally via a
`.env` file) and loaded into a `Settings` object built on
[`pydantic-settings`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).
Every variable uses the **`TG_` prefix**.

Source: [`tgtest/config.py`](../tgtest/config.py).

## Variables

| Env var | Field | Type | Default | Required | Meaning |
|---------|-------|------|---------|----------|---------|
| `TG_API_ID` | `api_id` | int | — | **yes** | User-client API id from my.telegram.org. |
| `TG_API_HASH` | `api_hash` | str | — | **yes** | User-client API hash. |
| `TG_SESSION` | `session` | str | `tgtest.session` | no | Telethon session file path. |
| `TG_PHONE` | `phone` | str | `None` | for login only | Test account phone, used by `login.py`. |
| `TG_DEFAULT_BOT` | `default_bot` | str | `None` | no | Bot used when a test/scenario names none. |
| `TG_PROXY` | `proxy` | str | `None` | no | Proxy URL for the user client (see [Proxy](#proxy)). |
| `TG_TIMEOUT` | `timeout` | float | `15.0` | no | Default per-step reply timeout (seconds). |
| `TG_APP_NAME` | `app_name` | str | `tgtest` | no | Logger name. |
| `TG_LOG_LEVEL` | `log_level` | str | `INFO` | no | Logging level. |

`api_id` and `api_hash` are mandatory; if either is missing, loading raises a
`RuntimeError` with guidance (see [Troubleshooting](troubleshooting.md)).

## Loading settings in code

```python
from tgtest import Settings

settings = Settings.load()                 # reads env + ./.env
settings = Settings.load(env_file=".env.ci")  # explicit env file
```

`Settings.load()` wraps construction and turns a missing-credentials
`ValidationError` into a friendly `RuntimeError`. Direct construction also
works: `Settings()` (reads `.env`) or `Settings(_env_file=None)` (ignore any
`.env`, useful in unit tests).

## `.env` resolution

- The CLI loads `./.env` by default; override with `tgtest run --env path`.
- The pytest fixtures call `Settings.load()`, which reads `./.env`.
- pydantic-settings precedence: explicit kwargs > real environment variables >
  values in the `.env` file.

## Proxy

Set `TG_PROXY` to route the **user client** (and `login.py`) through a proxy.
It is a single URL; the scheme selects the type. Parsing lives in
[`tgtest/proxy.py`](../tgtest/proxy.py) and is applied by `build_client`.

| Scheme | Type | Notes |
|--------|------|-------|
| `socks5://` | SOCKS5 | DNS resolved locally. |
| `socks5h://` | SOCKS5 | DNS resolved **via the proxy** (avoids leaks). |
| `socks4://` / `socks4a://` | SOCKS4 / 4a | `4a` resolves DNS remotely. |
| `http://` / `https://` | HTTP CONNECT | DNS resolved by the proxy. |
| `mtproxy://` / `mtproto://` | Telegram MTProxy | Uses a dedicated MTProto connection. |

```
# no auth
TG_PROXY=socks5://127.0.0.1:9050
# with auth (percent-encode special characters, e.g. @ -> %40)
TG_PROXY=socks5://user:p%40ss@host:1080
# HTTP proxy
TG_PROXY=http://proxy.local:3128
# Telegram MTProxy — secret in userinfo or as ?secret=
TG_PROXY=mtproxy://0123456789abcdef@host:443
TG_PROXY=mtproxy://host:443?secret=0123456789abcdef
```

SOCKS/HTTP proxies use [`python-socks`](https://github.com/romis2012/python-socks)
(a runtime dependency). MTProxy uses Telethon's
`ConnectionTcpMTProxyRandomizedIntermediate` automatically. A malformed
`TG_PROXY` raises `ValueError` at startup so problems surface immediately.

## Logging

`configure_logger(settings)` (in [`tgtest/logger.py`](../tgtest/logger.py))
sets up a rotating file handler writing to `logs/tgtest.log`
(5 MB × 3 backups). The CLI calls it automatically and logs each scenario's
`PASS` / `FAIL` / `ERROR`. Control verbosity with `TG_LOG_LEVEL`.
