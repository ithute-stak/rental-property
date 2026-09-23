import unittest

from production_preflight import (
    PreflightError,
    validate_android_release,
    validate_server_environment,
)


class ProductionPreflightTests(unittest.TestCase):
    def server_values(self) -> dict[str, str]:
        return {
            "API_DOMAIN": "api.mosala.co.ls",
            "MEDIA_DOMAIN": "media.mosala.co.ls",
            "API_HOST_BIND": "127.0.0.1",
            "API_HOST_PORT": "8090",
            "TLS_EMAIL": "operations@mosala.co.ls",
            "APP_VERSION": "1.0.0",
            "RELEASE_SHA": "0123456789abcdef0123456789abcdef01234567",
            "CORS_ORIGINS": "https://mosala.co.ls,https://www.mosala.co.ls",
            "POSTGRES_DB": "mosala_rentals",
            "POSTGRES_USER": "mosala",
            "POSTGRES_PASSWORD": "postgres-0123456789-strong-secret",
            "REDIS_PASSWORD": "redis-0123456789-strong-secret-value",
            "AUTH_SECRET_KEY": "auth-0123456789-strong-secret-value-abcdef",
            "OBJECT_STORAGE_BUCKET": "mosala-rentals",
            "OBJECT_STORAGE_ACCESS_KEY": "mosala-storage",
            "OBJECT_STORAGE_SECRET_KEY": "storage-0123456789-strong-secret-value",
            "OBJECT_STORAGE_PUBLIC_BASE_URL": "https://media.mosala.co.ls/mosala-rentals",
        }

    def android_environment(self) -> dict[str, str]:
        return {
            "GOOGLE_MAPS_API_KEY": "AIza" + "A" * 35,
            "ANDROID_KEYSTORE_BASE64": "not-a-real-keystore-but-nonempty-for-input-validation",
            "ANDROID_KEYSTORE_PASSWORD": "strong-keystore-password",
            "ANDROID_KEY_ALIAS": "mosala-upload",
            "ANDROID_KEY_PASSWORD": "strong-key-password",
            "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON": (
                '{"type":"service_account","project_id":"mosala-release",'
                '"private_key":"-----BEGIN PRIVATE KEY-----\\nredacted\\n-----END PRIVATE KEY-----\\n",'
                '"client_email":"play-release@mosala-release.iam.gserviceaccount.com"}'
            ),
        }

    def test_server_configuration_passes_when_values_are_production_shaped(self) -> None:
        validate_server_environment(self.server_values())

    def test_server_configuration_rejects_example_domain(self) -> None:
        values = self.server_values()
        values["API_DOMAIN"] = "api.rentals.example.com"
        with self.assertRaisesRegex(PreflightError, "placeholder"):
            validate_server_environment(values)

    def test_server_configuration_rejects_public_raw_api_bind(self) -> None:
        values = self.server_values()
        values["API_HOST_BIND"] = "0.0.0.0"
        with self.assertRaisesRegex(PreflightError, "loopback-only"):
            validate_server_environment(values)

    def test_server_configuration_rejects_invalid_api_port(self) -> None:
        values = self.server_values()
        values["API_HOST_PORT"] = "70000"
        with self.assertRaisesRegex(PreflightError, "between 1 and 65535"):
            validate_server_environment(values)

    def test_server_configuration_rejects_reused_secrets(self) -> None:
        values = self.server_values()
        values["REDIS_PASSWORD"] = values["POSTGRES_PASSWORD"]
        with self.assertRaisesRegex(PreflightError, "must be distinct"):
            validate_server_environment(values)

    def test_server_configuration_requires_full_release_sha(self) -> None:
        values = self.server_values()
        values["RELEASE_SHA"] = "unknown"
        with self.assertRaises(PreflightError):
            validate_server_environment(values)

    def test_android_release_passes_with_production_shaped_inputs(self) -> None:
        validate_android_release(
            api_base_url="https://api.mosala.co.ls/api/v1",
            version_name="1.2.3",
            version_code="42",
            application_id="ls.co.mosala.rentals",
            environment=self.android_environment(),
            require_google_play=True,
        )

    def test_android_release_rejects_placeholder_api_domain(self) -> None:
        with self.assertRaises(PreflightError):
            validate_android_release(
                api_base_url="https://api.example.com/api/v1",
                version_name="1.2.3",
                version_code="42",
                application_id="ls.co.mosala.rentals",
                environment=self.android_environment(),
                require_google_play=False,
            )

    def test_android_release_rejects_wrong_application_id(self) -> None:
        with self.assertRaisesRegex(PreflightError, "locked"):
            validate_android_release(
                api_base_url="https://api.mosala.co.ls/api/v1",
                version_name="1.2.3",
                version_code="42",
                application_id="ls.co.other.app",
                environment=self.android_environment(),
                require_google_play=False,
            )

    def test_android_release_rejects_placeholder_maps_key(self) -> None:
        environment = self.android_environment()
        environment["GOOGLE_MAPS_API_KEY"] = "ci-placeholder-not-for-production"
        with self.assertRaises(PreflightError):
            validate_android_release(
                api_base_url="https://api.mosala.co.ls/api/v1",
                version_name="1.2.3",
                version_code="42",
                application_id="ls.co.mosala.rentals",
                environment=environment,
                require_google_play=False,
            )


if __name__ == "__main__":
    unittest.main()
