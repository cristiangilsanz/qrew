# Contributing

## Issues

Create issues using the [Task template](.github/ISSUE_TEMPLATE/ISSUE.md). When you open or edit an issue, automation handles:

- **Auto-assign** — assigned to `@cristiangilsanz`
- **Type label** — set from the checked type (e.g. `feat`, `fix`, `docs`)
- **Branch name** — generated and written into the issue body as `<type>/QRW-<number>_<slug>`
- **Milestone** — set from the checked milestone (`API`, `App`, `Web`, `CI/CD`)
- **Project board** — issue added to the project with today as the start date

Branch names follow the pattern:

```
feat/QRW-255_ui_refinement_and_polish
fix/QRW-310_scanner_auth_timeout
docs/QRW-312_update_routing_guide
```

---

## Branches

| Branch | Purpose |
|---|---|
| `main` | Production-ready code. Protected. No direct pushes. |
| `feat/<ticket>_<slug>` | New features |
| `fix/<ticket>_<slug>` | Bug fixes |
| `chore/<slug>` | Maintenance, deps, config |
| `docs/<slug>` | Documentation only |

Branch from `main`. Keep branches short-lived. Delete after merging.

---

## Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/).

```
<type>(<scope>): <short summary>
```

**Types:** `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `style`, `ci`, `build`, `revert`

**Scopes:** `api`, `app`, `android`, `ios`, `identity`, `catalog`, `sales`, `ticketing`, `payments`, `entry`, `gateway`

```
feat(app): add resale market hub
fix(api): enforce ongoing event edit restriction
chore(android): update capacitor configs
docs: add frontend routing guide
```

- Lowercase subject, no trailing period
- Keep the summary under 72 characters
- Add a body when the why is not obvious from the title

---

## Pull Requests

1. Open a PR against `main` using the [PR template](.github/PULL_REQUEST_TEMPLATE.md)
2. Title must follow Conventional Commits format — enforced by CI (`pr-linter`)
3. All commit messages in the branch must also follow the format
4. Link the related ticket with `Closes QRW-<number>` — this triggers automation:
   - Type label and milestone copied from the linked issue
   - End date set on the project item when merged
5. All CI checks must pass before merging
6. At least one approval required
7. Squash merge to keep `main` history clean

---

## CI

| Workflow | Trigger | What it does |
|---|---|---|
| `api-ci` | Push / PR | Lint, typecheck, test all API services |
| `app-ci` | Push / PR | Lint, typecheck, test the frontend |
| `pr-linter` | PR opened / edited | Validates PR title and commit messages against Conventional Commits |
| `issue-labeler` | Issue opened / edited | Sets label, branch name, milestone, project item, start date |
| `pr-labeler` | PR opened / edited / merged | Copies label and milestone from linked issue; sets end date on merge |
| `codeql` | Push / PR | Static security analysis |
| `secret-scan` | Push / PR | Scans for accidentally committed secrets |
| `api-release-versioning` | Push to `main` | Bumps service versions on release |

---

## Code Standards

### Backend

- Formatter: `ruff format`
- Linter: `ruff check`
- Type checker: `pyright`
- Tests: `pytest`

```bash
just api-lint
just api-test
```

### Frontend

- Formatter: `prettier`
- Linter: `eslint`
- Type checker: `tsc --noEmit`
- Tests: `vitest`

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

## Adding a New API Service

1. Copy an existing service as a template (e.g. `audit`)
2. Add it to `docker-compose.yml`
3. Add a `just` recipe for `dev` and `worker`
4. Add its NATS subjects to [docs/api/messaging/subjects.md](docs/api/messaging/subjects.md)
5. Write an overview doc in `docs/api/services/<name>/`
