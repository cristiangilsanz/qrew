# Frontend App

The frontend is a React 18 single-page application that compiles to a Capacitor mobile app for Android and iOS, and also runs as a web app in the browser.

---

## Stack

| Concern | Library |
|---|---|
| Framework | React 18 |
| Routing | TanStack Router v1 |
| Server state | TanStack Query v5 |
| Styling | Tailwind CSS v3 |
| UI primitives | Radix UI |
| Forms | React Hook Form + Zod |
| Payments | Stripe.js |
| Maps | Google Maps JS API |
| i18n | react-i18next |
| Captcha | Cloudflare Turnstile |
| Mobile | Capacitor v6 |
| Build | Vite |
| Tests | Vitest + React Testing Library |

---

## Folder Structure

```
apps/app/
  src/
    assets/           Static images and icons
    components/
      layout/         App shell: BottomDock, layout wrappers
      ui/             Design system components (Button, Input, StatusChip, etc.)
    config/
      env.ts          Typed environment variable access
    features/         Domain slices (see below)
    i18n/
      locales/        en.json, es.json
    lib/
      imageUrl.ts     Event image URL resolver
      utils.ts        Shared utilities (cn, formatters)
    routes/           TanStack Router file-based routes
  public/             Static public assets (favicon, app icons)
  android/            Capacitor Android project
  ios/                Capacitor iOS project
```

### Feature Slices

Each feature owns its API client, hooks, components, and types:

```
features/
  auth/         Login, registration, passkeys, TOTP
  events/       Event listing and detail (public)
  market/       Resale listings, assignments, waitlist
  onboarding/   Phone verification, KYC, setup flow
  organiser/    Event management, venue creation, ticket types
  passkeys/     WebAuthn registration and authentication
  profile/      User profile, security log
  realtime/     Server-sent events, live queue updates
  scanner/      QR scanner for entry (ongoing events only)
  tickets/      Ticket list, QR display, checkout flow
```

---

## Environment Variables

All variables are accessed via `src/config/env.ts`. Never read `import.meta.env` directly.

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | No | Base URL for the API gateway. In dev the Vite proxy is used instead. |
| `VITE_GATEWAY_URL` | No | WebSocket URL for SSE gateway |
| `VITE_STRIPE_PUBLISHABLE_KEY` | Yes | Stripe publishable key |
| `VITE_GOOGLE_MAPS_API_KEY` | Yes | Google Maps JS API key |
| `VITE_TURNSTILE_SITE_KEY` | Yes | Cloudflare Turnstile site key |

In development, `VITE_API_URL` can be left empty. Vite proxies `/api` and `/ws` to `localhost:8000` automatically.

---

## Development Scripts

```bash
npm run dev           # Start dev server (http://localhost:5173)
npm run build         # Production build
npm run preview       # Preview production build locally
npm run lint          # ESLint
npm run typecheck     # TypeScript check
npm run test          # Vitest in watch mode
npm run test:run      # Vitest single run
npm run test:coverage # Coverage report
npm run sync          # Capacitor sync (after build)
npm run android       # Open in Android Studio
npm run ios           # Open in Xcode
```

---

## Capacitor Mobile

After any build change, sync to native projects:

```bash
npm run build
npm run sync
```

Then open in Android Studio with `npm run android` or Xcode with `npm run ios` and run from the IDE.

App icons and splash screens are generated from `assets/logo.png` using `@capacitor/assets`. The source logo is `src/assets/logo.webp`.

---

## Internationalisation

The app supports English and Spanish. Language codes are `en` and `es`. Translation files are at `src/i18n/locales/`.

All user-visible strings must use `t('key')` from `useTranslation()`. Never hardcode strings in components. All keys live in the root namespace.
