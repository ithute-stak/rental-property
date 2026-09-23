# Mosala Rentals — Mama production target

This document is the deployment contract for the first Mosala Rentals production environment.

## Public endpoints

| Purpose | Production value |
| --- | --- |
| VPS | `204.12.205.224` |
| Public API hostname | `api.mama.ithute.co.ls` |
| Public API base URL | `https://api.mama.ithute.co.ls/api/v1` |
| Public media hostname | `media.mama.ithute.co.ls` |
| Raw API listener on VPS | `127.0.0.1:8090` |
| Android application ID | `ls.co.mosala.rentals` |

The raw port is deliberately loopback-only. Do not expose TCP 8090 to the public internet. Caddy is the public entry point and terminates HTTPS on ports 80/443 before proxying to the API container.

## DNS cutover

Create these A records before starting Caddy:

```text
api.mama.ithute.co.ls    A    204.12.205.224
media.mama.ithute.co.ls  A    204.12.205.224
```

Verify both names resolve to the VPS before the production start. Caddy will obtain and renew the public TLS certificates after DNS is correct and inbound ports 80/443 reach the VPS.

## Production environment

On the VPS, create the real environment file from the checked-in template:

```bash
cp deploy/.env.production.example deploy/.env.production
chmod 600 deploy/.env.production
```

Keep these target values:

```dotenv
API_DOMAIN=api.mama.ithute.co.ls
MEDIA_DOMAIN=media.mama.ithute.co.ls
TLS_EMAIL=thekoetlisi@ithute.co.ls
API_HOST_BIND=127.0.0.1
API_HOST_PORT=8090
OBJECT_STORAGE_PUBLIC_BASE_URL=https://media.mama.ithute.co.ls/mosala-rentals
```

Generate distinct production secrets directly on the VPS. Do not put PostgreSQL, Redis, authentication, object-storage, Android signing, Maps, payment-provider, or Google Play credentials in Git.

Set `RELEASE_SHA` to the exact 40-character commit being deployed and set `APP_VERSION` to the matching semantic release version.

Before starting anything, run:

```bash
python3 tools/production_preflight.py server --env-file deploy/.env.production
```

The preflight refuses placeholder secrets, public raw-API binding, invalid release identity, invalid domains, weak/reused secrets, and inconsistent media configuration.

## Start the production stack

Use the supported production path:

```bash
make prod-validate
make prod-up
```

Then confirm container state and the private raw API listener:

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml ps
curl --fail --silent http://127.0.0.1:8090/api/v1/health/ready
```

The public verification must use HTTPS:

```bash
curl --fail --silent https://api.mama.ithute.co.ls/api/v1/health/ready
bash deploy/smoke.sh
```

Do not open port 8090 in the public firewall/security group. Public inbound access should be limited to the administrative access policy for the VPS plus HTTP/HTTPS required by Caddy.

## Initial Mosala administrator

The production administrator is provisioned after migrations have completed. The bootstrap helper never requires the password to be written to the repository or production env file.

Run:

```bash
MOSALA_ADMIN_EMAIL=thekoetlisi@ithute.co.ls \
MOSALA_ADMIN_NAME="Mosala Administrator" \
bash deploy/provision-admin.sh
```

Enter the bootstrap password at the hidden prompt. The application stores only its password hash.

If an account with the same email already exists and deliberately needs to be promoted/reset, use:

```bash
MOSALA_ADMIN_EMAIL=thekoetlisi@ithute.co.ls \
MOSALA_ADMIN_NAME="Mosala Administrator" \
MOSALA_ADMIN_UPDATE_EXISTING=true \
bash deploy/provision-admin.sh
```

Do not place the administrator password in a shell script, committed `.env` file, issue, workflow YAML, or GitHub repository variable.

## Android production configuration

Set the protected GitHub `production` environment variable:

```text
MOSALA_PRODUCTION_API_BASE_URL=https://api.mama.ithute.co.ls/api/v1
```

Keep the production Google Maps key, upload keystore/passwords, and Google Play service-account credential in protected GitHub environment secrets. The Android production workflow builds the signed AAB with this API URL and can publish only to the Play internal track when publishing is explicitly enabled.

## Release acceptance

A production candidate is GO only after all of the following are true:

1. `main` CI is green.
2. Disaster Recovery Rehearsal is green.
3. Production preflight passes on the VPS with the real environment.
4. Public `/api/v1/health/ready` reports all dependencies ready over HTTPS.
5. `deploy/smoke.sh` passes.
6. Administrator login succeeds using the configured email identity.
7. The exact signed Android candidate passes `docs/ANDROID_DEVICE_ACCEPTANCE.md` on physical Android devices.
8. The release bundle provenance/signature is verified before Play internal-track distribution.

Payment-provider production activation remains separate from application deployment: enable a concrete provider only after its official contract, webhook/signature documentation, merchant credentials, and reconciliation procedure are available.
