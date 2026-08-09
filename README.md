# Northstar

A Markdown-first product roadmap that keeps GitHub, GitLab, Wayfinder, and Graphify aligned.

Northstar gives a team one compact, reviewable `ROADMAP.md` while making ownership, handoffs, tracker state, Graphify evidence, and delivery closeout auditable. The roadmap remains canonical even when an item is tracked in GitHub and GitLab simultaneously.

## Install

```sh
npx skills@latest add Navteca/northstar
```

Choose both `northstar` and `setup-northstar`, then select the coding agents where they should be installed. Run `/setup-northstar` once in each product repository.

Requirements: Python 3.11 or newer. GitHub synchronization uses an authenticated `gh` session; GitLab synchronization uses an authenticated `glab` session. Credentials are never stored by Northstar.

## What it enforces

- Compact Markdown roadmap with permanent `RM-###` identifiers.
- Mandatory linked user-story briefs and checkbox acceptance criteria.
- Separate work status and synchronization health.
- Exclusive ownership, required target branches, and audited handoffs.
- GitHub, GitLab, or dual-platform execution records.
- Explicit import and reconciliation of externally-created work.
- Wayfinder authorization before implementation.
- Mandatory Graphify verification and roadmap/tracker updates before `Done`.

## Deterministic engine

Every mutation previews by default. Add `--apply` only after reviewing it.

```sh
python3 skills/northstar/scripts/northstar.py doctor
python3 skills/northstar/scripts/northstar.py validate
python3 skills/northstar/scripts/northstar.py add --help
python3 skills/northstar/scripts/northstar.py update --help
python3 skills/northstar/scripts/northstar.py claim --help
python3 skills/northstar/scripts/northstar.py handoff --help
python3 skills/northstar/scripts/northstar.py reconcile --help
python3 skills/northstar/scripts/northstar.py close --help
```

See [`skills/northstar/EXAMPLES.md`](skills/northstar/EXAMPLES.md) for complete workflows.

## How the pieces fit

```text
Northstar authorizes and records the roadmap item
    ↓
Wayfinder executes the claimed item and maintains its map
    ↓
Graphify records or verifies the resulting codebase knowledge
    ↓
Northstar verifies evidence and closes every linked tracker
```

## Development

```sh
python3 -m unittest discover -s skills/northstar/tests -v
python3 skills/northstar/scripts/northstar.py --help
```

The engine uses only the Python standard library. Remote adapter tests do not make network calls; live synchronization always uses the user-selected authenticated CLI sessions.
