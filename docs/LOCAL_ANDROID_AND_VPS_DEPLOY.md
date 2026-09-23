# Local Android build and VPS API image deployment

This is the preferred Mosala Rentals release flow when the Android APK is built on a trusted local workstation and the backend is deployed to the VPS from an immutable GHCR image.

## 1. Update the local workstation

From the local production repository root:

```bash
git fetch origin main
git switch main
git merge --ff-only origin/main
```

Confirm the exact source revision:

```bash
git rev-parse HEAD
```

The Android app must target:

```text
https://api.mama.ithute.co.ls/api/v1
```

## 2. Build a release APK locally

The repository intentionally does not commit generated Android runner files. Generate them locally, then apply the checked-in Mosala release configuration.

```bash
cd mobile
flutter pub get
flutter analyze
flutter test
flutter create \
  --platforms=android \
  --org ls.co.mosala \
  --project-name rental_property \
  --no-pub \
  .
```

For a signed production/device-test APK, export the signing and Maps inputs only in the local shell:

```bash
export GOOGLE_MAPS_API_KEY='<production Android Maps key>'
export ANDROID_KEYSTORE_PATH='/absolute/path/to/mosala-upload-keystore.jks'
export ANDROID_KEYSTORE_PASSWORD='<keystore password>'
export ANDROID_KEY_ALIAS='upload'
export ANDROID_KEY_PASSWORD='<key password>'

python3 tool/prepare_android_release.py \
  --application-id ls.co.mosala.rentals \
  --signed

flutter build apk \
  --release \
  --dart-define=API_BASE_URL=https://api.mama.ithute.co.ls/api/v1
```

The APK is produced at:

```text
mobile/build/app/outputs/flutter-apk/app-release.apk
```

Verify and record its checksum:

```bash
sha256sum build/app/outputs/flutter-apk/app-release.apk
```

Do not commit the generated `mobile/android` directory, keystore, Maps key, or passwords.

## 3. Backend image publication

After the release change reaches `main`, the `Backend API Image` workflow publishes:

```text
ghcr.io/ithute-stak/rental-property-api:<full-git-sha>
```

It also updates the convenience `:main` tag, but production deployment must use the immutable full-SHA tag.

## 4. VPS production environment

On the VPS, `deploy/.env.production` must use matching release identity and backend image values:

```dotenv
RELEASE_SHA=<40-character-main-commit-sha>
API_IMAGE=ghcr.io/ithute-stak/rental-property-api:<same-40-character-main-commit-sha>
API_DOMAIN=api.mama.ithute.co.ls
MEDIA_DOMAIN=media.mama.ithute.co.ls
API_HOST_BIND=127.0.0.1
API_HOST_PORT=8090
```

The API image validator rejects an image tag that does not exactly match `RELEASE_SHA`.

If the GHCR package is private, authenticate on the VPS with a token that has only the package-read permission required for the image:

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u ithute-stak --password-stdin
```

Do not store that token in Git.

## 5. Pull and start on the VPS

Run the normal production preflight and the pull-based deployment path:

```bash
make prod-pull-validate
make prod-pull-up
```

This pulls the exact backend image for the migration, API and worker services. It does not rebuild backend source on the VPS. The local MinIO compatibility image is still built from the checked-in deployment Dockerfile.

Verify the private listener and the public TLS endpoint:

```bash
curl --fail --silent http://127.0.0.1:8090/api/v1/health/ready
curl --fail --silent https://api.mama.ithute.co.ls/api/v1/health/ready
bash deploy/smoke.sh
```

Do not expose port `8090` publicly. Caddy remains the public HTTPS ingress on ports 80/443.
