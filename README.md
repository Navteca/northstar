# Northstar

Northstar keeps a product roadmap inside the repository as a small Markdown table, and makes AI assistants and teammates follow the same rules when they pick up, hand off, and close work. GitHub Issues stay the place where execution happens; `ROADMAP.md` stays the place that says what matters, why, who owns it, and whether it is done.

It is deliberately small. Northstar owns the roadmap row, the item brief, ownership, handoff, and closeout evidence. It does not plan implementations, replace GitHub Issues or Projects, or add a UI.

## Why

Agent-assisted teams lose context at every handoff. Issues, PRs, chat, and specs hold the pieces, but nothing small and reviewable says "this is the next thing, this is who has it, and here is what done means." Northstar is that index, with gates a deterministic engine enforces so an assistant cannot skip them:

- every item has a permanent `RM-###` ID, a user story, and checkbox acceptance criteria;
- active work has exactly one owner and a target branch;
- lifecycle moves follow one transition table, in the engine and in CI;
- closing requires checked criteria, delivery evidence, and durable context for the next person;
- every ownership change is audited, and the linked GitHub issue is kept in step.

Northstar is a team protocol. It pays off when the whole repository routes roadmap changes through it and work regularly moves between people or agent sessions. For one person, or for portfolio planning with capacity and forecasting needs, use something else.

## Install

```sh
npx skills@latest add Navteca/northstar --skill northstar --skill setup-northstar
```

Then ask the assistant to set up Northstar in a product repository. It detects or creates `ROADMAP.md`, shows the authenticated `gh` account, asks which repository to link, writes safe configuration to `roadmap/northstar.toml`, and vendors the engine into `roadmap/bin/` so CI can run it. Nothing external is created or installed without approval.

Requirements: Python 3.11 or newer and an authenticated `gh` session. Northstar never stores credentials.

## Talk to Northstar

```text
Set up Northstar here and link it to acme/product on GitHub.

Add a P1 story for workspace invitations. As a workspace admin, I want to invite teammates and choose their roles, so that I can onboard my team without support.

Let Maya pick up RM-024 on feat/rm-024-invitations.

Hand RM-024 from Maya to Iker because Maya moved to incident response.

RM-024 is finished. Verify its criteria, record PR #160, then update the roadmap and the issue.
```

The assistant previews each change in plain language, asks before touching ownership or GitHub, then applies it through the engine.

## The contract

```md
| ID | P | Status | Story | Owner | Branch | Issue | Plan | Sync |
|---|---|---|---|---|---|---|---|---|
| RM-024 | P1 | In Progress | [Team invitations](roadmap/items/RM-024.md) | Maya | feat/rm-024-invitations | [#142](https://github.com/acme/app/issues/142) | — | Synced |
```

`Plan` is optional and points to one planning artifact when an item needed discovery or a spec first. `Sync` says whether the linked issue reflects the row. Everything else about the item lives in its brief under `roadmap/items/`. See [REFERENCE.md](skills/northstar/REFERENCE.md) for the lifecycle and file layout, and the [sample project](examples/sample-project/ROADMAP.md) for a valid roadmap.

## Optional operations

Setup can install GitHub workflow templates, each with approval:

- **policy**: validates the contract and lifecycle transitions on roadmap pull requests;
- **claim**: serialized server-side pickup, claimant resolved from the GitHub actor;
- **reconcile**: scheduled drift report between the roadmap and linked issues;
- **maintenance**: archives old completed rows and regenerates views and a read-only dashboard;
- **notify**: delivers lifecycle events to a webhook.

Details in [OPERATIONS.md](skills/northstar/OPERATIONS.md). GitLab is not supported; the design for adding it later is in [docs/research/DUAL_TRACKER_SUPPORT.md](docs/research/DUAL_TRACKER_SUPPORT.md).

## Companions

Northstar is complete on its own: `Plan kind: Direct` and any URL in `Plan`. Teams that already use these tools can record them per item; setup detects them and offers each one explicitly. See [PROFILES.md](skills/setup-northstar/PROFILES.md).

- [Wayfinder](https://github.com/Navteca/skills/blob/navteca/docs/engineering/wayfinder.md) for a single large or foggy item, from the [Navteca skills distribution](https://github.com/Navteca/skills) (see [FORK_MAINTENANCE.md](docs/FORK_MAINTENANCE.md)).
- [Spec Kit](https://github.com/github/spec-kit) when a feature needs a formal specification first.
- [cc-rpi](https://github.com/juan294/cc-rpi) as an execution method, recorded separately from the planning route.
- [Graphify](https://github.com/Graphify-Labs/graphify) for durable codebase context at closeout.

Design rationale and limitations: [docs/DESIGN_AND_VALUE.md](docs/DESIGN_AND_VALUE.md). Contributing: [CONTRIBUTING.md](CONTRIBUTING.md).

## Development

```sh
python3 -m unittest discover -s skills/northstar/tests -v
python3 skills/northstar/scripts/northstar.py --root examples/sample-project validate
python3 skills/northstar/scripts/northstar_admin.py --root examples/sample-project policy
```

Standard library only. Tests never contact GitHub.
