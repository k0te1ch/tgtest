"""Open a game or Mini App URL in a headless browser (optional `browser` extra).

Playwright is imported inside the function, so tgtest works without it.
Install with `pip install "tgtest[browser]"` and `playwright install chromium`.
"""

from __future__ import annotations

_MISSING = (
    "assert_page_loads needs the optional browser extra: "
    'pip install "tgtest[browser]" && playwright install chromium'
)


async def assert_page_loads(url: str, timeout: float = 30.0) -> None:
    """Fail unless `url` reaches `load` within `timeout` seconds without errors.

    Uncaught JavaScript errors and HTTP error statuses fail the check.
    """
    try:
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise ImportError(_MISSING) from exc

    errors: list[str] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page()
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            try:
                response = await page.goto(
                    url, wait_until="load", timeout=timeout * 1000
                )
            except PlaywrightError as exc:
                raise AssertionError(
                    f"page did not load within {timeout}s: {url}\n  {exc}"
                ) from exc
        finally:
            await browser.close()
    if response is not None and not response.ok:
        raise AssertionError(f"page answered HTTP {response.status}: {url}")
    if errors:
        raise AssertionError(
            f"page raised {len(errors)} error(s): {url}\n  " + "\n  ".join(errors)
        )
