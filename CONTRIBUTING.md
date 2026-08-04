# Contributing

## Introduction

This document describes how to contribute to the project.

1. [Getting Started](#getting-started)
2. [Reporting Issues](#reporting-issues)
3. [Creating Pull Requests](#creating-pull-requests)
4. [Testing](#testing)
5. [Code of Conduct](#code-of-conduct)

## Getting Started

Install all required tools and configure your environment before contributing.

See [Prerequisites](docs/development/prerequisites.md), [Configuration](docs/development/configuration.md), and the [Setup guides](docs/development/setup/).

## Reporting Issues

Create issues using the [Task template](.github/ISSUE_TEMPLATE/ISSUE.md).

When you open or edit an issue, automation handles:

- **Auto-assign:** Assigned to the repo owner
- **Type label:** Set from the checked type
- **Branch name:** Generated as `<type>/QRW-<number>_<slug>` and written into the issue body
- **Milestone:** Set from the checked milestone
- **Project board:** Added with today as the start date

## Creating Pull Requests

#### Branches

Branches use the auto-generated name from the issue.

| Branch | Purpose |
|---|---|
| `main` |Protected |
| `feat/<ticket>_<slug>` | New feature |
| `fix/<ticket>_<slug>` | Bug fix |
| `refactor/<ticket>_<slug>` | Refactor |
| `perf/<ticket>_<slug>` | Performance Improvement |
| `test/<ticket>_<slug>` | Tests |
| `chore/<slug>` | Maintenance  |
| `ci/<slug>` | CI/CD changes |
| `docs/<slug>` | Documentation |
| `style/<slug>` | Code Style |
| `build/<slug>` | Build System |
| `revert/<slug>` | Revert Changes |

> [!NOTE]
> Always branch from `main`. Keep them short-lived and delete after merging.

#### Commits

Commits follow [Conventional Commits](https://www.conventionalcommits.org/) specification.

```
<type>(<scope>): <short summary>
```

The type describes the nature of the change and the scope narrows it to the affected area:

- **Types:** `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `style`, `ci`, `build`, `revert`

- **Scopes:** `api`, `app`, `android`, `ios`, `identity`, `catalog`, `sales`, `ticketing`, `payments`, `entry`, `gateway`

A few rules to keep the history clean and readable:

- Lowercase subject.
- Keep the summary under 72 characters.
- Add a body when the why is not obvious from the title.

### Review & Merge

1. Open a PR against `main` using the [PR template](.github/PULL_REQUEST_TEMPLATE.md)
2. Title must follow Conventional Commits specification. 
3. Link the related issue with `Closes QRW-<number>`
4. All CI checks must pass before merging.
5. At least one approval required.
6. Squash merge.

## Testing

See [Testing](docs/development/testing.md).

## Code of Conduct

Be respectful and constructive. Focus feedback on the code, not the person.
