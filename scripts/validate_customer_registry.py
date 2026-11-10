"""Validate all entries in the customer registry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.customer_registry import load_customer_registry


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("customer_config"),
        help="Directory containing customer .env files.",
    )
    parser.add_argument(
        "--fallback-customer-id",
        default="default",
        help="Customer ID used when no customer can be resolved.",
    )
    return parser.parse_args()


def main() -> int:
    """Validate the registry and return a process exit code."""
    args = parse_args()
    try:
        registry = load_customer_registry(
            args.config_dir,
            fallback_customer_id=args.fallback_customer_id,
        )
    except (OSError, ValueError) as exc:
        print(f"Customer registry validation failed: {exc}", file=sys.stderr)  # noqa: T201
        return 1

    print(f"Validated {len(registry)} customer registry entries.")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())