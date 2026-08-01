# Contributing

## Branching

| Branch | Purpose |
|---|---|
| `main` | Production-ready code. Protected. No direct pushes. |
| `feat/<ticket>_<slug>` | New features, e.g. `feat/QRW-255_ui_refinement` |
| `fix/<ticket>_<slug>` | Bug fixes |
| `chore/<slug>` | Maintenance, deps, config |
| `docs/<slug>` | Documentation only |

Branch from `main`. Keep branches short-lived. Delete after merging.

---

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/).

```
<type>(<scope>): <short summary>
```

**Types:** `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `style`

**Scopes:** `api`, `app`, `android`, `ios`, `identity`, `catalog`, `sales`, `ticketing`, `payments`, `entry`, `gateway`

**Examples:**

```
feat(app): add resale market hub
fix(api): enforce ongoing event edit restriction
chore(android): update capacitor configs
docs: add frontend routing guide
```

- Subject line in lowercase, no trailing period
- Keep the summary under 72 characters
- Add a body if the why is not obvious from the title

---

## Pull Requests

1. Open a PR against `main`
2. Title must follow conventional commits format
3. Fill in the PR description: what changed and why
4. Link the related ticket, e.g. `Closes QRW-255`
5. All CI checks must pass before merging
6. At least one approval required
7. Squash merge to keep `main` history clean

---

## Code Standards

### Backend

- Formatter: `ruff format`
- Linter: `ruff check`
- Type checker: `pyright`
- Tests: `pytest`

Run all checks:

```bash
just api-lint
just api-test
```

### Frontend

- Formatter: `prettier`
- Linter: `eslint`
- Type checker: `tsc --noEmit`
- Tests: `vitest`

Run all checks:

```bash
cd apps/app
npm run lint
npm run typecheck
npm run test:run
```

---

## Local Setup

See [docs/development/](docs/development/).

---

## Adding a New Service

1. Copy an existing service as a template, e.g. `audit`
2. Add it to `docker-compose.yml`
3. Add a `just` recipe for dev and worker
4. Add its NATS subjects to `docs/api/services/subjects.md`
5. Write an overview doc in `docs/api/services/<name>/`
