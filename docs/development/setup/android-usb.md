# Android · USB

Runs the app on a physical device connected via USB.

> [!NOTE]
> Requires the native stack already running. See [local-native.md](local-native.md).

## Steps

**1. Start the frontend**

```bash
npm run dev
```

**2. Start the tunnel**

```bash
npm run dev:tunnel
```

> [!WARNING]
> To use your own, create a tunnel via `cloudflared tunnel create <name>` and update `TUNNEL_URL` and `TUNNEL_HOST` in `scripts/tunnel.sh`.

**3. Deploy to device**

```bash
npm run deploy:android-phone
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

> [!NOTE]
> When the tunnel is active, the app is also reachable at `https://qrew-dev.uk`.
