# Testing

## Introduction

The project has two independent test suites, so ensure both pass before merging:

- **Frontend** : [Vitest](https://vitest.dev) + [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- **Backend** : [pytest](https://docs.pytest.org)

## Frontend

### Where Tests Live

Test files are co-located next to the source file they cover:

```
src/
  components/
    ui/
      back-button.tsx
      back-button.test.tsx   ← test file
  features/
    tickets/
      components/
        CheckoutForm.tsx
        CheckoutForm.test.tsx
```

### How To Write A Test

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { BackButton } from './back-button'

describe('BackButton', () => {
  it('renders a link when to is provided', () => {
    render(<BackButton to="/home" />)
    expect(screen.getByRole('link')).toHaveAttribute('href', '/home')
  })

  it('calls onClick when clicked', async () => {
    const onClick = vi.fn()
    render(<BackButton onClick={onClick} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledOnce()
  })
})
```

### Run All Tests

```bash
npm run test
```

### Run One File

```bash
npm run test:file -- src/components/ui/back-button.test.tsx
```

### Run One Test

```bash
npm run test:name -- "renders a link when to is provided"
```

### Coverage

```bash
npm run test:coverage
```

---

## Backend

### Where Tests Live

Test files are co-located under each service's `tests/` directory:

```
apps/api/services/identity/
  tests/
    conftest.py        ← shared fixtures
    unit/
      services/
        application/
          notification/
            masking_test.py      ← test file
          authentication/
            login_test.py        ← test file
    integration/
      login_flow_test.py         ← test file
```

### How To Write A Test

```python
from com.qode.qrew.v1.identity.services.application.notification._masking import mask_email


class TestMaskEmail:
    def test_normal_email(self) -> None:
        assert mask_email("john.doe@example.com") == "j******e@example.com"

    def test_single_char_local(self) -> None:
        assert mask_email("j@example.com") == "j*@example.com"
```

### Unit Tests

Run all services:

```bash
just test
```

Run one service:

```bash
just test-service identity
```

Run one file:

```bash
just test-file identity tests/unit/services/application/notification/masking_test.py
```

Run one test:

```bash
just test-name identity test_normal_email
```

### Integration Tests

Run all services:

```bash
just test-integration
```

Run one service:

```bash
just test-integration-service identity
```

Run one file:

```bash
just test-file identity tests/integration/login_flow_test.py
```

Run one test:

```bash
just test-name identity test_login_success
```

### Coverage

```bash
just test-coverage identity
```

### Run Everything

> [!NOTE]
> `just test-all` runs unit and integration tests across all services.