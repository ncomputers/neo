# Android TWA Publish Guide

This document outlines the steps required to build and release the Android Trusted Web Activity (TWA) wrappers for the Admin and KDS applications.

## Keystore
- Use the shared `neo.keystore` file stored in the secure credentials store.
- Keystore alias: `neo`
- Ensure the keystore password and key password are provided via environment variables `TWA_KEYSTORE_PASSWORD` and `TWA_KEY_PASSWORD`.

## Package Names
- **Admin**: `com.neo.admin.twa`
- **KDS**: `com.neo.kds.twa`

## Building
Run the helper script to assemble release builds for both TWAs:

```bash
./scripts/twa_build.sh
```

## Play Store Listing
Metadata templates live under `android/metadata/**`. Update the text and graphics before publishing.

## Rollout Steps
1. Upload the generated `.aab` files to the Play Console.
2. Attach corresponding metadata and graphics.
3. Submit for review and roll out to production once approved.
