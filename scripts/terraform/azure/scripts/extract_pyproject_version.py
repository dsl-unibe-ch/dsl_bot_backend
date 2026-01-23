from __future__ import annotations

import argparse
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pyproject", required=True)
    parser.add_argument("--output", required=False)
    args = parser.parse_args()

    pyproject_path = Path(args.pyproject)
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    version = data.get("project", {}).get("version")
    if not version:
        raise SystemExit("Missing [project].version in pyproject.toml")
    print(version)


if __name__ == "__main__":
    main()
