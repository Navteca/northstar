# Northstar operations

These commands are for assistants, CI, and troubleshooting. Users normally speak in natural language.

## Reliability commands

```sh
python3 skills/northstar/scripts/northstar_admin.py policy
python3 skills/northstar/scripts/northstar_admin.py retry all
python3 skills/northstar/scripts/northstar_admin.py reconcile-all --strategy report
python3 skills/northstar/scripts/northstar_admin.py compatibility
python3 skills/northstar/scripts/northstar_admin.py render
python3 skills/northstar/scripts/northstar_admin.py render --check
python3 skills/northstar/scripts/northstar_admin.py archive --apply
python3 skills/northstar/scripts/northstar_admin.py notify --dry-run
```

## Durable synchronization

Every synchronization attempt writes a journal record. Failed destinations also create a durable operation under `roadmap/outbox/`. `retry` replays only failed services and includes the operation ID in remote notes. Keep `roadmap/journal/` and `roadmap/outbox/` in Git; ignore only `roadmap/.northstar.lock`.

`reconcile-all --strategy report` is read-only and exits nonzero when it detects drift. `canonical` restores roadmap state through the normal tracker adapters. `ignore` records visible drift without selecting a remote winner.

## Server-side claims

Install exactly one claim workflow on the configured `Home` service. GitHub uses a concurrency group per `RM-###`; GitLab uses a `resource_group`. The workflow re-reads the default branch, performs pickup, validates, commits, and pushes. Do not enable independent claim authorities on both services.

Templates live under `setup-northstar/assets/github/` and `setup-northstar/assets/gitlab/`.

## Policy and generated views

`policy --base <previous-roadmap>` checks the current contract, audit chain, legal lifecycle transitions, removal through archives, and audited owner changes. `render` produces owner/status/priority views and `roadmap/dashboard.html`; these are projections and must never be edited manually.

`archive` uses `[policy].archive_after_days`, defaults to `Done`, `Deferred`, and `Retired`, preserves item briefs, and prevents ID reuse. The active item limit comes from `[policy].max_active_items`.

## Audit and notifications

Each lifecycle event appends a SHA-256-linked record to `roadmap/audit.chain.jsonl`. Protected branches and signed commits remain the trust anchor; the chain exposes accidental or unauthorized rewriting within the file.

`notify` reads unsent chain events and posts through the webhook URL named by `[notifications].webhook_url_env`. Formats are `generic`, `slack`, and `teams`. The committed `.notification-cursor` prevents duplicate delivery across ephemeral CI runners.

## Live contracts and compatibility

The opt-in live test requires `NORTHSTAR_LIVE_CONTRACTS=1` plus dedicated sandbox project variables. It creates, verifies, comments on, and closes temporary issues. Never point it at a production tracker.

`COMPATIBILITY.toml` lists required CLI capabilities. `compatibility` reports missing companions selected in `roadmap/northstar.toml`; version pinning should be added only when an upstream incompatibility is known.
