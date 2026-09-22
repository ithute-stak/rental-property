---
name: Android release acceptance
title: "Android release acceptance: vVERSION (CODE)"
about: Record physical-device and Play Store candidate validation before production release
labels: release, android
---

# Android release acceptance

Use this issue as the auditable release record for one exact Android production candidate. Follow `docs/ANDROID_DEVICE_ACCEPTANCE.md`; do not carry approval forward from an older commit or bundle.

## Candidate identity

- Commit SHA:
- Production workflow run:
- Version name:
- Version code:
- Application ID: `ls.co.mosala.rentals`
- `.aab` SHA-256:
- Tester(s):
- Release approver:
- Device model / Android version:
- Test date:

## Automated release gates

- [ ] CI backend job is green.
- [ ] Database migrations are green.
- [ ] Backend test suite is green.
- [ ] Rental lifecycle acceptance gate is green.
- [ ] Backend container build/non-root gate is green.
- [ ] Flutter analyze/tests are green.
- [ ] Signed Android release APK gate is green.
- [ ] Signed Android `.aab` gate is green.
- [ ] `.aab` signature verification passed.
- [ ] Recorded SHA-256 matches the production bundle artifact.

## Physical-device critical path

- [ ] Clean install and launch passed.
- [ ] Upgrade over previous approved version passed.
- [ ] Mosala branding/app identity is correct.
- [ ] House-seeker registration/login/session restore/logout passed.
- [ ] Landlord login/profile/verification flow passed.
- [ ] Public feed/search/filter behavior passed.
- [ ] Protected exact address/GPS remains hidden before authorization.
- [ ] Production Google Maps loads with no key/authorization error.
- [ ] Location permission deny/grant/revoke behavior passed.
- [ ] Property + unit creation/edit/submission passed.
- [ ] Advert approval, charge, payment verification and activation passed.
- [ ] Booking hold and double-booking prevention passed.
- [ ] Booking payment submission/admin confirmation passed.
- [ ] Authorized seeker exact-location release passed.
- [ ] Tenancy activation/check-in passed.
- [ ] Notice-to-vacate and future re-advertising passed.
- [ ] Move-out/inspection/final availability passed.
- [ ] Realtime notification/reconnect behavior passed.
- [ ] Offline → online recovery passed.
- [ ] Wi-Fi ↔ mobile-data transition passed where available.
- [ ] Critical screens remain usable with increased Android font/display scaling.

## Privacy/security observations

- [ ] No protected location leaked before authorization.
- [ ] Logout prevents return to protected stale screens/data.
- [ ] No password/token/API secret/raw authorization header appears in UI errors.
- [ ] Test screenshots/recordings are safe to retain/share internally.

## Defects / evidence

Link every release-affecting defect and attach useful screenshots or recordings here.

- Defects:
- Evidence:
- Retest notes:

## Final decision

Choose exactly one after all required testing is complete.

- [ ] **GO** — approved for the intended Play Store track.
- [ ] **NO-GO** — blocked; a new candidate is required after fixes.

Approver:

Decision date/time:

Notes:
