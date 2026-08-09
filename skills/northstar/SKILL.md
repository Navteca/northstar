---
name: northstar
description: Maintains a compact Markdown product roadmap and safely coordinates execution through GitHub, GitLab, Wayfinder, and Graphify. Use when creating, updating, prioritizing, claiming, handing off, importing, reconciling, or closing roadmap items, user stories, product features, or roadmap tasks.
---

# Northstar

Northstar governs the roadmap; Wayfinder executes authorized work. `ROADMAP.md` is canonical.

The user expresses intent in natural language. The agent runs the bundled engine internally; never ask the user to translate their request into Python or CLI flags. Show human-readable previews and results, not raw commands, unless the user asks for troubleshooting details.

## Intent routing

| User intent | Internal operation |
|---|---|
| Set up or connect services | `/setup-northstar`, then `doctor` / `init` |
| Create or import a story | `add` |
| Refine, reprioritize, defer, or retire | `update` |
| Pick up, start, or claim work | `claim` |
| Transfer ownership | `handoff` |
| Check or repair GitHub/GitLab drift | `reconcile` |
| Finish or deliver work | `close` |

## Start every operation

1. Locate `ROADMAP.md` and `roadmap/northstar.toml`. If absent, offer `/setup-northstar`.
2. Run the bundled engine's `validate` operation internally.
3. Use the engine for mutations; do not hand-edit governed fields when an operation exists.
4. Run the operation in preview mode, translate the preview into plain language, and obtain confirmation before applying external or lock-changing operations.

See [REFERENCE.md](REFERENCE.md) for the schema, ownership rules, state machine, synchronization contract, and concurrency model. See [EXAMPLES.md](EXAMPLES.md) for internal engine recipes.

## Create or import

- Require a full “As a/an/the …, I want …, so that …” user story and checkbox acceptance criteria in the linked brief.
- Assign the next permanent sequential ID; never renumber or reuse IDs.
- A native item may create GitHub and GitLab records after approved setup. An imported item links its source, records provenance, and marks the remote record as imported into canonical `ROADMAP.md`.

## Update and prioritize

Use `northstar.py update` for title, priority, and planning-state changes. Require an actor and reason. Keep work status separate from sync health.

## Claim and hand off

- Claim only a `Ready` item with an owner, target branch, and Wayfinder map. The engine locks it exclusively and records the event in the brief, audit log, journal, and linked trackers.
- The claim is authoritative only after its canonical roadmap change reaches the default branch. Wayfinder must wait for that point.
- Collaborators may join without replacing the owner.
- The current owner may hand off. A designated product owner/maintainer may override with `--override`; a reason is always mandatory.

## Reconcile

- Never silently import remote changes. Compare them and ask whether to import, restore the canonical roadmap state, or ignore and mark drift.
- An item may link GitHub, GitLab, or both. Publish to every linked service; journal partial failures and set `Sync` to `Partial` or `Error` without changing work `Status`.
- Resolve outstanding sync state before closeout.

## Finish

1. Verify every acceptance criterion is checked.
2. Have Wayfinder update Graphify. If the graph does not change, record `Verified-no-change:` with evidence.
3. Run the close preview, confirm it, then apply it.
4. Do not mark `Done` until Graphify evidence, delivery evidence, `ROADMAP.md`, item brief, audit log, and every linked tracker are current.

## Guardrails

- Never store credentials; use authenticated `gh` and `glab` sessions selected during setup.
- Never overwrite drift, override a lock, create external records, or close remote work without confirmation.
- GitHub/GitLab updates are the v1 team signal. Do not send chat notifications unless an adapter is configured later.
