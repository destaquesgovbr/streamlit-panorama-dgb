"""E2E smoke tests for all Panorama Gov.BR pages.

Navigates each page on the deployed app and checks for errors.
Run: pytest tests/test_pages_e2e.py -v
Requires: pip install pytest playwright && playwright install chromium
"""

import os
import re
import pytest
from playwright.sync_api import sync_playwright, Page, expect

BASE_URL = os.environ.get(
    "PANORAMA_URL",
    "https://streamlit-panorama-dgb-klvx64dufq-rj.a.run.app",
)

# Streamlit page routes (sidebar links)
PAGES = [
    {"name": "Visão Geral", "path": "/", "source": "bigquery"},
    {"name": "Agências", "path": "/Agencias", "source": "bigquery"},
    {"name": "Temas", "path": "/Temas", "source": "bigquery"},
    {"name": "Qualidade", "path": "/Qualidade", "source": "bigquery"},
    {"name": "Entidades", "path": "/Entidades", "source": "postgres"},
    {"name": "Engajamento", "path": "/Engajamento", "source": "umami"},
    {"name": "Mapa_Semantico", "path": "/Mapa_Semantico", "source": "postgres"},
]

# Error patterns that indicate a broken page
ERROR_PATTERNS = [
    r"(?i)traceback",
    r"(?i)error.*:",
    r"(?i)exception",
    r"(?i)não configurado",
    r"(?i)undefined\s*table",
    r"(?i)relation.*does not exist",
    r"(?i)connection\s*refused",
    r"(?i)operational\s*error",
    r"(?i)programming\s*error",
]

# Warning patterns (non-fatal but worth flagging)
WARNING_PATTERNS = [
    r"(?i)sem (dados|embeddings|registros) disponíveis",
    r"(?i)verifique se",
    r"(?i)defina as variáveis",
]


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    yield page
    context.close()


def wait_for_streamlit(page: Page, timeout: int = 60000):
    """Wait for Streamlit app to finish loading."""
    # Wait for the main app container
    page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=timeout)
    # Wait for any running status to finish
    try:
        page.wait_for_selector(
            '[data-testid="stStatusWidget"]',
            state="detached",
            timeout=30000,
        )
    except Exception:
        pass  # Widget might not appear if page loads fast
    # Extra wait for async rendering
    page.wait_for_timeout(3000)


def get_page_errors(page: Page) -> tuple[list[str], list[str]]:
    """Extract error and warning messages from page content."""
    content = page.content()
    text = page.inner_text("body")

    errors = []
    warnings = []

    for pattern in ERROR_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            # Get context around the match
            for match in matches[:3]:  # Limit to 3 matches per pattern
                idx = text.lower().find(match.lower())
                start = max(0, idx - 50)
                end = min(len(text), idx + len(match) + 100)
                context = text[start:end].strip()
                errors.append(context)

    for pattern in WARNING_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            for match in matches[:2]:
                idx = text.lower().find(match.lower())
                start = max(0, idx - 30)
                end = min(len(text), idx + len(match) + 80)
                context = text[start:end].strip()
                warnings.append(context)

    return errors, warnings


class TestPanoramaPages:
    """Smoke tests for each page of the Panorama dashboard."""

    @pytest.mark.parametrize(
        "page_info",
        PAGES,
        ids=[p["name"] for p in PAGES],
    )
    def test_page_loads_without_errors(self, page, page_info):
        """Each page should load without Python tracebacks or connection errors."""
        url = f"{BASE_URL}{page_info['path']}"
        console_errors = []

        # Capture console errors
        page.on("console", lambda msg: (
            console_errors.append(msg.text)
            if msg.type == "error" else None
        ))

        # Navigate
        response = page.goto(url, wait_until="networkidle", timeout=90000)
        assert response is not None, f"No response from {url}"
        assert response.status == 200, f"HTTP {response.status} for {url}"

        # Wait for Streamlit to finish rendering
        wait_for_streamlit(page)

        # Check for errors in page content
        errors, warnings = get_page_errors(page)

        # Print warnings (non-fatal)
        if warnings:
            print(f"\n  WARNINGS on {page_info['name']}:")
            for w in warnings:
                print(f"    - {w[:120]}")

        # Assert no errors
        assert not errors, (
            f"Errors found on page '{page_info['name']}' ({url}):\n"
            + "\n".join(f"  - {e[:200]}" for e in errors)
        )

    def test_home_has_kpis(self, page):
        """Home page should display KPI metrics."""
        page.goto(BASE_URL, wait_until="networkidle", timeout=90000)
        wait_for_streamlit(page)

        # Streamlit metrics use data-testid="stMetricValue"
        metrics = page.query_selector_all('[data-testid="stMetricValue"]')
        assert len(metrics) >= 2, (
            f"Expected at least 2 KPI metrics on home page, found {len(metrics)}"
        )

    def test_sidebar_navigation(self, page):
        """Sidebar should contain links to all pages."""
        page.goto(BASE_URL, wait_until="networkidle", timeout=90000)
        wait_for_streamlit(page)

        sidebar = page.query_selector('[data-testid="stSidebar"]')
        if sidebar is None:
            # Try expanding collapsed sidebar
            expand = page.query_selector('[data-testid="stSidebarCollapsedControl"]')
            if expand:
                expand.click()
                page.wait_for_timeout(1000)
                sidebar = page.query_selector('[data-testid="stSidebar"]')

        assert sidebar is not None, "Sidebar not found"
        sidebar_text = sidebar.inner_text()

        for p in PAGES:
            if p["path"] == "/":
                continue
            # Page name without emoji prefix
            clean_name = p["name"]
            assert clean_name.lower() in sidebar_text.lower() or p["path"].strip("/").lower() in sidebar_text.lower(), (
                f"Page '{clean_name}' not found in sidebar"
            )
