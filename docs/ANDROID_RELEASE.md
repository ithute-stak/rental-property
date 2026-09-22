# Android production release

Mosala Rentals keeps generated Flutter Android runner files and all signing material out of Git. The production workflow generates Android scaffolding inside GitHub Actions, applies the checked-in release configuration, and produces a signed Android App Bundle (`.aab`) for Play Store upload.

## Permanent Android identity

The default application ID is:

```text
ls.co.mosala.rentals
```

Treat this as permanent once the first Play Store release is published. The workflow exposes the application ID as a manual release input only so it can still be corrected before the first publication.

The app label is `Mosala Rentals`.

## Production GitHub environment

Create a GitHub environment named `production`. Configure deployment protection or required reviewers there if desired, then add the release configuration below.

Repository/environment variable:

```text
MOSALA_PRODUCTION_API_BASE_URL=https://<production-api-domain>/api/v1
```

Required Actions secrets:

```text
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_ALIAS
ANDROID_KEY_PASSWORD
GOOGLE_MAPS_API_KEY_ANDROID
```

Do not commit any of those values.

## Create the Android upload keystore

Generate the upload key once on a trusted machine and keep an offline backup:

```bash
keytool -genkeypair -v \
  -keystore mosala-upload-keystore.jks \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -alias upload
```

Encode it for the GitHub secret:

```bash
base64 -w 0 mosala-upload-keystore.jks
```

Store that output as `ANDROID_KEYSTORE_BASE64`. Store the keystore password, alias, and key password in the matching secrets. Keep the original keystore and credentials in a secure offline backup; losing the upload key can disrupt future releases.

## Google Maps Android key

The Maps API key is injected only during the build. The built app necessarily contains the key, so security comes from Google Cloud API restrictions rather than secrecy alone.

Restrict `GOOGLE_MAPS_API_KEY_ANDROID` to the Android application ID and signing certificate. For Play Store installs, use the Google Play **app-signing** certificate SHA-1 after Play App Signing is enabled. If direct/internal builds signed with the upload key also need Maps access, add that certificate fingerprint separately.

To inspect an upload-key fingerprint locally:

```bash
keytool -list -v -keystore mosala-upload-keystore.jks -alias upload
```

## Build a production bundle

Run **Android Production Release** from GitHub Actions and provide:

- `version_name`, for example `1.0.0`
- `version_code`, a positive integer that must increase for each Play Store upload
- the application ID, normally `ls.co.mosala.rentals`

The workflow will:

1. validate versioning and protected production configuration;
2. run Flutter analysis and tests;
3. generate the Android runner ephemerally;
4. inject the Mosala application ID, app label, Internet permission, Maps key placeholder, and upload-key signing configuration;
5. build a signed release `.aab` against the production API URL;
6. verify the bundle signature;
7. generate a SHA-256 checksum; and
8. upload the `.aab` and checksum as a 30-day workflow artifact.

The workflow does **not** automatically publish to Google Play. Keeping bundle generation and store publication separate gives Mosala a final approval point before a release reaches users.

## CI release-smoke build

Normal CI uses the same Android preparation script with a dummy Maps key and Flutter's generated debug signing for the release-smoke APK. This validates package identity, manifest configuration, Gradle/native plugin compatibility, and release compilation without exposing or requiring production secrets.
