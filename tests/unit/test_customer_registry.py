"""Focused tests for the versioned customer registry contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.customer_registry import load_customer_registry


def _entry(customer_id: str = "alpha", **overrides: str) -> dict[str, str]:
    values = {
        "CUSTOMER_ID": customer_id,
        "CUSTOMER_FULL_NAME": f"Customer {customer_id}",
        "CUSTOMER_CONTACT_EMAIL": f"{customer_id}@example.org",
        "CUSTOMER_ROOT_URLS": f'["https://{customer_id}.example.org/"]',
        "BACKEND_PROMPT": "Answer using customer content.",
        "BACKEND_AGENTIC_MAX_NUM_RETRIEVALS": "3",
        "BACKEND_AGENTIC_MAX_NUM_ACTIONS": "12",
        "BACKEND_AGENTIC_MAX_LATENCY": "8",
        "BACKEND_AGENTIC_MAX_TOKEN_BUDGET": "10000",
        "BACKEND_AGENTIC_RECURSION_LIMIT": "25",
        "BACKEND_ENABLE_AGENTIC_SEARCH": "true",
        "ETL_ENABLED": "false",
        "FRONTEND_ORIGIN": f"https://chat-{customer_id}.example.org",
        "FRONTEND_LOGIN_REQUIRED": "true",
        "SEARCH_INDEX_NAME": f"index_{customer_id}",
        "LIFECYCLE_STATUS": "active",
    }
    values.update(overrides)
    return values


def _write_entry(path: Path, values: dict[str, str]) -> None:
    path.write_text(
        "".join(f"{key}={value}\n" for key, value in values.items()),
        encoding="utf-8",
    )


def _load(config_dir: Path, fallback: str = "alpha") -> None:
    load_customer_registry(config_dir, fallback_customer_id=fallback)


def test_loads_valid_registry(tmp_path: Path) -> None:
    _write_entry(tmp_path / "alpha.env", _entry())

    registry = load_customer_registry(tmp_path, fallback_customer_id="alpha")

    assert registry["alpha"].CUSTOMER_ID == "alpha"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("CUSTOMER_ID", "Alpha", "CUSTOMER_ID must match"),
        ("CUSTOMER_ROOT_URLS", "[]", "at least 1 item"),
        ("FRONTEND_ORIGIN", "not-a-url", "valid URL"),
    ],
)
def test_rejects_malformed_fields(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    _write_entry(tmp_path / "alpha.env", _entry(**{field: value}))

    with pytest.raises(ValueError, match=message):
        _load(tmp_path)


def test_rejects_missing_field(tmp_path: Path) -> None:
    values = _entry()
    del values["CUSTOMER_FULL_NAME"]
    _write_entry(tmp_path / "alpha.env", values)

    with pytest.raises(ValueError, match="CUSTOMER_FULL_NAME"):
        _load(tmp_path)


def test_rejects_unknown_field(tmp_path: Path) -> None:
    _write_entry(tmp_path / "alpha.env", _entry(UNKNOWN_FIELD="value"))

    with pytest.raises(ValueError, match="UNKNOWN_FIELD"):
        _load(tmp_path)


def test_rejects_duplicate_customer_id(tmp_path: Path) -> None:
    _write_entry(tmp_path / "alpha.env", _entry())
    _write_entry(tmp_path / "duplicate.env", _entry())

    with pytest.raises(ValueError, match="Duplicate CUSTOMER_ID 'alpha'"):
        _load(tmp_path)


def test_rejects_filename_mismatch(tmp_path: Path) -> None:
    _write_entry(tmp_path / "wrong.env", _entry())

    with pytest.raises(ValueError, match="wrong.env.*alpha.env"):
        _load(tmp_path)


def test_rejects_missing_fallback(tmp_path: Path) -> None:
    _write_entry(tmp_path / "alpha.env", _entry())

    with pytest.raises(ValueError, match="FALLBACK_CUSTOMER_ID 'missing'"):
        _load(tmp_path, fallback="missing")


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("FRONTEND_ORIGIN", "Duplicate FRONTEND_ORIGIN"),
        ("SEARCH_INDEX_NAME", "Duplicate SEARCH_INDEX_NAME"),
    ],
)
def test_rejects_duplicate_global_values(
    tmp_path: Path, field: str, message: str
) -> None:
    alpha = _entry()
    beta = _entry("beta", **{field: alpha[field]})
    _write_entry(tmp_path / "alpha.env", alpha)
    _write_entry(tmp_path / "beta.env", beta)

    with pytest.raises(ValueError, match=message):
        _load(tmp_path)


def test_rejects_missing_active_field(tmp_path: Path) -> None:
    values = _entry()
    del values["BACKEND_PROMPT"]
    _write_entry(tmp_path / "alpha.env", values)

    with pytest.raises(ValueError, match="active.*BACKEND_PROMPT"):
        _load(tmp_path)