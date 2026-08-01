# Internationalisation

---

## Overview

The app uses `react-i18next` for translations. All user-facing strings live in JSON locale files. The active language is persisted to `localStorage`.

Supported languages: English (`en`), Spanish (`es`).

---

## Setup

Initialised in `src/i18n/index.ts` and imported once at the app entry point. The saved language preference is read from `localStorage` under the key `qrew_lang`. If no preference exists, it falls back to English.

---

## Locale files

```
src/i18n/
  index.ts          i18next initialisation
  locales/
    en.json         English strings
    es.json         Spanish strings
```

Both files must stay in sync. Every key present in `en.json` must also exist in `es.json`.

---

## Namespaces

All translations live in the default `translation` namespace. Keys are organised by feature or page using a flat dot-notation convention:

```json
{
  "events": {
    "title": "Events",
    "empty": "No events yet"
  },
  "organiser": {
    "createEvent": "Create event",
    "editEvent": "Edit event"
  }
}
```

---

## Using translations in components

```tsx
import { useTranslation } from 'react-i18next'

function EventList() {
  const { t } = useTranslation()
  return <h1>{t('events.title')}</h1>
}
```

Interpolation:

```tsx
t('tickets.remaining', { count: 3 })
// en.json: "remaining": "{{count}} tickets remaining"
```

---

## Changing language

```tsx
import { useTranslation } from 'react-i18next'

function LanguageSwitcher() {
  const { i18n } = useTranslation()

  const toggle = () => {
    const next = i18n.language === 'en' ? 'es' : 'en'
    i18n.changeLanguage(next)
    localStorage.setItem('qrew_lang', next)
  }

  return <button onClick={toggle}>{i18n.language.toUpperCase()}</button>
}
```

---

## Adding a new string

1. Add the key and English value to `en.json`
2. Add the same key and Spanish value to `es.json`
3. Use the key in the component via `t('your.key')`

Never hardcode user-visible text directly in JSX.

---

## Adding a new language

1. Create `src/i18n/locales/<code>.json` with all keys translated
2. Import the file in `src/i18n/index.ts`
3. Add it to the `resources` object in `i18n.init`

```ts
import fr from './locales/fr.json'

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    es: { translation: es },
    fr: { translation: fr },
  },
  ...
})
```
