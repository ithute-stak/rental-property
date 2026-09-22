#!/usr/bin/env python3
"""Publish a signed Android App Bundle to Google Play's internal track.

The script intentionally supports only the internal track. It is used by the protected
Android production workflow after the bundle has been built, signature-verified,
checksummed and attested. Service-account JSON is read from an environment variable
and is never written to the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

ANDROID_PUBLISHER_SCOPE = "https://www.googleapis.com/auth/androidpublisher"
API_ROOT = "https://androidpublisher.googleapis.com/androidpublisher/v3"
UPLOAD_ROOT = "https://androidpublisher.googleapis.com/upload/androidpublisher/v3"
DEFAULT_CREDENTIAL_ENV = "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON"


class PublishError(RuntimeError):
    pass


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"Google Play publish error: {message}")


def require_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        fail(f"bundle does not exist or is empty: {path}")


def load_service_account(env_name: str) -> dict:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        fail(f"{env_name} is required")
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"{env_name} is not valid JSON: {exc}")
    if not isinstance(info, dict):
        fail(f"{env_name} must contain a JSON object")
    for key in ("client_email", "private_key", "token_uri"):
        if not str(info.get(key, "")).strip():
            fail(f"{env_name} is missing {key}")
    return info


def build_session(service_account_info: dict):
    try:
        import requests
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except ImportError as exc:
        fail(
            "publishing dependencies are missing; install google-auth and requests "
            f"({exc})"
        )

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=[ANDROID_PUBLISHER_SCOPE],
    )
    credentials.refresh(Request())
    if not credentials.token:
        fail("Google service account did not return an access token")

    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {credentials.token}",
            "User-Agent": "mosala-rentals-release/1.0",
        }
    )
    return session


def checked(response, action: str):
    if 200 <= response.status_code < 300:
        return response
    detail = response.text.strip()
    if len(detail) > 1200:
        detail = detail[:1200] + "..."
    raise PublishError(
        f"{action} failed with HTTP {response.status_code}: {detail or '<empty response>'}"
    )


def publish_internal(
    *,
    session,
    bundle: Path,
    application_id: str,
    release_name: str,
) -> str:
    package = quote(application_id, safe="")
    edit_id: str | None = None

    try:
        created = checked(
            session.post(
                f"{API_ROOT}/applications/{package}/edits",
                json={},
                timeout=60,
            ),
            "create Google Play edit",
        ).json()
        edit_id = str(created.get("id", "")).strip()
        if not edit_id:
            raise PublishError("Google Play did not return an edit id")

        with bundle.open("rb") as stream:
            uploaded = checked(
                session.post(
                    f"{UPLOAD_ROOT}/applications/{package}/edits/{quote(edit_id, safe='')}/bundles",
                    params={"uploadType": "media"},
                    headers={"Content-Type": "application/octet-stream"},
                    data=stream,
                    timeout=600,
                ),
                "upload Android App Bundle",
            ).json()

        version_code = str(uploaded.get("versionCode", "")).strip()
        if not version_code.isdigit():
            raise PublishError("Google Play did not return a valid bundle versionCode")

        checked(
            session.put(
                f"{API_ROOT}/applications/{package}/edits/{quote(edit_id, safe='')}/tracks/internal",
                json={
                    "track": "internal",
                    "releases": [
                        {
                            "name": release_name,
                            "versionCodes": [version_code],
                            "status": "completed",
                        }
                    ],
                },
                timeout=60,
            ),
            "assign release to Google Play internal track",
        )

        checked(
            session.post(
                f"{API_ROOT}/applications/{package}/edits/{quote(edit_id, safe='')}:commit",
                json={},
                timeout=60,
            ),
            "commit Google Play edit",
        )
        return version_code
    except Exception:
        if edit_id:
            try:
                session.delete(
                    f"{API_ROOT}/applications/{package}/edits/{quote(edit_id, safe='')}",
                    timeout=30,
                )
            except Exception:
                pass
        raise


def write_github_output(version_code: str) -> None:
    output = os.getenv("GITHUB_OUTPUT", "").strip()
    if not output:
        return
    with Path(output).open("a", encoding="utf-8") as handle:
        handle.write(f"version_code={version_code}\n")
        handle.write("track=internal\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--application-id", required=True)
    parser.add_argument("--release-name", required=True)
    parser.add_argument(
        "--service-account-env",
        default=DEFAULT_CREDENTIAL_ENV,
        help="environment variable containing the Google Play service-account JSON",
    )
    args = parser.parse_args()

    application_id = args.application_id.strip()
    if not application_id or "." not in application_id:
        fail("application id is invalid")
    release_name = args.release_name.strip()
    if not release_name:
        fail("release name is required")

    bundle = args.bundle.resolve()
    require_file(bundle)
    service_account_info = load_service_account(args.service_account_env)
    session = build_session(service_account_info)

    try:
        version_code = publish_internal(
            session=session,
            bundle=bundle,
            application_id=application_id,
            release_name=release_name,
        )
    except PublishError as exc:
        fail(str(exc))
    finally:
        session.close()

    write_github_output(version_code)
    print(
        f"Published {bundle.name} to Google Play internal track "
        f"for {application_id} as versionCode {version_code}."
    )


if __name__ == "__main__":
    main()
