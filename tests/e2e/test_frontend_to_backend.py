"""Test End to End.

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
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
from playwright.sync_api import Page, Request, Response, expect

from app.agent.utils import get_customer_name_from_url
from app.config import settings

BAD_REQUEST_CODE = 400
INVOKE_AGENT_ENDPOINT_MATCH = re.compile(r"/invoke-agent(?:\?|$)")
FEEDBACK_ENDPOINT_MATCH = re.compile(r"/send-feedback(?:\?|$)")
INITIALIZE_AGENT_ENDPOINT_MATCH = re.compile(r"/initialize-agent(?:\?|$)")


@pytest.fixture
def accept_disclaimer(page: Page) -> Callable[[], None]:
    """Returns a reusablefunction to accept the disclaimer.

    When called, the functions accepts the "terms of use and disclaimer"
    dialog in the UI.
    """

    def _accept() -> None:
        """Accepts the disclaimer by clicking the button or pressing Escape."""
        dialog = page.locator(
            "[role='alertdialog'][data-state='open'],"
            "[data-slot='alert-dialog-content'][data-state='open']"
        )
        if dialog.count():
            button = dialog.locator(
                "[data-alert-dialog-cancel], [data-alert-dialog-action]"
            )
            if not button.count():
                button = dialog.get_by_role(
                    "button",
                    name=re.compile(
                        r"Akzeptieren|Accept|OK|Schliessen|Schließen", re.IGNORECASE
                    ),
                )
                page.keyboard.press("Escape")
            if button.count():
                button.first.click()
            expect(dialog).not_to_be_visible(timeout=5000)

    return _accept


@pytest.fixture
def initialize_agent_origin_url(request: pytest.FixtureRequest) -> str:
    """Return the optional --origin CLI argument."""
    return str(request.config.getoption("origin") or "").strip()


@pytest.fixture
def app_page(
    page: Page,
    accept_disclaimer: Callable[[], None],
    initialize_agent_origin_url: str,
) -> Page:
    """Navigates to the frontend, handles the disclaimer, and returns the page."""
    if not settings.FRONTEND_URL:
        pytest.skip("FRONTEND_URL not set")
    resolved_customer = (
        get_customer_name_from_url(initialize_agent_origin_url)
        if initialize_agent_origin_url
        else None
    )
    _install_initialize_agent_origin_override(page, initialize_agent_origin_url)
    with (
        page.expect_request(
            lambda r: _is_outgoing_request_valid_get(r, INITIALIZE_AGENT_ENDPOINT_MATCH),
            timeout=60_000,
        ) as request_info_root,
        page.expect_response(
            lambda r: _is_incoming_response_valid_get(r, INITIALIZE_AGENT_ENDPOINT_MATCH),
            timeout=60_000,
        ) as response_info_root,
    ):
        page.goto(url=settings.FRONTEND_URL)
    request_root = request_info_root.value
    response_root = response_info_root.value
    status, ok, body_json, body_text = _read_response(response_root)
    if not ok or status >= BAD_REQUEST_CODE:
        _save_frontend_snapshot(
            request_root, response_root, body_json, body_text, prefix="root_get"
        )
        detail = _extract_fastapi_detail(body_json, body_text)
        pytest.fail(
            f"GET / returned {status}: {detail}. "
            f"Supplied origin URL from test: {initialize_agent_origin_url or '<none>'}. "
            f"Resolved customer via get_customer_name_from_url: "
            f"{resolved_customer or '<none>'}."
        )
    page.wait_for_load_state("networkidle")

    accept_disclaimer()
    return page


def _path(url: str) -> str:
    """Return only the path part (no scheme/host/query)."""
    return urlsplit(url).path or "/"


def _override_query_origin(url: str, origin: str) -> str:
    """Return URL with an explicit origin query parameter."""
    parts = urlsplit(url)
    query_params = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "origin"]
    query_params.append(("origin", origin))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query_params, doseq=True), parts.fragment)
    )


def _install_initialize_agent_origin_override(page: Page, origin_url: str) -> None:
    """Ensure initialize-agent requests include the provided origin URL."""
    if not origin_url:
        return

    def _rewrite(route, request) -> None:
        route.continue_(url=_override_query_origin(request.url, origin_url))

    page.route("**/initialize-agent*", _rewrite)


def _is_outgoing_request_valid_post(
    request: Request, endpoint_pattern: re.Pattern
) -> bool:
    """Checks if the request sent is a valid POST request and endpoint_pattern."""
    content_type = request.headers.get("content-type") or ""
    return (
        endpoint_pattern.search(_path(request.url)) is not None
        and request.method.upper() == "POST"
        and content_type.startswith("application/json")
    )


def _is_outgoing_request_valid_get(
    request: Request, endpoint_pattern: re.Pattern
) -> bool:
    """Checks if the request sent is a valid GET request and endpoint_pattern."""
    return (
        endpoint_pattern.search(_path(request.url)) is not None
        and request.method.upper() == "GET"
    )


def _is_incoming_response_valid_post(
    response: Response, endpoint_pattern: re.Pattern
) -> bool:
    """Checks if the incoming response has a valid POST request and endpoint_pattern."""
    return (
        endpoint_pattern.search(_path(response.url)) is not None
        and response.request.method.upper() == "POST"
    )


def _is_incoming_response_valid_get(
    response: Response, endpoint_pattern: re.Pattern
) -> bool:
    """Checks if the incoming response has a valid GET request and endpoint_pattern."""
    return (
        endpoint_pattern.search(_path(response.url)) is not None
        and response.request.method.upper() == "GET"
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
    response: Response,
    body_json: dict[str, Any] | None,
    body_text: str | None,
    prefix: str = "snapshot",
) -> None:
    """Persists a contract snapshot."""
    outdir = _out_dir()

    # Parse request body only if it's a POST/PUT request with JSON content
    sent_body = None
    if request.method.upper() in ("POST", "PUT", "PATCH"):
        try:
            sent_body = _parse_request_json(request)
        except Exception:
            sent_body = {"error": "Could not parse request body"}
    
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
    _dump(record, outdir / f"{prefix}_{response.status}.json")


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
    """Sends one chat message, capture /invoke-agent req/resp, return last bot text.

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
            lambda r: _is_outgoing_request_valid_post(r, INVOKE_AGENT_ENDPOINT_MATCH),
            timeout=60_000,
        ) as request_info,
        app_page.expect_response(
            lambda r: _is_incoming_response_valid_post(r, INVOKE_AGENT_ENDPOINT_MATCH),
            timeout=60_000,
        ) as response_info,
    ):
        submit_button.click()

    request_rag = request_info.value
    response_rag = response_info.value

    sent = _parse_request_json(request_rag)
    txt_val = sent.get("text")
    if not isinstance(txt_val, str) or not txt_val.strip():
        pytest.fail("text missing or empty in request body")
    status, ok, body_json, body_text = _read_response(response_rag)
    if not ok or status >= BAD_REQUEST_CODE:
        _save_frontend_snapshot(
            request_rag, response_rag, body_json, body_text, prefix="rag_agent"
        )
        detail_msg = _extract_fastapi_detail(body_json, body_text)
        pytest.fail(f"/invoke-agent returned {status}: {detail_msg}")
    expect(app_page.get_by_text(message_text)).to_be_visible(timeout=15_000)
    last_msg = (
        app_page.locator("div.prose.mb-2.text-gray-700").last.text_content(
            timeout=15_000
        )
        or ""
    )
    if not last_msg.strip():
        pytest.fail("UI returned an empty chatbot message")
    return request_rag, response_rag, last_msg


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
            timeout=60_000,
        ) as request_info_fb,
        app_page.expect_response(
            lambda r: _is_incoming_response_valid_post(r, FEEDBACK_ENDPOINT_MATCH),
            timeout=60_000,
        ) as response_info_fb,
    ):
        submit_button.click()

    request_fb = request_info_fb.value
    response_fb = response_info_fb.value

    sent_fb = _parse_request_json(request_fb)
    comments_val = sent_fb.get("comments")
    if comments_val is not None and not isinstance(comments_val, str):
        pytest.fail(f"Invalid comments type: {type(comments_val).__name__}")
    status_fb, ok_fb, body_json_fb, body_text_fb = _read_response(response_fb)
    if not ok_fb or status_fb >= BAD_REQUEST_CODE:
        _save_frontend_snapshot(
            request_fb, response_fb, body_json_fb, body_text_fb, prefix="send_feedback"
        )
        detail_msg = _extract_fastapi_detail(body_json_fb, body_text_fb)
        pytest.fail(f"/send-feedback returned {status_fb}: {detail_msg}")


def test_backend_root_contract(page: Page) -> None:
    """Contract check for backend root."""
    if not settings.BACKEND_URL:
        pytest.skip("BACKEND_URL not set")
    page.goto(settings.FRONTEND_URL)
    page.wait_for_load_state("domcontentloaded")
    backend_url = settings.BACKEND_URL.rstrip("/")
    request = page.context.request.get(backend_url + "/initialize-agent")
    print(request.url)
    req_path = (urlsplit(request.url).path or "/").rstrip("/")
    exp_path = (urlsplit(backend_url + "/initialize-agent").path or "/").rstrip("/")
    if req_path != exp_path:
        pytest.fail(f"Root path {req_path!r} != expected {exp_path!r}.")
    status = request.status
    ctype = (request.headers.get("content-type") or "").lower()
    text = request.text()

    if status >= BAD_REQUEST_CODE:
        pytest.fail(f"GET root returned {status}: {text[:200]}")

    if "application/json" not in ctype:
        pytest.fail(f"Root content-type not JSON: {ctype!r}")

    try:
        body = json.loads(text)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Root JSON decode failed: {exc}. Body: {text[:200]}")

    sid = body.get("session_id") if isinstance(body, dict) else None
    if not (isinstance(sid, str) and _is_valid_uuid(sid)):
        pytest.fail(f"Invalid session_id from root: {sid!r}")
