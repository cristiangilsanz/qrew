# Emulator and Simulator

Run QREW on an Android emulator or iOS simulator for local development.


## Before you start

Build the web bundle and sync it:

```bash
cd apps/app
npm run build
npx cap sync
```


## Android emulator

### Prerequisites

Install Android Studio and Android SDK Platform 34 or later. Set `ANDROID_HOME` to your SDK directory.

### Open the project

```bash
cd apps/app
npx cap open android
```

Let Gradle sync finish in Android Studio before running.

### Run

From Android Studio, select an AVD in the toolbar and click Run.

Or from the terminal:

```bash
npx cap run android
```

### Connect to the local backend

The emulator reaches `localhost` on the host at `10.0.2.2`.

In `apps/app/.env.local`:

```
VITE_API_URL=http://10.0.2.2:8000
```

### Live reload

```bash
cd apps/app
npx cap run android --livereload --external
```

This serves the app from the Vite dev server. The emulator must be able to reach your machine on the network.


## iOS simulator

### Prerequisites

macOS only. Install Xcode 15 or later and Xcode Command Line Tools.

### Open the project

```bash
cd apps/app
npx cap open ios
```

### Run

Select a simulator in the Xcode toolbar and click Run.

Or from the terminal:

```bash
npx cap run ios
```

### Connect to the local backend

iOS simulators reach `localhost` directly. No IP substitution needed.

In `apps/app/.env.local`:

```
VITE_API_URL=http://localhost:8000
```

### Live reload

```bash
cd apps/app
npx cap run ios --livereload --external
```


## Troubleshooting

**Gradle sync fails.** Check `ANDROID_HOME` is set and the Android SDK is installed. Open Android Studio and let it download missing SDK components.

**White screen on launch.** The web bundle is missing or stale. Run `npm run build && npx cap sync` and try again.

**Plugin not implemented.** Run `npx cap sync` to ensure native plugin code is up to date.
