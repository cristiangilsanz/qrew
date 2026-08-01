# Capacitor

QREW is a web app wrapped in a native shell by Capacitor. The same React codebase runs in the browser and as a native Android and iOS app.

---

## Configuration

File: `apps/app/capacitor.config.ts`

| Setting | Value |
|---|---|
| App ID | `com.qrew.app` |
| App name | `Qrew` |
| Web output directory | `dist` |
| Android scheme | `https` |

The `server.url` field in the config points to the production deployment. For local development, override this via `capacitor.config.ts` or by using the `--livereload` flag when running `npx cap run`.

---

## Plugins

| Plugin | Import path | What it does |
|---|---|---|
| Camera | `@capacitor/camera` | Opens the camera for QR scanning |
| Geolocation | `@capacitor/geolocation` | Resolves venue location |
| Haptics | `@capacitor/haptics` | Vibration feedback on successful scan |
| Keyboard | `@capacitor/keyboard` | Manages keyboard insets in input flows |
| Network | `@capacitor/network` | Detects offline state |
| Preferences | `@capacitor/preferences` | Key-value storage backed by native prefs |
| PushNotifications | `@capacitor/push-notifications` | Queue alerts and event notifications |
| SplashScreen | `@capacitor/splash-screen` | Launch screen shown at startup |
| StatusBar | `@capacitor/status-bar` | Controls status bar colour and style |
| Passkeys | `@capawesome/capacitor-passkeys` | WebAuthn passkey registration and authentication |

---

## Web fallbacks

All Capacitor plugin calls are guarded for the web environment. When running in a browser, plugins either use web APIs where available or no-op gracefully.

Pattern:

```ts
import { Capacitor } from '@capacitor/core'
import { Haptics } from '@capacitor/haptics'

if (Capacitor.isNativePlatform()) {
  await Haptics.vibrate()
}
```

Use `Capacitor.isNativePlatform()` to branch logic that only makes sense on a device.

---

## Preferences vs localStorage

Use `@capacitor/preferences` for data that should persist across app reinstalls or that will be stored in the native keychain on iOS. Use `localStorage` for lightweight, non-sensitive UI preferences.

The auth store uses `localStorage` for token persistence. Anything more sensitive should go through `Preferences`.

---

## Native project files

After installing a new Capacitor plugin, sync it into the native projects:

```bash
npx cap sync
```

This copies the built web assets and installs the plugin's native code into `android/` and `ios/`.

Native project files under `android/` and `ios/` are committed to the repo. Do not manually edit files in `android/app/src/main/assets/`. They are overwritten by `cap sync`.

---

## SplashScreen

Configured to show for 2 seconds on launch with a black background and no spinner. To change the duration:

```ts
SplashScreen: {
  launchShowDuration: 2000,
}
```

To hide programmatically:

```ts
import { SplashScreen } from '@capacitor/splash-screen'
await SplashScreen.hide()
```

---

## Push notifications

Push notifications are enabled for the `badge`, `sound`, and `alert` presentation options. The registration token must be sent to the backend after the user grants permission. See the `PushNotifications` setup in the auth flow for the implementation.

---

## For setup and build steps

See [EMULATOR.md](../development/EMULATOR.md) for simulator and emulator setup, or [DEVICE.md](../development/DEVICE.md) for USB device builds.
