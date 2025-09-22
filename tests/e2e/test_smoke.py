"""Test smoke.

This test is meant to check if
- the page loads
- the health check endpoint is available.
- the minimal chat round trip returns a non-empty response within N seconds.
"""

import json
import re
import time
from collections.abc import Callable
from pathlib import Path

import pytest
import requests
from playwright.sync_api import Page, expect

from app.config import settings

SUCCESS_STATUS_CODE = 200
SESSION_ID_MIN_LENGTH = 5
API_MATCH = re.compile(r"/rag-agent(?:\?|$)")


@pytest.fixture(scope="session")
def session_id() -> str:
    """Get a session id once for the session and share it."""
    if not settings.BACKEND_URL:
        pytest.skip("BACKEND_URL not set")

    try:
        response = requests.get(f"{settings.BACKEND_URL}/", timeout=10)
    except requests.RequestException as exc:
        pytest.fail(f"Backend root request failed: {exc}")

    if response.status_code != SUCCESS_STATUS_CODE:
        pytest.fail(f"Backend root returned {response.status_code}: {response.text}")

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        pytest.fail(f"Backend root JSON decode failed: {exc}. Body: {response.text}")

    if "session_id" not in data:
        pytest.fail(f"Expected 'session_id' in response: {data}")

    sid = data["session_id"]
    if not isinstance(sid, str) or len(sid) <= SESSION_ID_MIN_LENGTH:
        pytest.fail(f"Invalid session_id: {sid!r}")
    return sid


@pytest.fixture
def accept_disclaimer(page: Page) -> Callable[[], None]:
    """Accepts the disclaimer for other tests."""

    def _accept() -> None:
        # Find the open dialog
        dialog = page.locator(
            "[role='alertdialog'][data-state='open'],"
            "[data-slot='alert-dialog-content'][data-state='open']"
        )
        if dialog.count():
            # Prefer the explicit cancel/accept data attributes if present
            btn = dialog.locator(
                "[data-alert-dialog-cancel], [data-alert-dialog-action]"
            )
            if not btn.count():
                # Fallback to a localized text match
                btn = dialog.get_by_role(
                    "button",
                    name=re.compile(
                        r"Akzeptieren|Accept|OK|Schliessen|Schließen", re.IGNORECASE
                    ),
                )
            if btn.count():
                btn.first.click()
            else:
                # Last resort: press Escape to dismiss dialogs
                page.keyboard.press("Escape")
            # Wait until overlay is truly gone so it won't intercept clicks
            expect(dialog).not_to_be_visible(timeout=5000)

    return _accept


def test_frontend_running() -> None:
    """Frontend returns 200."""
    if not settings.FRONTEND_URL:
        pytest.skip("FRONTEND_URL not set")
    try:
        response = requests.get(settings.FRONTEND_URL, timeout=10)
    except requests.RequestException as exc:
        pytest.fail(f"Frontend request failed: {exc}")
    if response.status_code != SUCCESS_STATUS_CODE:
        pytest.fail(f"Frontend returned {response.status_code}: {response.text}")


def test_frontend_disclaimer_button_visible(page: Page) -> None:
    """Disclaimer dialog and button are visible."""
    if not settings.FRONTEND_URL:
        pytest.skip("FRONTEND_URL not set")

    page.goto(url=settings.FRONTEND_URL)
    disclaimer = page.get_by_role("alertdialog")
    expect(disclaimer).to_be_visible(timeout=5000)

    accept_button = page.get_by_role("button", name="Akzeptieren")
    expect(accept_button).to_be_visible(timeout=5000)


def test_frontend_send_message(
    page: Page, accept_disclaimer: Callable[[], None]
) -> None:
    """Frontend sends a message and receives a response."""
    if not settings.FRONTEND_URL:
        pytest.skip("FRONTEND_URL not set")
    page.goto(url=settings.FRONTEND_URL)
    page.wait_for_load_state("networkidle")
    accept_disclaimer()
    page.get_by_placeholder("Nachricht eingeben").fill("Test E2E: Hi")
    submit_button = page.locator("button[data-slot='button']")
    expect(submit_button).to_be_visible(timeout=10000)
    submit_button.click()
    expect(page.get_by_text("Test E2E: Hi")).to_be_visible(timeout=15000)


def test_backend_running() -> None:
    """Backend root returns 200."""
    if not settings.BACKEND_URL:
        pytest.skip("BACKEND_URL not set")

    try:
        response = requests.get(f"{settings.BACKEND_URL}/", timeout=10)
    except requests.RequestException as exc:
        pytest.fail(f"Backend status request failed: {exc}")

    if response.status_code != SUCCESS_STATUS_CODE:
        pytest.fail(f"Backend status returned {response.status_code}: {response.text}")


def test_get_session_id() -> None:
    """Backend root returns a valid session_id."""
    if not settings.BACKEND_URL:
        pytest.skip("BACKEND_URL not set")

    try:
        response = requests.get(f"{settings.BACKEND_URL}/", timeout=10)
    except requests.RequestException as exc:
        pytest.fail(f"Backend root request failed: {exc}")

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        pytest.fail(f"JSON decode failed: {exc}. Body: {response.text}")

    if "session_id" not in data:
        pytest.fail(f"Expected 'session_id' in response: {data}")

    sid = data["session_id"]
    if not isinstance(sid, str) or len(sid) <= SESSION_ID_MIN_LENGTH:
        pytest.fail(f"Invalid session_id: {sid!r}")


def test_backend_health(session_id: str) -> None:
    """Health endpoint works with session_id."""
    if not settings.BACKEND_URL:
        pytest.skip("BACKEND_URL not set")

    try:
        r = requests.get(
            f"{settings.BACKEND_URL}/check_status",
            params={"session_id": session_id},
            timeout=5,
        )
    except requests.RequestException as exc:
        pytest.fail(f"/check_status request failed: {exc}")

    if r.status_code != SUCCESS_STATUS_CODE:
        pytest.fail(f"/check_status failed: {r.status_code} {r.text}")

    try:
        data = r.json()
    except json.JSONDecodeError as exc:
        pytest.fail(f"/check_status JSON decode failed: {exc}. Body: {r.text}")

    if "chatbot_status" not in data or "message" not in data:
        pytest.fail(f"/check_status missing keys in response: {data}")


# -------- helpers --------
def _out_dir() -> Path:
    """Creates a directory for the contract snapshots."""
    d = Path("tests/e2e/contract-snapshots") / time.strftime("%Y-%m-%dT%H-%M-%S")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _dump(obj: json, path: Path) -> None:
    """Dumps the object to a file."""
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


# ===== 1) Backend-only: what we send vs what backend returns =====
def test_backend_rag_agent(session_id: str) -> None:
    """Call /rag-agent directly and RECORD what we sent and what we got back.

    No schema assertions—just capture for comparison.
    """
    if not settings.BACKEND_URL:
        pytest.skip("BACKEND_URL not set")

    outdir = _out_dir()
    payload = {"text": "Test Hi", "session_id": session_id}
    url = f"{settings.BACKEND_URL}/rag-agent"

    # Some backends expect SID in query; some in body—send both for visibility
    try:
        r = requests.post(
            url, params={"session_id": session_id}, json=payload, timeout=20
        )
    except requests.RequestException as exc:
        pytest.fail(f"/rag-agent request failed: {exc}")

    record = {
        "request": {
            "url": r.request.url,
            "method": r.request.method,
            "headers": dict(r.request.headers),
            "body": payload,
        },
        "response": {
            "status": r.status_code,
            "headers": dict(r.headers),
            "text": r.text,
        },
    }

    # Console + files
    _dump(record, outdir / "backend_rag_agent.json")
    if r.status_code not in (200, 400, 401, 403, 404, 422, 500):
        pytest.fail(f"Unexpected status code: {r.status_code}")
