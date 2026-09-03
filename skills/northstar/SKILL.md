---
name: northstar
description: Maintains a compact repository-owned product roadmap (ROADMAP.md) and coordinates user stories, prioritization, pickup, ownership, handoffs, GitHub issue links, reconciliation, and closeout. Use when creating or updating roadmap items, choosing the next feature, importing GitHub issues, handing work to a teammate or assistant, or auditing delivery history.
---

# Northstar

`ROADMAP.md` is the canonical compact index. Linked briefs, GitHub issues, plans, and pull requests hold the detail.

Users speak naturally. Operate the bundled engine internally and show plain-language previews. Do not ask users to run its commands unless troubleshooting.

## Route the intent

| Intent | Operation |
|---|---|
| Set up or connect GitHub | `/setup-northstar`, then `doctor` / `init` |
| Create or import a story | `add` |
| Refine, reprioritize, block, defer, or retire | `update` |
| Pick up or start one item | `pickup` |
| Attach or finish a discovery plan | `link-plan` |
| Transfer ownership | `handoff` |
| Check or repair issue drift | `reconcile` |
| Finish delivery | `close` |

The engine lives at `roadmap/bin/northstar.py` in a set-up repository, or at `scripts/northstar.py` beside this file.

## Begin every operation

1. Find `ROADMAP.md` and `roadmap/northstar.toml`; offer `/setup-northstar` when absent.
2. Run the operation without `--apply` to preview it, then explain it in ordinary language.
3. Confirm before changing ownership, touching GitHub, importing work, or closing out.
4. Apply, then report the local result and the `Sync` state. A `Sync` of `Error` means the roadmap changed but the issue did not; offer `northstar_admin.py retry`.

## Govern roadmap work

- Every row has a permanent ascending `RM-###` ID, `P0`–`P3` priority, linked user story, and checkbox acceptance criteria. Owned work also has a target branch.
- `Issue` links the one GitHub issue for the item. When GitHub is enabled, the engine creates it on first pickup if it does not exist.
- `Plan` points to one planning artifact. The brief records `Plan kind: Direct`, `Wayfinder`, or `Spec Kit`; non-direct routes need a plan before active work.
- Status moves follow the engine's transition table; illegal moves are refused, not worked around.
- Imported issues are marked at the source as imported into canonical `ROADMAP.md`.

## Pick up and hand off

- Pick up only a `Ready` item that is unowned or reserved to the same teammate. Require the target branch.
- Clear work goes straight to `In Progress`. Large or foggy work can use `--planning` with a Wayfinder map or Spec Kit spec in `--plan`; the item sits in `Planning` until the plan clears and `link-plan` returns it to `Ready`.
- If the repository uses cc-rpi, record `--execution-method RPI`. It changes how the work is executed, not the roadmap gates.
- Handoffs need a reason and are recorded with previous owner, new owner, actor, and time. Only the owner hands off; maintainers use `--override`, which is audited as such.
- Across clones, the shared default branch is the lock. Re-read the row before starting work.

## Finish every item

1. Verify every acceptance criterion is checked.
2. Record durable context for the next teammate: Graphify update, repository docs, decisions, or the PR.
3. `close` with the PR as evidence. It updates the brief, the row, the audit trail, and the issue.

See [REFERENCE.md](REFERENCE.md) for the contract, [EXAMPLES.md](EXAMPLES.md) for commands, and [OPERATIONS.md](OPERATIONS.md) for CI, retry, archival, and notifications.

## Guardrails

- Never store credentials; use the authenticated `gh` session.
- Never silently pick a side during drift, override a lock, create issues, or close remote work.
- Northstar is not an implementation planner or a project-management UI. Keep execution detail in the repository and the issue.
