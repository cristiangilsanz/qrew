# Testing


## Backend tests

Tests use pytest. Each service has its own test suite under `tests/`.

### Run all backend tests

```bash
just test
```

### Run tests for one service

```bash
cd apps/api/services/identity
uv run pytest
```

With verbose output:

```bash
uv run pytest -v
```

Run a specific test file:

```bash
uv run pytest tests/unit/test_login.py
```

Run a specific test:

```bash
uv run pytest tests/unit/test_login.py::test_login_success
```

### Test structure

```
tests/
  unit/         Pure function tests, no I/O
  integration/  Tests that hit the database or NATS
  conftest.py   Shared fixtures
```

Integration tests require a running database. The test suite uses a separate test schema. Run `just db-upgrade` first to ensure migrations are applied.

### Writing backend tests

Use `pytest` fixtures for database sessions and NATS clients. Keep tests small and independent. Name tests `test_<what>_<when>_<expected>`.


## Frontend tests

Tests use Vitest and React Testing Library.

### Run all frontend tests

```bash
cd apps/app
npm run test:run
```

Watch mode:

```bash
npm run test
```

With UI:

```bash
npm run test:ui
```

Coverage report:

```bash
npm run coverage
```

### Test structure

```
src/
  components/
    ui/
      button.test.tsx
      dialog.test.tsx
  features/
    organiser/
      components/
        CreateEventForm.test.tsx
```

Tests live next to the files they test.

### Writing frontend tests

- Test component behaviour, not implementation
- Use `screen.getByRole` and `screen.getByText` over test IDs where possible
- Wrap async interactions in `act` or use `waitFor` from Testing Library
- Mock API calls at the network layer using `msw`, not by mocking modules

Example:

```tsx
import { render, screen } from '@testing-library/react'
import { StatusChip } from './status-chip'

it('renders published status', () => {
  render(<StatusChip status="published" />)
  expect(screen.getByText('Published')).toBeInTheDocument()
})
```


## Type checking

### Backend

```bash
just api-type-check
```

Or per service:

```bash
just identity-type-check
just catalog-type-check
```

### Frontend

```bash
cd apps/app
npm run typecheck
```


## Linting

### Backend

Check:

```bash
just lint-check
```

Auto-fix:

```bash
just lint-fix
```

Format check:

```bash
just format-check
```

Auto-format:

```bash
just format-fix
```

### Frontend

```bash
cd apps/app
npm run lint
npm run lint:fix
```


## Running all checks before pushing

```bash
just check
```

This runs lint, format, type checking, and tests for all backend services. Run this before opening a pull request.

For the frontend, run separately:

```bash
cd apps/app
npm run lint && npm run typecheck && npm run test:run
```


## CI

All checks run automatically on every pull request. A merge requires all checks to pass. See `.github/workflows/` for the full pipeline definition.
