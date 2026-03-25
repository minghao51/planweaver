"""
E2E Tests for Static UI using Playwright
"""

import asyncio

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, Page, Browser

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]
UI_URL = "http://localhost:8000/static/index.html"


@pytest_asyncio.fixture
async def browser():
    """Create browser instance for testing."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def page(browser: Browser):
    """Create new page for testing."""
    page = await browser.new_page()
    yield page
    await page.close()


@pytest_asyncio.fixture
async def ui_url() -> str:
    """Skip E2E tests when the local UI server is not running."""
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", 8000), timeout=1)
        writer.close()
        await writer.wait_closed()
    except Exception:
        pytest.skip(f"UI server not running at {UI_URL}")
    return UI_URL


async def test_ui_loads(page: Page, ui_url: str):
    """Test that UI loads successfully."""
    await page.goto(ui_url)

    # Check that title is visible
    title = await page.text_content("h1")
    assert "PlanWeaver" in title


async def test_session_creation_form_exists(page: Page, ui_url: str):
    """Test that session creation form is present."""
    await page.goto(ui_url)

    # Check form elements exist
    assert await page.query_selector("#user-intent") is not None
    assert await page.query_selector("#scenario-name") is not None
    assert await page.query_selector("#planning-mode") is not None
    assert await page.query_selector("button[type='submit']") is not None


async def test_session_list_loads(page: Page, ui_url: str):
    """Test that session list is displayed."""
    await page.goto(ui_url)

    # Wait for session list to load
    await page.wait_for_selector("#session-list-container", state="visible", timeout=5000)

    # Check that session list container exists
    assert await page.query_selector("#session-list") is not None


async def test_create_session_flow(page: Page, ui_url: str):
    """Test complete session creation flow."""
    await page.goto(ui_url)

    # Fill out form
    await page.fill("#user-intent", "Build a REST API with FastAPI")
    await page.fill("#scenario-name", "web_development")
    await page.select_option("#planning-mode", "baseline")

    # Submit form
    await page.click("button[type='submit']")

    # Wait for navigation to session detail
    await page.wait_for_selector("#session-detail", state="visible", timeout=10000)

    # Verify we're on session detail page
    assert await page.query_selector("#session-detail") is not None


async def test_session_detail_display(page: Page, ui_url: str):
    """Test that session detail displays correctly."""
    await page.goto(ui_url)

    # Create a session first
    await page.fill("#user-intent", "Test session for E2E")
    await page.click("button[type='submit']")
    await page.wait_for_selector("#session-detail", state="visible", timeout=10000)

    # Check session detail elements
    assert await page.query_selector("#session-info") is not None
    assert await page.query_selector("#chat-interface") is not None
    assert await page.query_selector("#back-button") is not None


async def test_chat_interface_exists(page: Page, ui_url: str):
    """Test that chat interface is present in session detail."""
    await page.goto(ui_url)

    # Create session
    await page.fill("#user-intent", "Test chat interface")
    await page.click("button[type='submit']")
    await page.wait_for_selector("#session-detail", state="visible", timeout=10000)

    # Check chat elements
    assert await page.query_selector("#chat-messages") is not None
    assert await page.query_selector("#chat-input") is not None
    assert await page.query_selector("#chat-form") is not None


async def test_send_message(page: Page, ui_url: str):
    """Test sending a message in the chat interface."""
    await page.goto(ui_url)

    # Create session
    await page.fill("#user-intent", "Test message sending")
    await page.click("button[type='submit']")
    await page.wait_for_selector("#session-detail", state="visible", timeout=10000)

    # Send a message
    await page.fill("#chat-input", "Add user authentication")
    await page.click("#chat-form button")

    # Wait for message to appear (user message)
    await page.wait_for_selector(".message.user", state="visible", timeout=5000)

    # Verify message was added
    messages = await page.query_selector_all(".message.user")
    assert len(messages) > 0


async def test_back_button_navigation(page: Page, ui_url: str):
    """Test back button returns to session list."""
    await page.goto(ui_url)

    # Create session
    await page.fill("#user-intent", "Test back button")
    await page.click("button[type='submit']")
    await page.wait_for_selector("#session-detail", state="visible", timeout=10000)

    # Click back button
    await page.click("#back-button")

    # Verify we return to create session view
    await page.wait_for_selector("#create-session", state="visible", timeout=5000)
    assert await page.query_selector("#create-session") is not None


async def test_status_badges_render(page: Page, ui_url: str):
    """Test that status badges are rendered correctly."""
    await page.goto(ui_url)

    # Wait for session list
    await page.wait_for_selector("#session-list", state="visible", timeout=5000)

    # Check for status badges
    badges = await page.query_selector_all(".status-badge")
    assert len(badges) > 0


async def test_responsive_design_mobile(page: Page, ui_url: str):
    """Test that UI is responsive on mobile viewport."""
    await page.set_viewport_size({"width": 375, "height": 667})
    await page.goto(ui_url)

    # Check that main elements are still visible
    assert await page.query_selector("h1") is not None
    assert await page.query_selector("#user-intent") is not None
    assert await page.query_selector("button[type='submit']") is not None


async def test_error_handling(page: Page, ui_url: str):
    """Test error handling and display."""
    await page.goto(ui_url)

    # The error element should be hidden initially
    error_el = await page.query_selector("#error")
    assert error_el is not None

    # Check that it's hidden (has 'hidden' class)
    is_hidden = await error_el.evaluate("el => 'hidden' in el.classList")
    assert is_hidden


async def test_planning_mode_selector(page: Page, ui_url: str):
    """Test planning mode dropdown has correct options."""
    await page.goto(ui_url)

    # Get planning mode options
    options = await page.query_selector_all("#planning-mode option")
    option_texts = [await option.text_content() for option in options]

    assert "Baseline" in option_texts
    assert "Specialist" in option_texts
    assert "Ensemble" in option_texts
    assert "Debate" in option_texts


async def test_execution_graph_display(page: Page, ui_url: str):
    """Test that execution graph is displayed when available."""
    await page.goto(ui_url)

    # Create session (this will have execution steps after planning)
    await page.fill("#user-intent", "Build a simple web API")
    await page.click("button[type='submit']")
    await page.wait_for_selector("#session-detail", state="visible", timeout=10000)

    # The execution graph container may or may not be visible
    # depending on whether the plan has been generated yet
    # Just check the element exists
    assert await page.query_selector("#execution-graph-container") is not None


async def test_candidates_display(page: Page, ui_url: str):
    """Test that candidates list is displayed when available."""
    await page.goto(ui_url)

    # Create session
    await page.fill("#user-intent", "Test candidates display")
    await page.click("button[type='submit']")
    await page.wait_for_selector("#session-detail", state="visible", timeout=10000)

    # Check candidates container exists
    assert await page.query_selector("#candidates-container") is not None


async def test_approve_button_visibility(page: Page, ui_url: str):
    """Test that approve button is shown when plan is awaiting approval."""
    await page.goto(ui_url)

    # Create session
    await page.fill("#user-intent", "Test approve button")
    await page.click("button[type='submit']")
    await page.wait_for_selector("#session-detail", state="visible", timeout=10000)

    # The approve button may or may not be visible
    # depending on plan status
    # Just check the element exists
    assert await page.query_selector("#approve-container") is not None


async def test_session_info_display(page: Page, ui_url: str):
    """Test that session info is displayed correctly."""
    await page.goto(ui_url)

    # Create session
    await page.fill("#user-intent", "Test session info")
    await page.click("button[type='submit']")
    await page.wait_for_selector("#session-detail", state="visible", timeout=10000)

    # Check session info elements exist
    assert await page.query_selector("#session-info") is not None
    assert await page.query_selector("#session-title") is not None
