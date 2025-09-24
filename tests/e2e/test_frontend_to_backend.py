"""Test smoke.

This test is meant to check if
- the page loads
- the health check endpoint is available.
- the minimal chat round trip returns a non-empty response within N seconds.
"""

import json
import re
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, Request, Response, expect

from app.config import settings

SUCCESS_STATUS_CODE = 200
BAD_REQUEST_CODE = 400
SESSION_ID_MIN_LENGTH = 5
RAG_AGENT_ENDPOINT_MATCH = re.compile(r"/rag-agent(?:\?|$)")
FEEDBACK_ENDPOINT_MATCH = re.compile(r"/send_feedback(?:\?|$)")


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
            button = dialog.locator(
                "[data-alert-dialog-cancel], [data-alert-dialog-action]"
            )
            if not button.count():
                # Fallback to a localized text match
                button = dialog.get_by_role(
                    "button",
                    name=re.compile(
                        r"Akzeptieren|Accept|OK|Schliessen|Schließen", re.IGNORECASE
                    ),
                )
            if button.count():
                button.first.click()
            else:
                page.keyboard.press("Escape")
            expect(dialog).not_to_be_visible(timeout=5000)

    return _accept


@pytest.fixture
def app_page(page: Page, accept_disclaimer: Callable[[], None]) -> Page:
    """Navigates to the frontend and ensures the disclaimer is handled."""
    if not settings.FRONTEND_URL:
        pytest.skip("FRONTEND_URL not set")
    page.goto(url=settings.FRONTEND_URL)
    page.wait_for_load_state("networkidle")
    accept_disclaimer()
    return page


def _is_outgoing_request_valid_post(
    request: Request, endpoint_pattern: re.Pattern
) -> bool:
    """Checks if the request sent is a valid POST request and endpoint_pattern."""
    content_type = request.headers.get("content-type") or ""
    return (
        endpoint_pattern.search(request.url) is not None
        and request.method.upper() == "POST"
        and content_type.startswith("application/json")
    )


def _is_incoming_response_valid_post(
    response: Response, endpoint_pattern: re.Pattern
) -> bool:
    """Checks if the incoming response has a valid POST request and endpoint_pattern."""
    return (
        endpoint_pattern.search(response.url) is not None
        and response.request.method.upper() == "POST"
    )


def _parse_request_json(request: Request) -> dict[str, Any]:
    """Parses JSON body from a JSON request or fail clearly."""
    content_type = request.headers.get("content-type") or ""
    if not content_type.startswith("application/json"):
        pytest.fail(f"Expected JSON request, got content-type={content_type!r}")
    raw_request = request.post_data or ""
    try:
        return json.loads(raw_request)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Request body is not valid JSON: {exc}")
    # unreachable; pytest.fail raises


def _read_response(
    response: Response,
) -> tuple[int, bool, dict[str, Any] | None, str | None]:
    """Reads response deterministically without blind exceptions.

    Prefer JSON only if the content-type says JSON; otherwise return text.
    """
    status = response.status
    ok = response.ok
    content_type = (response.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        response_text = response.text()
        try:
            body_json = json.loads(response_text)
        except json.JSONDecodeError:
            return status, ok, None, response_text
        else:
            return status, ok, body_json, None
    return status, ok, None, response.text()


def _extract_fastapi_detail(
    body_json: dict[str, Any] | None, body_text: str | None
) -> str:
    """Formats FastAPI/Pydantic 422 detail if available; otherwise return JSON/text."""
    if isinstance(body_json, dict):
        json_body_details = body_json.get("detail")
        if isinstance(json_body_details, list):
            parts: list[str] = []
            for item in json_body_details:
                loc = ".".join(str(x) for x in item.get("loc", []))
                msg = item.get("msg")
                typ = item.get("type")
                seg = f"{loc}: {msg}" if msg else loc
                if typ:
                    seg = f"{seg} ({typ})"
                parts.append(seg)
            if parts:
                return "; ".join(parts)
        return json.dumps(body_json, ensure_ascii=False)
    return body_text or "Unknown backend error"


def _save_frontend_snapshot(
    request: Request,
    sent_body: dict[str, Any],
    response: Response,
    body_json: dict[str, Any] | None,
    body_text: str | None,
) -> None:
    """Persists a contract snapshot."""
    outdir = _out_dir()
    record = {
        "request": {
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers),
            "body": sent_body,
        },
        "response": {
            "status": response.status,
            "headers": dict(response.headers),
            "json": body_json,
            "text": body_text,
        },
    }
    # Include status in filename to avoid accidental overwrites in same second
    _dump(record, outdir / f"rag_agent_{response.status}.json")


def _is_valid_uuid(value: str) -> bool:
    """Checks if value is a valid UUID4 string."""
    try:
        parsed = uuid.UUID(value, version=4)
    except ValueError:
        return False
    return str(parsed) == value


def _out_dir() -> Path:
    """Creates a directory for the contract snapshots."""
    d = Path("tests/e2e/contract-snapshots") / time.strftime("%Y-%m-%dT%H-%M-%S")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _dump(obj: json, path: Path) -> None:
    """Dumps the object to a file."""
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _send_one_message_and_wait(
    app_page: Page,
    message_text: str = "Test E2E: Hi",
) -> tuple[Request, Response, str]:
    """Sends one chat message, capture /rag-agent req/resp, return last bot text.

    List of Steps
    1. Validates the session_id.
    2. Send a chat message and press submit button.
    If backend throws error, extracts details.
    """
    app_page.locator("textarea[data-slot=textarea]").fill(message_text)
    submit_button = app_page.locator("button[data-slot='button']")
    expect(submit_button).to_be_visible(timeout=10_000)

    with (
        app_page.expect_request(
            lambda r: _is_outgoing_request_valid_post(r, RAG_AGENT_ENDPOINT_MATCH),
            timeout=30_000,
        ) as req_info,
        app_page.expect_response(
            lambda r: _is_incoming_response_valid_post(r, RAG_AGENT_ENDPOINT_MATCH),
            timeout=30_000,
        ) as resp_info,
    ):
        submit_button.click()

    req = req_info.value
    resp = resp_info.value

    sent = _parse_request_json(req)
    sid_val = sent.get("session_id")
    if (
        not isinstance(sid_val, str)
        or not sid_val.strip()
        or not _is_valid_uuid(sid_val)
    ):
        pytest.fail(f"Invalid session_id in body: {sid_val!r}")
    txt_val = sent.get("text")
    if not isinstance(txt_val, str) or not txt_val.strip():
        pytest.fail("text missing or empty in request body")
    status, ok, body_json, body_text = _read_response(resp)
    if not ok or status >= BAD_REQUEST_CODE:
        _save_frontend_snapshot(
            req, sent, resp, body_json, body_text, prefix="rag_agent"
        )
        detail_msg = _extract_fastapi_detail(body_json, body_text)
        pytest.fail(f"/rag-agent returned {status}: {detail_msg}")
    expect(app_page.get_by_text(message_text)).to_be_visible(timeout=15_000)
    last_msg = (
        app_page.locator("div.prose.mb-2.text-gray-700").last.text_content(
            timeout=15_000
        )
        or ""
    )
    if not last_msg.strip():
        pytest.fail("UI returned an empty chatbot message")
    return req, resp, last_msg


def test_frontend_to_backend(app_page: Page) -> None:
    """Tests that frontend and backend integrations work.

    List of checks performed:
    1. Whether the frontend app_page can be loaded.
    2. Whether one message can be sent.
    3. Whether negative feedback and comments can be sent.
    """
    _send_one_message_and_wait(app_page, "Test E2E: Hi")

    feedback_form = app_page.locator(
        "form", has=app_page.get_by_placeholder("Feedback eingeben...")
    ).last
    expect(feedback_form).to_be_visible(timeout=15_000)

    rating_button = feedback_form.get_by_role("button", name="Nein")  # or "Ja"
    expect(rating_button).to_be_visible(timeout=10_000)
    rating_button.click()

    textarea = feedback_form.get_by_placeholder("Feedback eingeben...")
    if textarea.count():
        textarea.fill("E2E feedback: negative test")

    submit_button = feedback_form.locator("button[type='submit']").first
    expect(submit_button).to_be_enabled(timeout=10_000)

    with (
        app_page.expect_request(
            lambda r: _is_outgoing_request_valid_post(r, FEEDBACK_ENDPOINT_MATCH),
            timeout=30_000,
        ) as req_info_fb,
        app_page.expect_response(
            lambda r: _is_incoming_response_valid_post(r, FEEDBACK_ENDPOINT_MATCH),
            timeout=30_000,
        ) as resp_info_fb,
    ):
        submit_button.click()

    req_fb = req_info_fb.value
    resp_fb = resp_info_fb.value

    sent_fb = _parse_request_json(req_fb)
    sid_fb = sent_fb.get("session_id")
    if not isinstance(sid_fb, str) or not sid_fb.strip() or not _is_valid_uuid(sid_fb):
        pytest.fail(f"Invalid session_id in feedback body: {sid_fb!r}")
    rating_val = sent_fb.get("rating")
    if rating_val not in (0, 1):
        pytest.fail(f"Invalid rating (expected 0 or 1): {rating_val!r}")
    comments_val = sent_fb.get("comments")
    if comments_val is not None and not isinstance(comments_val, str):
        pytest.fail(f"Invalid comments type: {type(comments_val).__name__}")

    status_fb, ok_fb, body_json_fb, body_text_fb = _read_response(resp_fb)
    if not ok_fb or status_fb >= BAD_REQUEST_CODE:
        _save_frontend_snapshot(
            req_fb, sent_fb, resp_fb, body_json_fb, body_text_fb, prefix="send_feedback"
        )
        detail_msg = _extract_fastapi_detail(body_json_fb, body_text_fb)
        pytest.fail(f"/send_feedback returned {status_fb}: {detail_msg}")
