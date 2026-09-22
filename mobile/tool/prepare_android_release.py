#!/usr/bin/env python3
"""Prepare the ephemeral Flutter Android runner for Mosala release builds.

The repository intentionally does not commit generated Android runner files. Both CI
and the production-release workflow generate the runner first, then call this script
so application identity, network access, Maps configuration, and optional release
signing stay deterministic.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

DEFAULT_APPLICATION_ID = "ls.co.mosala.rentals"
APP_LABEL = "Mosala Rentals"
MAPS_PLACEHOLDER = "GOOGLE_MAPS_API_KEY"


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"Android release configuration error: {message}")


def validate_application_id(value: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", value):
        fail(f"invalid Android application id: {value!r}")


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        fail(f"could not locate {label} in generated Android project")
    return updated


def configure_gradle(path: Path, application_id: str, signed: bool) -> None:
    if not path.exists():
        fail(f"missing generated Gradle file: {path}")

    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        r'^(\s*)namespace\s*=\s*"[^"]+"',
        rf'\1namespace = "{application_id}"',
        "Android namespace",
    )
    text = replace_once(
        text,
        r'^(\s*)applicationId\s*=\s*"[^"]+"',
        rf'\1applicationId = "{application_id}"',
        "Android applicationId",
    )

    placeholder_line = 'manifestPlaceholders["GOOGLE_MAPS_API_KEY"]'
    if placeholder_line not in text:
        marker = "    defaultConfig {\n"
        if marker not in text:
            fail("could not locate defaultConfig block")
        replacement = (
            marker
            + '        manifestPlaceholders["GOOGLE_MAPS_API_KEY"] =\n'
            + '            System.getenv("GOOGLE_MAPS_API_KEY")\n'
            + '                ?: error("GOOGLE_MAPS_API_KEY is required")\n'
        )
        text = text.replace(marker, replacement, 1)

    if signed:
        release_signing_block = '''    signingConfigs {
        create("release") {
            val keystorePath = System.getenv("ANDROID_KEYSTORE_PATH")
                ?: error("ANDROID_KEYSTORE_PATH is required")
            storeFile = file(keystorePath)
            storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
                ?: error("ANDROID_KEYSTORE_PASSWORD is required")
            keyAlias = System.getenv("ANDROID_KEY_ALIAS")
                ?: error("ANDROID_KEY_ALIAS is required")
            keyPassword = System.getenv("ANDROID_KEY_PASSWORD")
                ?: error("ANDROID_KEY_PASSWORD is required")
        }
    }

'''
        if 'create("release")' not in text:
            marker = "    defaultConfig {\n"
            if marker not in text:
                fail("could not locate insertion point for release signing")
            text = text.replace(marker, release_signing_block + marker, 1)

        debug_signing = 'signingConfig = signingConfigs.getByName("debug")'
        release_signing = 'signingConfig = signingConfigs.getByName("release")'
        if release_signing not in text:
            if debug_signing not in text:
                fail("could not locate generated release signing configuration")
            text = text.replace(debug_signing, release_signing, 1)

    path.write_text(text, encoding="utf-8")


def configure_manifest(path: Path) -> None:
    if not path.exists():
        fail(f"missing generated Android manifest: {path}")

    text = path.read_text(encoding="utf-8")

    internet_permission = '<uses-permission android:name="android.permission.INTERNET" />'
    if internet_permission not in text:
        manifest_match = re.search(r"<manifest\b[^>]*>", text)
        if manifest_match is None:
            fail("could not locate <manifest> element")
        insert_at = manifest_match.end()
        text = text[:insert_at] + f"\n    {internet_permission}" + text[insert_at:]

    text = replace_once(
        text,
        r'android:label="[^"]*"',
        f'android:label="{APP_LABEL}"',
        "application label",
    )

    maps_metadata_name = "com.google.android.geo.API_KEY"
    if maps_metadata_name not in text:
        marker = "    </application>"
        if marker not in text:
            fail("could not locate </application> element")
        metadata = (
            '        <meta-data\n'
            '            android:name="com.google.android.geo.API_KEY"\n'
            '            android:value="${GOOGLE_MAPS_API_KEY}" />\n'
        )
        text = text.replace(marker, metadata + marker, 1)

    path.write_text(text, encoding="utf-8")


def configure_main_activity(android_root: Path, application_id: str) -> None:
    kotlin_root = android_root / "app" / "src" / "main" / "kotlin"
    candidates = list(kotlin_root.rglob("MainActivity.kt"))
    if len(candidates) != 1:
        fail(f"expected exactly one generated MainActivity.kt, found {len(candidates)}")

    source = candidates[0]
    text = source.read_text(encoding="utf-8")
    text = replace_once(text, r"^package\s+[A-Za-z0-9_.]+", f"package {application_id}", "MainActivity package")

    destination = kotlin_root.joinpath(*application_id.split("."), "MainActivity.kt")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    if source.resolve() != destination.resolve():
        source.unlink()


def validate_environment(signed: bool) -> None:
    if not os.getenv(MAPS_PLACEHOLDER, "").strip():
        fail(f"{MAPS_PLACEHOLDER} is required")

    if signed:
        required = (
            "ANDROID_KEYSTORE_PATH",
            "ANDROID_KEYSTORE_PASSWORD",
            "ANDROID_KEY_ALIAS",
            "ANDROID_KEY_PASSWORD",
        )
        missing = [name for name in required if not os.getenv(name, "").strip()]
        if missing:
            fail("missing signing environment: " + ", ".join(missing))
        keystore = Path(os.environ["ANDROID_KEYSTORE_PATH"])
        if not keystore.is_file() or keystore.stat().st_size == 0:
            fail("ANDROID_KEYSTORE_PATH does not point to a non-empty keystore")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--application-id", default=DEFAULT_APPLICATION_ID)
    parser.add_argument("--signed", action="store_true", help="configure the generated release build to use the upload keystore")
    args = parser.parse_args()

    validate_application_id(args.application_id)
    validate_environment(args.signed)

    mobile_root = Path(__file__).resolve().parents[1]
    android_root = mobile_root / "android"
    configure_gradle(android_root / "app" / "build.gradle.kts", args.application_id, args.signed)
    configure_manifest(android_root / "app" / "src" / "main" / "AndroidManifest.xml")
    configure_main_activity(android_root, args.application_id)

    print(f"Configured Android runner for {APP_LABEL} ({args.application_id}); signed={args.signed}")


if __name__ == "__main__":
    main()
