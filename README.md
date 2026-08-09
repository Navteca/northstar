# Northstar

A Markdown-first product-roadmap skill that keeps GitHub, GitLab, Wayfinder, and Graphify aligned.

Northstar gives a team one compact, reviewable `ROADMAP.md` while making ownership, handoffs, tracker state, Graphify evidence, and delivery closeout auditable. A roadmap item can be tracked in GitHub, GitLab, or both.

## Install

```sh
npx skills@latest add Navteca/northstar
```

Choose both `northstar` and `setup-northstar`, then select the coding agents where they should be installed. Run `/setup-northstar` once in each product repository.

Requirements: Python 3.11 or newer. GitHub synchronization uses an authenticated `gh` session; GitLab synchronization uses an authenticated `glab` session. Northstar never stores credentials.

## Talk to Northstar

Users express intent in ordinary language. They are not expected to run Northstar's internal engine.

```text
Set up Northstar for this project and show me the GitHub and GitLab accounts you found.

Add a P1 roadmap story for workspace invitations. As a workspace admin, I want to invite teammates and choose their roles, so that I can onboard my team without support.

Let Maya pick up RM-024 on feat/rm-024-invitations.

Hand RM-024 from Maya to Iker because Maya moved to incident response.

Check whether RM-024 has drifted between the roadmap, GitHub, and GitLab.

RM-024 is finished. The implementation is in PR #142 and Graphify was updated at abc1234.
```

Northstar interprets the request, validates the roadmap, runs a deterministic preview internally, explains the proposed changes, and asks for confirmation when the operation affects ownership, external trackers, imports, or closeout.

## What it enforces

- Compact Markdown roadmap with permanent `RM-###` identifiers.
- Mandatory linked user-story briefs and checkbox acceptance criteria.
- Separate work status and synchronization health.
- Exclusive ownership, required target branches, and audited handoffs.
- GitHub, GitLab, or dual-platform execution records.
- Explicit import and reconciliation of externally-created work.
- Wayfinder authorization before implementation.
- Mandatory Graphify verification and roadmap/tracker updates before `Done`.

## Technically hybrid, experientially a skill

Northstar includes a small deterministic engine so important mutations do not depend on the model rewriting Markdown or remote records from memory. The agent—not the user—operates that engine. Direct engine access exists for development, CI, and troubleshooting.

```text
User intent → Northstar skill → preview and confirmation → internal engine
                                                    ↓
                         ROADMAP.md + GitHub/GitLab + audit journal
                                                    ↓
                                  Wayfinder execution → Graphify → closeout
```

Start with the [`ROADMAP.md` sample](examples/sample-project/ROADMAP.md), then follow the user-facing [`complete workflow`](examples/COMPLETE_WORKFLOW.md). Internal engine recipes are documented separately in [`skills/northstar/EXAMPLES.md`](skills/northstar/EXAMPLES.md).

## Development

```sh
python3 -m unittest discover -s skills/northstar/tests -v
python3 skills/northstar/scripts/northstar.py --help
```

The engine uses only the Python standard library. Remote adapter tests do not make network calls; live synchronization always uses the user-selected authenticated CLI sessions.
