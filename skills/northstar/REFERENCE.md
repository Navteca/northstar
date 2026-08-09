# Northstar reference

## Repository contract

```text
ROADMAP.md                         # canonical compact overview
roadmap/northstar.toml             # safe machine-readable mapping
roadmap/audit.md                   # append-only business audit
roadmap/items/RM-001.md            # complete user story and evidence
roadmap/journal/*.json             # per-operation sync results
```

## Compact roadmap

```md
| ID | P | Status | Story | Owner | Branch | GitHub | GitLab | Wayfinder | Sync |
|---|---|---|---|---|---|---|---|---|---|
| RM-024 | P1 | In Progress | [Team invitations](roadmap/items/RM-024.md) | Maya | feat/rm-024-invites | [#142](https://github.com/acme/app/issues/142) | [#87](https://gitlab.com/acme/app/-/issues/87) | [map](roadmap/maps/RM-024.md) | Synced |
```

- IDs are permanent and ascending. Priority is `P0`–`P3`.
- Work status is `Candidate`, `Planned`, `Ready`, `In Progress`, `Done`, `Deferred`, or `Retired`.
- Sync health is independent: `Local`, `Synced`, `Drift`, `Partial`, or `Error`.
- Full user story, acceptance criteria, target, dependencies, origin, Graphify evidence, and delivery evidence live in the linked brief.

## State gates

```text
Candidate → Planned → Ready → In Progress → Done
                ↘ Deferred / Retired
```

- `Ready`: complete user story and at least one checkbox acceptance criterion.
- `In Progress`: exclusive owner, target branch, and Wayfinder map.
- `Done`: all criteria checked, Graphify `Updated:` or `Verified-no-change:` evidence, delivery evidence, and no unresolved sync failure.
- Use `update` for planning states, `claim` for `In Progress`, and `close` for `Done`.

## Canonical field ownership

| Field | Owner | Remote behavior |
|---|---|---|
| ID, title, priority, user story, acceptance criteria | Northstar | Restore or explicitly import a detected edit. |
| Work status, owner, branch | Northstar workflow | Change only through claim, handoff, update, or close. |
| Implementation discussion, commits, reviews | GitHub/GitLab | Preserve and summarize; do not copy every comment into the roadmap. |
| Sync state | Northstar engine | Derived from adapter results; never use it as work status. |
| Wayfinder and Graphify evidence | Wayfinder, verified by Northstar | Required by the corresponding state gate. |

## Synchronization transaction

1. Validate the current roadmap and item brief.
2. Preview the intended local and remote changes.
3. Acquire the local workspace lock and apply atomic file writes.
4. Update every linked service using the authenticated CLI session.
5. Save individual results under `roadmap/journal/`.
6. Set `Sync` to `Synced`, `Partial`, or `Error` and append the audit record.

Partial success is not rolled back remotely. The journal preserves what succeeded so reconciliation can resume idempotently.

## Concurrent claims

The engine prevents simultaneous mutations in one working tree. Across clones, the canonical default branch is the lock authority: a staged claim is not valid until its roadmap change is committed and merged/pushed to that branch. Wayfinder must re-read the latest canonical row before implementation. Competing claims produce a Git conflict on the same row; only the merged owner is authoritative.

## GitHub adapter

Northstar uses authenticated `gh` commands. It creates and edits issues, assignments, comments, closure, and optionally adds issues to the configured GitHub Project. Project field IDs can be added to configuration in a later adapter revision without changing the roadmap schema.

## GitLab adapter

Northstar uses authenticated `glab` commands and the GitLab API. It creates and edits issues/work items, assignments, notes, and closure. Boards remain views over the configured project’s labels/statuses.

## Import rule

External work is never silently added. Preview `add --origin github|gitlab --origin-url …`; after confirmation Northstar links the existing record, records provenance in the brief and audit, creates only missing mirrors, and comments on the source that it is now governed by canonical `ROADMAP.md`.

## Item brief minimum

Each brief contains a user story, checkbox acceptance criteria, planning metadata, execution links, Graphify state, completion evidence, and append-only history. A no-code item still requires Graphify verification recorded as `Verified-no-change: <reason/evidence>`.
