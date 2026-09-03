# Northstar operations

Commands for assistants, CI, and troubleshooting. In a set-up repository the scripts live under `roadmap/bin/`.

```sh
python3 roadmap/bin/northstar_admin.py policy [--base <previous ROADMAP.md>]
python3 roadmap/bin/northstar_admin.py retry
python3 roadmap/bin/northstar_admin.py reconcile-all --strategy report|canonical|ignore
python3 roadmap/bin/northstar_admin.py archive [--apply]
python3 roadmap/bin/northstar_admin.py render [--check]
python3 roadmap/bin/northstar_admin.py compatibility
python3 roadmap/bin/northstar_admin.py notify [--dry-run]
```

## Workflow templates

Installed by `setup-northstar` from `assets/github/`, each with approval. All reference `roadmap/bin/`, so the engine must be vendored first.

| Template | Trigger | Needs |
|---|---|---|
| `northstar-policy.yml` | pull requests touching the roadmap | nothing; read-only |
| `northstar-claim.yml` | manual dispatch by the claimant | `contents: write`; `NORTHSTAR_PUSH_TOKEN` if the default branch is protected |
| `northstar-reconcile.yml` | daily schedule | `issues: read` |
| `northstar-maintenance.yml` | weekly schedule | `contents: write`, same token note |
| `northstar-notify.yml` | every 15 minutes | `NORTHSTAR_WEBHOOK_URL` secret |

## Policy

`policy` validates the contract, verifies the audit hash chain, enforces the active-item limit from `[policy].max_active_items`, and with `--base` checks that every status change is a legal transition, that removed rows exist in an archive, and that owner changes have a handoff history event.

## Claims

The claim workflow re-reads the default branch, runs `pickup --owner-login "${{ github.actor }}" --local-only`, validates, commits the roadmap files, and pushes. A GitHub `concurrency` group per `RM-###` serializes competing claims. Because the owner is resolved from the dispatching actor through `[identities]`, nobody can claim on another person's behalf.

## Retry and reconcile

Every remote attempt writes `roadmap/journal/<timestamp>-<item>-<event>-<op>.json`. When the attempt fails the row's `Sync` is `Error`; `retry` replays the last journaled event for each such row and is safe to repeat, because issue creation searches by ID first and comments carry the operation ID.

`reconcile-all --strategy report` is read-only and exits nonzero on drift. `canonical` re-pushes roadmap state to each drifting issue. `ignore` marks the rows `Drift` without touching GitHub.

## Archive, views, notifications

`archive` moves rows in `Done`, `Deferred`, or `Retired` whose last history entry is older than `[policy].archive_after_days` into `roadmap/archive/<year>.md`. Briefs stay in place and IDs are never reused. `render` regenerates `roadmap/views/` and `roadmap/dashboard.html`; `render --check` fails when they are stale.

`notify` posts unsent audit-chain events to the webhook named by `[notifications].webhook_url_env` in `generic`, `slack`, or `teams` format, and advances the committed cursor so ephemeral runners do not resend.

## Live contract

This repository's `live-contracts.yml` runs `tests/live_tracker_contract.py` against a dedicated sandbox when `NORTHSTAR_GITHUB_TOKEN` and `NORTHSTAR_GITHUB_SANDBOX` are configured. It creates and closes one temporary issue. Never point it at a production repository.
