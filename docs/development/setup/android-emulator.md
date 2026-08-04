# Android · Emulator

Runs the app on an Android emulator.

> [!NOTE]
> Requires the native stack already running. See [local-native.md](local-native.md).

## Steps

**1. Start the frontend**

```bash
npm run dev
```

**2. Deploy to emulator**

```bash
npm run deploy:android-emulator
```

## Ports

| Service | Port |
|---|---|
| Frontend | `5173` |
| Gateway | `8000` |
| Identity | `8001` |
| Catalog | `8002` |
| Sales | `8003` |
| Payments | `8004` |
| Ticketing | `8005` |
| Entry | `8006` |
| Audit | `8007` |
| PostgreSQL | `5432` |
| Redis | `6379` |
| NATS | `4222` |
