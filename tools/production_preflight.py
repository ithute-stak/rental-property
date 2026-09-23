#!/usr/bin/env python3
"""Fail closed when Mosala production configuration still looks like a placeholder.

This module intentionally uses only the Python standard library so it can run on a
fresh VPS and in GitHub Actions before application dependencies are installed.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
APPLICATION_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}$")
BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
MAPS_KEY_RE = re.compile(r"^AIza[0-9A-Za-z_-]{30,}$")
PRODUCTION_API_DOMAIN = "api.mama.ithute.co.ls"

RESERVED_SUFFIXES = (".example", ".invalid", ".test", ".localhost")
PLACEHOLDER_MARKERS = (
    "replace_with",
    "replace-with",
    "changeme",
    "change-me",
    "change-this",
    "placeholder",
    "example.com",
    "example.net",
    "example.org",
)


class PreflightError(ValueError):
    pass


def _fail(message: str) -> None:
    raise PreflightError(message)


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def _require(mapping: dict[str, str], name: str) -> str:
    value = mapping.get(name, "").strip()
    if not value:
        _fail(f"{name} is required")
    if _is_placeholder(value):
        _fail(f"{name} still contains a placeholder value")
    return value


def _validate_public_hostname(value: str, name: str) -> str:
    host = value.strip().lower().rstrip(".")
    if not host or len(host) > 253 or "." not in host:
        _fail(f"{name} must be a fully-qualified public DNS hostname")
    if host == "localhost" or host.endswith(RESERVED_SUFFIXES):
        _fail(f"{name} cannot use a reserved or local hostname")
    if _is_placeholder(host):
        _fail(f"{name} still contains a placeholder hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        _fail(f"{name} must use a DNS hostname rather than an IP address")
    labels = host.split(".")
    label_re = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
    if any(not label_re.fullmatch(label) for label in labels):
        _fail(f"{name} contains an invalid DNS label")
    return host


def _validate_https_url(value: str, name: str, *, expected_host: str | None = None) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        _fail(f"{name} must be an HTTPS URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        _fail(f"{name} cannot contain userinfo, query parameters, or fragments")
    host = _validate_public_hostname(parsed.hostname, f"{name} host")
    if expected_host is not None and host != expected_host:
        _fail(f"{name} host must match {expected_host}")
    return value.strip()


def validate_api_base_url(value: str) -> None:
    parsed = urlparse(
        _validate_https_url(
            value,
            "production API base URL",
            expected_host=PRODUCTION_API_DOMAIN,
        )
    )
    if parsed.path.rstrip("/") != "/api/v1":
        _fail("production API base URL must end exactly in /api/v1")


def validate_android_release(
    *,
    api_base_url: str,
    version_name: str,
    version_code: str,
    application_id: str,
    environment: dict[str, str],
    require_google_play: bool,
) -> None:
    if not SEMVER_RE.fullmatch(version_name):
        _fail("version_name must use x.y.z format")
    if not version_code.isdigit() or int(version_code) <= 0:
        _fail("version_code must be a positive integer")
    if not APPLICATION_ID_RE.fullmatch(application_id):
        _fail("application_id is invalid")
    if application_id != "ls.co.mosala.rentals":
        _fail("production releases are locked to application ID ls.co.mosala.rentals")

    validate_api_base_url(api_base_url)

    maps_key = _require(environment, "GOOGLE_MAPS_API_KEY")
    if not MAPS_KEY_RE.fullmatch(maps_key):
        _fail("GOOGLE_MAPS_API_KEY does not look like a production Google API key")

    for name in (
        "ANDROID_KEYSTORE_BASE64",
        "ANDROID_KEYSTORE_PASSWORD",
        "ANDROID_KEY_ALIAS",
        "ANDROID_KEY_PASSWORD",
    ):
        value = _require(environment, name)
        if name.endswith("PASSWORD") and len(value) < 8:
            _fail(f"{name} must be at least 8 characters")

    if require_google_play:
        raw_service_account = _require(environment, "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON")
        try:
            service_account = json.loads(raw_service_account)
        except json.JSONDecodeError as exc:
            raise PreflightError("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON is not valid JSON") from exc
        if service_account.get("type") != "service_account":
            _fail("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON must contain a service_account credential")
        for field in ("project_id", "private_key", "client_email"):
            if not str(service_account.get(field, "")).strip():
                _fail(f"GOOGLE_PLAY_SERVICE_ACCOUNT_JSON is missing {field}")


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            _fail(f"{path}:{line_number} is not NAME=value syntax")
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            _fail(f"{path}:{line_number} contains an invalid environment variable name")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[name] = value
    return values


def validate_server_environment(values: dict[str, str]) -> None:
    api_domain = _validate_public_hostname(_require(values, "API_DOMAIN"), "API_DOMAIN")
    media_domain = _validate_public_hostname(_require(values, "MEDIA_DOMAIN"), "MEDIA_DOMAIN")
    if api_domain == media_domain:
        _fail("API_DOMAIN and MEDIA_DOMAIN must be different hostnames")

    api_host_bind = _require(values, "API_HOST_BIND")
    try:
        bind_address = ipaddress.ip_address(api_host_bind)
    except ValueError as exc:
        raise PreflightError("API_HOST_BIND must be a loopback IP address") from exc
    if not bind_address.is_loopback:
        _fail("API_HOST_BIND must be loopback-only so the raw API cannot bypass Caddy/TLS")

    api_host_port = _require(values, "API_HOST_PORT")
    if not api_host_port.isdigit() or not 1 <= int(api_host_port) <= 65535:
        _fail("API_HOST_PORT must be an integer between 1 and 65535")

    tls_email = _require(values, "TLS_EMAIL")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", tls_email):
        _fail("TLS_EMAIL is invalid")
    if _is_placeholder(tls_email):
        _fail("TLS_EMAIL still contains a placeholder value")

    app_version = _require(values, "APP_VERSION")
    if not SEMVER_RE.fullmatch(app_version):
        _fail("APP_VERSION must use x.y.z format")
    release_sha = _require(values, "RELEASE_SHA")
    if not SHA_RE.fullmatch(release_sha):
        _fail("RELEASE_SHA must be the full 40-character deployed Git commit SHA")

    postgres_db = _require(values, "POSTGRES_DB")
    postgres_user = _require(values, "POSTGRES_USER")
    if not IDENTIFIER_RE.fullmatch(postgres_db):
        _fail("POSTGRES_DB contains unsupported characters")
    if not IDENTIFIER_RE.fullmatch(postgres_user):
        _fail("POSTGRES_USER contains unsupported characters")

    secrets = {
        "POSTGRES_PASSWORD": _require(values, "POSTGRES_PASSWORD"),
        "REDIS_PASSWORD": _require(values, "REDIS_PASSWORD"),
        "AUTH_SECRET_KEY": _require(values, "AUTH_SECRET_KEY"),
        "OBJECT_STORAGE_SECRET_KEY": _require(values, "OBJECT_STORAGE_SECRET_KEY"),
    }
    minimum_lengths = {
        "POSTGRES_PASSWORD": 24,
        "REDIS_PASSWORD": 24,
        "AUTH_SECRET_KEY": 32,
        "OBJECT_STORAGE_SECRET_KEY": 24,
    }
    for name, secret in secrets.items():
        if len(secret) < minimum_lengths[name]:
            _fail(f"{name} is too short for production")
    if len(set(secrets.values())) != len(secrets):
        _fail("production database, Redis, auth, and object-storage secrets must be distinct")

    bucket = _require(values, "OBJECT_STORAGE_BUCKET")
    if not BUCKET_RE.fullmatch(bucket) or ".." in bucket or ".-" in bucket or "-." in bucket:
        _fail("OBJECT_STORAGE_BUCKET is not a safe S3-style bucket name")
    _require(values, "OBJECT_STORAGE_ACCESS_KEY")

    public_storage_url = _require(values, "OBJECT_STORAGE_PUBLIC_BASE_URL")
    parsed_storage = urlparse(
        _validate_https_url(
            public_storage_url,
            "OBJECT_STORAGE_PUBLIC_BASE_URL",
            expected_host=media_domain,
        )
    )
    if parsed_storage.path.rstrip("/").split("/")[-1] != bucket:
        _fail("OBJECT_STORAGE_PUBLIC_BASE_URL path must end with OBJECT_STORAGE_BUCKET")

    origins = [item.strip() for item in _require(values, "CORS_ORIGINS").split(",") if item.strip()]
    if not origins:
        _fail("CORS_ORIGINS must contain at least one origin")
    for origin in origins:
        parsed = urlparse(_validate_https_url(origin, "CORS_ORIGINS entry"))
        if parsed.path not in {"", "/"}:
            _fail("CORS_ORIGINS entries must be origins, not URLs with paths")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mosala production release preflight")
    subparsers = parser.add_subparsers(dest="command", required=True)

    server = subparsers.add_parser("server", help="Validate a production VPS env file")
    server.add_argument("--env-file", required=True, type=Path)

    android = subparsers.add_parser("android", help="Validate Android production release inputs")
    android.add_argument("--api-base-url", required=True)
    android.add_argument("--version-name", required=True)
    android.add_argument("--version-code", required=True)
    android.add_argument("--application-id", required=True)
    android.add_argument("--require-google-play", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        if args.command == "server":
            validate_server_environment(parse_env_file(args.env_file))
        else:
            validate_android_release(
                api_base_url=args.api_base_url,
                version_name=args.version_name,
                version_code=args.version_code,
                application_id=args.application_id,
                environment=dict(os.environ),
                require_google_play=args.require_google_play,
            )
    except (OSError, PreflightError) as exc:
        print(f"production preflight failed: {exc}", file=sys.stderr)
        return 1
    print("production preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
