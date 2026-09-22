# Android physical-device release acceptance

A green CI build proves that Mosala Rentals compiles, packages, signs, migrates, and passes automated tests. It does **not** prove that the production build behaves correctly on a real phone, with real permissions, mobile networks, Google Maps, background/resume transitions, or the final production API configuration.

Use this checklist for every production Android release candidate before uploading the signed `.aab` to a public Play Store track. Record the results in a release-acceptance GitHub issue and attach screenshots or screen recordings for any failure that is difficult to reproduce.

## Release candidate identity

Record all of the following before testing:

- Git commit SHA used for the release.
- Android application ID: `ls.co.mosala.rentals`.
- `version_name` and `version_code`.
- Production release workflow run URL.
- SHA-256 checksum of the generated `.aab`.
- Device manufacturer/model, Android version, and available storage.
- Network used for each connectivity test: Wi-Fi and mobile data where available.

Do not approve a release candidate whose bundle cannot be traced back to a green `main` commit and the protected **Android Production Release** workflow.

## Installation and upgrade

- Install the release candidate on a clean Android device or Play internal-test installation.
- Confirm the application label is **Mosala Rentals** and the app launches without a crash or blank screen.
- Confirm the Mosala branding/logo renders correctly on the initial screen.
- Background the app, reopen it, rotate the device where supported, and confirm the current workflow remains usable.
- Upgrade over the previous approved version and confirm existing login/session state and locally stored preferences do not cause a startup failure.
- Confirm uninstall/reinstall produces a clean first-run state.

## Authentication and session lifecycle

Test with at least one house seeker, one landlord, and one administrator account in the release environment.

- Register a new house seeker and sign in.
- Register/sign in a landlord and complete the landlord profile flow.
- Confirm invalid credentials show a controlled error and never expose stack traces or server internals.
- Close and reopen the app and confirm an authenticated session restores correctly.
- Exercise token refresh by leaving a session active long enough or using the test environment controls available for release validation.
- Log out and confirm protected screens/data are no longer available.
- Where available, use **log out all devices** and confirm another active device/session can no longer refresh its session.

## Marketplace feed and search

- Confirm the live feed loads active properties from the release API rather than seed/demo data.
- Pull to refresh and confirm loading/refresh states are visible and do not duplicate cards.
- Search by an exact area/town name and by a partial/fuzzy term.
- Apply price/location filters and confirm returned properties satisfy the selected constraints.
- Confirm an anonymous or unbooked seeker cannot see the exact physical address, latitude, or longitude of a protected listing.
- Open a property with multiple units and confirm room/unit prices, availability and future availability dates are correct.
- Confirm property images load on both Wi-Fi and mobile data and failure placeholders behave correctly when an image cannot load.

## Google Maps and location

The production build must use the restricted production Android Maps key, not the CI placeholder.

- Open every screen that renders or launches location/map functionality.
- Confirm the map loads without an API-key or authorization watermark/error.
- Confirm a property pin corresponds to the expected property location.
- Deny location permission and confirm the app remains usable with an understandable fallback.
- Grant location permission and confirm current-location dependent features behave correctly.
- Revoke permission from Android Settings while the app is backgrounded, return to the app, and confirm it handles the changed permission state safely.
- Confirm exact private location remains hidden until the business rule allowing its disclosure is satisfied.

## Landlord and advert lifecycle

Using a release-environment test landlord:

- Complete and submit landlord verification.
- Confirm the administrator can approve or reject the landlord and the landlord receives the expected state/notification.
- Create a property and at least one rental unit.
- Add/edit listing content and media before submission.
- Submit the property for review.
- Approve the property as administrator.
- Quote the advertising charge.
- Submit an advertising payment reference as landlord and verify it as administrator.
- Activate the property and confirm it appears in the public feed.
- Confirm an unapproved/unpaid advert cannot be activated through the app UI.

## Booking and payment lifecycle

Use two different seeker accounts when practical so booking contention is tested.

- Acquire a booking hold for an available unit.
- Attempt to acquire the same unit from a second seeker while the hold is active and confirm the conflict is clearly presented.
- Complete the first booking before the hold expires.
- Confirm the unit moves into the booking-pending state and can no longer be double-booked.
- Submit a booking payment reference.
- Confirm the administrator sees the payment-review item.
- Confirm the payment and verify the seeker and landlord both receive the expected booking confirmation.
- Confirm the booked seeker can now access the exact property location where the product rule allows it.
- Confirm a rejected/cancelled unpaid booking releases the unit back to the correct availability state.

Do not use real customer money for release acceptance unless Mosala has explicitly designated a production-safe low-value transaction procedure. Prefer a configured test/staging payment path where possible.

## Tenancy, notice and re-advertising

- Activate/check in a confirmed booking on or after the allowed move-in date.
- Confirm the unit becomes occupied and the seeker account receives tenant access/state where expected.
- Submit notice with a future move-out date and allow re-advertising.
- Confirm the unit becomes `vacating_soon` and displays the correct future availability date to seekers.
- End the tenancy and confirm the unit enters inspection rather than becoming immediately available when inspection is required.
- Complete the move-out inspection and confirm the unit returns to `available` with the expected date.

## Realtime and notifications

- Keep a landlord or seeker signed in while another account/admin performs an action that should create a notification.
- Confirm the realtime notification arrives without manually refreshing.
- Background the app and return; confirm the app reconnects or recovers cleanly.
- Disable networking temporarily, restore it, and confirm the app can recover without requiring a force-close.
- Confirm duplicate realtime reconnects do not create visibly duplicated notifications or repeated state transitions.

## Network resilience and error states

Run the critical seeker flow and at least one landlord/admin flow under degraded conditions.

- Start the app with airplane mode enabled and confirm an offline/error state is shown rather than an endless spinner.
- Restore connectivity and retry without restarting the app.
- Interrupt connectivity during feed refresh, booking submission and a non-destructive form submission; verify the app reports uncertainty safely and does not silently duplicate the action.
- Switch from Wi-Fi to mobile data while signed in.
- Confirm server validation errors are displayed as user-actionable messages.
- Confirm HTTP 401/403 behavior does not leave the user viewing protected stale data.

## Performance and usability smoke test

- Cold launch is responsive enough to show meaningful progress rather than an apparently frozen screen.
- Scroll a feed containing enough listings to exercise image loading and pagination/long-list behavior.
- Open and close property details repeatedly and watch for crashes, obvious memory-related degradation, or broken navigation.
- Confirm major screens remain usable with Android font/display scaling increased.
- Confirm touch targets, dialogs and bottom sheets remain reachable on a small-screen Android device.

## Privacy and data handling

- Confirm protected address/GPS information is absent before authorization and present only after the intended booking/viewing rule is satisfied.
- Confirm logout removes access to cached protected screens when navigating back through the app.
- Confirm no passwords, refresh tokens, payment references, API secrets, Maps secrets, or raw authorization headers appear in user-visible error messages.
- Inspect screenshots/recordings attached to the release issue and redact personal/test-account information before sharing them outside the release team.

## Go / no-go rule

A production release is **GO** only when all of the following are true:

- The tested commit is the exact commit used by the protected production bundle workflow.
- Required CI jobs are green, including the rental lifecycle acceptance gate and signed APK/AAB packaging gates.
- The production `.aab` signature verifies and its recorded SHA-256 matches the artifact being considered for Play Store upload.
- Critical flows in this checklist pass on at least one real Android device.
- Maps works using the production-restricted Android API key.
- No unresolved blocker or high-severity regression remains in auth, payments, booking exclusivity, privacy/location access, or tenancy state transitions.
- A named release approver records the final decision in the release-acceptance issue.

If any critical item fails, mark the candidate **NO-GO**, link the defect, fix it in a new commit, generate a new bundle, and repeat the affected acceptance sections. Never reuse the approval from an older artifact or commit.
