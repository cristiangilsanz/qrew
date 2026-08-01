# Physical Device

Run QREW on a real Android or iOS device connected via USB.


## Before you start

Build the web bundle and sync it:

```bash
cd apps/app
npm run build
npx cap sync
```


## Android via USB

### Prerequisites

- USB debugging enabled on the device: Settings > Developer Options > USB Debugging
- Device authorized on first connection when prompted
- Android Studio installed with ADB in your PATH

Verify ADB sees the device:

```bash
adb devices
```

### Run

Connect the device, then from Android Studio select it in the toolbar and click Run.

Or from the terminal:

```bash
npx cap run android
```

### Connect to the local backend

The device must be on the same network as your machine, or you can use USB port forwarding.

USB forwarding via ADB:

```bash
adb reverse tcp:8000 tcp:8000
```

Then in `apps/app/.env.local`:

```
VITE_API_URL=http://localhost:8000
```

Alternatively, use your machine's local IP:

```
VITE_API_URL=http://192.168.1.x:8000
```

### Live reload

```bash
cd apps/app
npx cap run android --livereload --external
```

The device must be on the same Wi-Fi network as your machine. ADB reverse does not apply to live reload traffic.


## iOS via USB

### Prerequisites

macOS only. Trust the device in Xcode when prompted. A valid Apple Developer account may be required for deployment to a physical device.

### Run

Connect the device. In Xcode, select it as the run target and click Run.

Or from the terminal:

```bash
npx cap run ios
```

### Connect to the local backend

Use your machine's local IP address. iOS devices cannot use `localhost` to reach the host machine.

In `apps/app/.env.local`:

```
VITE_API_URL=http://192.168.1.x:8000
```

Find your local IP:

```bash
ipconfig getifaddr en0
```

The device and your machine must be on the same network.

### Live reload

```bash
cd apps/app
npx cap run ios --livereload --external
```


## Troubleshooting

**ADB device not found.** Check USB debugging is enabled and the device is authorized. Try `adb kill-server && adb start-server`.

**Network calls fail.** Confirm `VITE_API_URL` points to the machine IP, not `localhost`. Verify both are on the same network.

**iOS code signing error.** Open Xcode, go to Signing and Capabilities, and select your development team.
