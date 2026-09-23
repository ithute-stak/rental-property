#!/usr/bin/env python3
"""Validate that the VPS pulls the backend image for the exact deployed release."""

from __future__ import annotations

import argparse
from pathlib import Path

from production_preflight import PreflightError, parse_env_file

IMAGE_PREFIX = "ghcr.io/ithute-stak/rental-property-api:"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True, type=Path)
    args = parser.parse_args()

    try:
        values = parse_env_file(args.env_file)
        release_sha = values.get("RELEASE_SHA", "").strip().lower()
        api_image = values.get("API_IMAGE", "").strip()
        if not release_sha:
            raise PreflightError("RELEASE_SHA is required")
        expected = IMAGE_PREFIX + release_sha
        if api_image != expected:
            raise PreflightError(f"API_IMAGE must be exactly {expected}")
    except (OSError, PreflightError) as exc:
        print(f"API image validation failed: {exc}")
        return 1

    print(f"API image validation passed: {api_image}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
