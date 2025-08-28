# Admin TWA

Placeholder for Android Trusted Web Activity wrapping the Admin PWA.

Generate project with Bubblewrap:
```
bubblewrap init --manifest=https://example.com/admin/manifest.json --directory android/admin-twa
```

Features to configure:
- start_url: https://<prod-domain>/admin
- disable screenshots via `FLAG_SECURE`
- icons and splash from `static/pwa`
