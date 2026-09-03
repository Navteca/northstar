# Northstar reference

## Repository contract

```text
ROADMAP.md                     canonical compact portfolio table
roadmap/northstar.toml         GitHub repository, identities, profile, policy (no credentials)
roadmap/bin/                   vendored engine used by CI (northstar.py, northstar_admin.py)
roadmap/items/RM-001.md        full user story, plan, execution, and evidence
roadmap/audit.md               human-readable lifecycle audit
roadmap/audit.chain.jsonl      SHA-256-linked machine-verifiable audit
roadmap/journal/*.json         one record per synchronization attempt
roadmap/archive/*.md           archived rows; briefs stay in place
roadmap/views/*.md             generated owner/status/priority projections
roadmap/dashboard.html         generated read-only dashboard
roadmap/.notification-cursor   webhook delivery cursor
roadmap/.northstar.lock        working-tree mutation lock (gitignored)
```

## Compact roadmap

```md
| ID | P | Status | Story | Owner | Branch | Issue | Plan | Sync |
|---|---|---|---|---|---|---|---|---|
| RM-024 | P1 | Planning | [Team invitations](roadmap/items/RM-024.md) | Maya | feat/rm-024-invitations | [#142](https://github.com/acme/app/issues/142) | [map](https://github.com/acme/app/issues/155) | Synced |
```

- `Issue` is the one GitHub issue for the item, or `—`. It is created on `add` or first `pickup` when GitHub is enabled, and idempotently: the engine searches for `[RM-###]` in issue titles before creating.
- `Plan` is one canonical planning artifact. The brief records `Plan kind` (`Direct`, `Wayfinder`, `Spec Kit`) and `Execution method` (`Native`, `RPI`).
- `Sync` is `Local` (no issue or GitHub disabled), `Synced`, `Error` (roadmap changed, issue update failed; retryable), or `Drift` (remote differs and the team chose to leave it).
- Story, criteria, dependencies, optional target date, origin, context, and delivery evidence live in the brief.

## Lifecycle

```text
Candidate → Planned → Ready → In Progress → Done
                         ↘ Planning → Ready
                         ↘ Blocked ↗
          ↘ Deferred / Retired
```

| From | To |
|---|---|
| Candidate | Planned, Deferred, Retired |
| Planned | Ready, Deferred, Retired |
| Ready | Planning, In Progress, Deferred, Retired |
| Planning | Ready, Blocked |
| In Progress | Blocked, Done |
| Blocked | Planning, In Progress, Ready |
| Deferred | Planned, Retired |
| Done, Retired | terminal |

The engine refuses any other move. The `policy` command re-checks the same table between a pull request's base and head so a hand edit cannot bypass it.

- `Ready`: valid story and criteria.
- `Planning`: owner, branch, non-Direct plan kind, and one `Plan`.
- `In Progress`: owner and branch. A plan is optional.
- `Blocked`: keeps owner and context.
- `Done`: every criterion checked, durable context, delivery evidence, branch, and a recorded sync result.

## Synchronization

1. Validate the roadmap and brief.
2. Preview the local and remote change.
3. Take the working-tree lock and write files atomically.
4. Push one event to the linked issue: assign and comment for pickup and handoff, comment for updates, close with comment for closeout. Comments carry `[northstar:RM-###][op:<id>]` so retries are recognizable.
5. Write the journal record and set `Sync`.

A failed remote step never rolls back the roadmap. `northstar_admin.py retry` replays the last journaled event for every `Error` row.

## Concurrent pickup

The lock protects one working tree. Across clones, the shared default branch is the authority: a pickup counts once its roadmap change lands there, and competing edits touch the same row and conflict visibly. The optional claim workflow serializes pickups per item on the server and resolves the claimant from the GitHub actor.

## Import rule

External issues are imported with `add --origin github --origin-url <issue>`. Northstar links the original instead of duplicating it, records provenance in the brief, and comments on the issue that it is now governed by `ROADMAP.md`.
