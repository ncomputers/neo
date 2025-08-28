# KDS TWA

Placeholder for Android Trusted Web Activity wrapping the Kitchen Display System.

Generate project with Bubblewrap:
```
bubblewrap init --manifest=https://example.com/kds/expo/manifest.json --directory android/kds-twa
```

Features to configure:
- start_url: https://<prod-domain>/kds/expo
- orientation landscape
- keep screen on
- back button disabled on main route
- immersive mode with long-press exit
- offline banner when network drops
- icons and splash from `static/pwa`
