---
name: northstar
description: Maintains a compact repository-owned product roadmap and coordinates prioritization, pickup, ownership, handoffs, tracker links, reconciliation, and closeout. Use when creating or updating roadmap items, choosing the next item, importing GitHub/GitLab work, handing work to a teammate, or auditing delivery history.
---

# Northstar

Northstar is the portfolio and handoff layer. `ROADMAP.md` is the canonical compact index; linked briefs, tracker issues, plans, pull requests, and repository context hold the detail.

Users speak naturally. Operate the bundled engine internally and show plain-language previews. Do not ask users to run its commands unless troubleshooting.

## Route the intent

| Intent | Operation |
|---|---|
| Set up or connect services | `/setup-northstar`, then `doctor` / `init` |
| Create or import a story | `add` |
| Refine, reprioritize, defer, or retire | `update` |
| Pick up or start one item | `pickup` |
| Attach or finish a discovery plan | `link-plan` |
| Transfer ownership | `handoff` |
| Check or repair tracker drift | `reconcile` |
| Finish delivery | `close` |

## Begin every operation

1. Find `ROADMAP.md` and `roadmap/northstar.toml`; offer `/setup-northstar` when absent.
2. Validate the roadmap and linked brief.
3. Preview the operation and explain it in ordinary language.
4. Confirm before changing ownership, external trackers, imported work, or closeout.
5. Apply through the bundled engine and report local plus per-service results.

## Govern roadmap work

- Every row has a permanent ascending `RM-###` ID, `P0`–`P3` priority, mandatory linked user story, and checkbox acceptance criteria. Actively owned work also requires its target branch; expected completion remains optional in the brief.
- One `Home` tracker owns execution context: `github`, `gitlab`, or `local`. A row may still link both GitHub and GitLab for team visibility.
- `Plan` points to one authoritative planning artifact. Every brief records `Plan kind: Direct`, `Wayfinder`, or `Spec Kit`; non-direct routes require an approved plan before active pickup.
- Work status and sync health are independent.
- Imported work is explicitly marked at its source as imported into canonical `ROADMAP.md`.

## Pick up and hand off

- Pick up only a `Ready` item that is unowned or already reserved to the same teammate. Require its target branch, record one owner, and notify every linked tracker.
- If the work is already clear, move directly to `In Progress`; Wayfinder is not required.
- If the work is large or foggy, offer Wayfinder. Create its map only on `Home`, write its URL to `Plan`, and use `Planning` until the map clears. Wayfinder then writes durable context back and returns the item to `Ready`; it never marks delivery `Done`.
- If the feature needs formal requirements, acceptance boundaries, or multi-step design, offer Spec Kit. Link the approved specification in `Plan`, then return the item to `Ready` for implementation.
- If the repository uses cc-rpi, select `Execution method: RPI` at pickup. Let cc-rpi run Research → Plan → Implement → Validate, while Northstar retains the owner lock, target branch, plan link, handoff/audit record, and mandatory roadmap update after each meaningful phase and at closeout. RPI is an execution method, not another `Plan kind`.
- The canonical lock is effective after the roadmap change reaches the shared default branch. Re-read it before work starts.
- Handoffs preserve the item and plan, require a reason, and record previous owner, new owner, actor, and timestamp. Maintainer overrides must be explicit.

## Finish every item

1. Verify every acceptance criterion.
2. Record durable context for the next teammate. Prefer Graphify when installed and useful; otherwise link repository docs, decisions, commits, PRs/MRs, or tracker evidence.
3. Record delivery evidence, update `ROADMAP.md` and the brief, synchronize all linked trackers, and append the audit/journal entries.
4. Mark `Done` only after those updates succeed locally; report any `Partial` or `Error` sync separately.

See [REFERENCE.md](REFERENCE.md) for the contract and [EXAMPLES.md](EXAMPLES.md) for internal recipes.

## Guardrails

- Never store credentials; use the authenticated `gh` and `glab` sessions approved during setup.
- Never silently choose a side during drift, override a lock, create external records, or close remote work.
- Northstar is not an implementation planner, project-management UI, or chat notifier. Delegate discovery to Wayfinder and keep detailed execution/audit evidence in the repository and trackers.
