# Android TWA Build & Publish

This document outlines steps to build and publish the Admin and KDS Android Trusted Web Activity wrappers.

## Keystore
- Use a Play App Signing compatible keystore.
- Store the keystore path and passwords in the CI environment.

## Package Names
- Admin: `com.example.admin`
- KDS: `com.example.kds`

## Build
```
./scripts/twa_build.sh
```

## Play Console Listing
- Upload the release AABs for each app.
- Place screenshots and 1024x500 feature graphics in `android/metadata/<app>/en-US/images` before uploading.

## Rollout
1. Create internal test release.
2. Verify deep links and PWA update flow.
3. Promote to production with staged rollout.

## QA Checklist
- [ ] Deep links from QR codes open in the correct TWA.
- [ ] PWA updates propagate without manual app updates.
- [ ] Asset Links verified via `chrome://digital-assets-internal`.
