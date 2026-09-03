# Complete Northstar workflow

The user speaks naturally; the assistant operates the engine and `gh` internally.

## 1. Set up

> Set up Northstar here and link it to acme/product on GitHub.

Northstar detects an existing roadmap before creating one, shows the authenticated `gh` account, asks for the repository and optional Project title, previews `ROADMAP.md` and `roadmap/northstar.toml`, vendors the engine into `roadmap/bin/`, and offers the policy workflow. Companions are reported and offered, never installed silently.

## 2. Add a story

> Add a P0 item for workspace invitations. As a workspace admin, I want to invite teammates and choose their roles, so that I can onboard my team without support. It must validate email addresses, allow role selection, prevent double acceptance, and record invitation events.

Northstar allocates `RM-001`, writes the brief, and, with approval, creates the GitHub issue `[RM-001] Workspace invitations`.

## 3. Pick up clear work

> Let Maya pick up RM-001 on feat/rm-001-invitations.

Northstar checks the item is `Ready` and unowned, previews the ownership change and the issue assignment, then applies both. No plan is needed because the work is clear.

## 4. Use Wayfinder for foggy work

> RM-002 is too ambiguous. Let Iker pick it up on feat/rm-002-usage-dashboard for planning with Wayfinder.

Northstar hands Wayfinder that one row and brief. Wayfinder creates one map on the GitHub issue; Northstar writes the map URL to `Plan`, sets `Planning`, and locks the item to Iker. When the map clears, `link-plan` records the durable context and returns the item to `Ready`.

## 5. Use Spec Kit for a formal feature

> RM-003 needs a formal specification before implementation.

Northstar records `Plan kind: Spec Kit` and requires the spec link before the item can leave `Planning`. If the repository uses cc-rpi, the teammate can also choose `Execution method: RPI`; Northstar's gates do not change.

## 6. Block and hand off

> RM-001 is blocked on vendor API keys.

> Hand RM-001 from Maya to Iker because Maya moved to incident response.

`update --status Blocked` is a legal move from `In Progress`. The handoff records previous owner, new owner, actor, reason, and time, reassigns the issue, and comments on it.

## 7. Finish

> RM-001 is finished. Verify every criterion, record PR #160, and close it.

Northstar requires checked criteria, delivery evidence, and durable context, then updates the brief, the row, the audit trail, and closes the issue with a comment.

## 8. Import work created outside Northstar

> Import GitHub issue https://github.com/acme/product/issues/151 as a P1 candidate.

Northstar links the original, records its origin, and comments on it that it is now governed by `ROADMAP.md`.

## 9. Reconcile drift

> Check RM-001 for drift between the roadmap and its issue.

Northstar reports state and assignee differences and asks whether to restore canonical roadmap state, import the change through a normal operation, or leave the row marked `Drift`.

## 10. Operate

If an issue update fails, the row shows `Sync: Error` and the roadmap change stands. `retry` replays it. With the optional workflows installed, roadmap pull requests are policy-checked, pickups can be serialized on the server, drift is reported daily, old rows are archived weekly, and lifecycle events can reach a webhook.
