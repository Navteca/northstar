# Northstar

Northstar is the shared product-roadmap and handoff layer for an AI-assisted team.

Northstar is a repository-owned product-roadmap skill for teams that want a compact shared portfolio, clean pickup and handoff, dual GitHub/GitLab visibility, and an auditable trail without adopting another planning database.

It intentionally does less than an implementation planner. Northstar owns **what is in the roadmap, why it matters, its priority, lifecycle, and initiative owner**. GitHub and GitLab provide the visible execution record; the repository keeps the durable brief and audit trail.

The assistant is the interface: teammates ask for a setup, pickup, handoff, reconciliation, or closeout in natural language. The deterministic engine validates and updates the compact Markdown table, item briefs, tracker links, and audit records behind the scenes.

## Why Northstar exists

Teams often have the ingredients for good project context—issues, pull requests, specifications, architecture notes, and chat—but no small, shared index that tells the next teammate what matters and who owns it. Northstar makes `ROADMAP.md` the source of truth without introducing a new planning database.

Three decisions shape the design:

- **Markdown first:** the roadmap is reviewable in Git, easy to merge, and useful even when no tracker is connected.
- **One home, two mirrors:** an item can link to GitHub and GitLab simultaneously, while one `Home` remains authoritative for execution.
- **Planning is routed per item:** clear work can start Direct; uncertain work can use Wayfinder; feature work that needs formal requirements can use Spec Kit. Northstar coordinates these routes but does not pretend they are interchangeable.

## Install

```sh
npx skills@latest add Navteca/northstar
```

Select `northstar` and `setup-northstar`, then ask the assistant to set up Northstar in a product repository. Users are not expected to learn or run Northstar's internal engine.

Choose capabilities during setup, not blindly during npm installation. See [skills/setup-northstar/PROFILES.md](skills/setup-northstar/PROFILES.md) for Core, Wayfinder, Spec Kit, and Full profiles. Because the standard Skills installer cannot resolve skills from a separate repository, companion installs are explicit and consent-based. Tracker destinations, authenticated accounts, and sync policy are selected later per repository.

Requirements: Python 3.11 or newer. Remote synchronization uses user-approved authenticated `gh` and/or `glab` sessions; Northstar never stores credentials.

## Setup flow

After installation, ask the assistant to:

1. Detect or initialize `ROADMAP.md` and validate existing item briefs.
2. Show authenticated GitHub and GitLab sessions without exposing tokens.
3. Ask which repositories/projects to synchronize, whether to use one or both services, and which service is the default `Home`.
4. Detect companion skills/tools and ask which capability profile to enable.
5. Write only safe repository configuration to `roadmap/northstar.toml`.

Installation does not create GitHub/GitLab issues, select accounts, or install optional tools silently. Those are repository decisions that may differ from project to project. Re-running setup shows the current mapping before proposing changes.

See the [profile matrix and detection commands](skills/setup-northstar/PROFILES.md) for the exact choices.

## Talk to Northstar

```text
Set up Northstar here. Show me the GitHub and GitLab sessions you detect and ask which ones to connect.

Add a P1 roadmap story for workspace invitations. As a workspace admin, I want to invite teammates and choose their roles, so that I can onboard my team without support.

Let Maya pick up RM-024.

RM-025 is still too ambiguous. Use Wayfinder on its GitHub home and link the map back to the roadmap.

Hand RM-024 from Maya to Iker because Maya moved to incident response.

Check whether RM-024 has drifted across the roadmap, GitHub, and GitLab.

RM-024 is finished. Verify its criteria, record the PR and durable project context, then update the roadmap and trackers.
```

Northstar interprets the request, validates the repository contract, previews material changes, and coordinates its internal engine plus tracker tools.

## Compact contract

```md
| ID | P | Status | Story | Owner | Branch | Home | GitHub | GitLab | Plan | Sync |
|---|---|---|---|---|---|---|---|---|---|---|
| RM-024 | P1 | Planning | [Team invitations](roadmap/items/RM-024.md) | Maya | feat/rm-024-invitations | github | [#142](https://github.com/acme/app/issues/142) | [#87](https://gitlab.com/acme/app/-/issues/87) | [map](https://github.com/acme/app/issues/155) | Synced |
```

One `Home` tracker is authoritative for execution context even when both service links exist. The target branch is required for actively owned work. Every brief records `Plan kind: Direct`, `Wayfinder`, or `Spec Kit`; non-direct routes must link an approved plan before active pickup. Expected completion dates remain optional in the linked brief.

## Companions

- **[Wayfinder](https://github.com/Navteca/skills/blob/navteca/docs/engineering/wayfinder.md):** recommended for a single large or foggy item. It creates one canonical map, writes the link/context back, and returns the item to Northstar when planning clears.
- **[Spec Kit](https://github.com/github/spec-kit):** recommended when a feature needs a formal specification, acceptance boundary, or multi-step design before implementation. Northstar stores the approved spec link and still owns pickup, handoff, closeout, and roadmap updates.
- **[Graphify](https://github.com/safishamsi/graphify):** recommended for durable architecture and codebase context. It is not required; repository decisions, commits, PRs/MRs, and tracker links are valid closeout evidence on their own.

The Wayfinder companion stack is maintained in the [Navteca downstream skills fork](https://github.com/Navteca/skills), which preserves a clean upstream mirror of [Matt Pocock's skills](https://github.com/mattpocock/skills) on its `main` branch. Northstar-specific integration stays downstream so the team can update upstream deliberately and contribute generally useful improvements back.

Northstar also relies on the [Skills CLI](https://github.com/vercel-labs/skills) for installation. The CLI installs skills; it does not infer Northstar's tracker configuration or resolve cross-repository companion dependencies, which is why profiles and setup are explicit.

The optional Wayfinder profile pulls a focused set of companion workflows from Navteca's fork: [Wayfinder](https://github.com/Navteca/skills/blob/navteca/docs/engineering/wayfinder.md), [Grilling](https://github.com/Navteca/skills/blob/navteca/docs/productivity/grilling.md), [Domain Modeling](https://github.com/Navteca/skills/blob/navteca/docs/engineering/domain-modeling.md), [Research](https://github.com/Navteca/skills/blob/navteca/docs/engineering/research.md), [Prototype](https://github.com/Navteca/skills/blob/navteca/docs/engineering/prototype.md), [To Spec](https://github.com/Navteca/skills/blob/navteca/docs/engineering/to-spec.md), [To Tickets](https://github.com/Navteca/skills/blob/navteca/docs/engineering/to-tickets.md), and [Implement](https://github.com/Navteca/skills/blob/navteca/docs/engineering/implement.md). They remain separate so teams can install only what they need.

This makes Northstar a hybrid internally but a skill experientially: the deterministic engine protects concurrent edits and synchronization; the assistant operates it.

See the [sample roadmap](examples/sample-project/ROADMAP.md), [complete workflow](examples/COMPLETE_WORKFLOW.md), and [fork maintenance guide](docs/FORK_MAINTENANCE.md).

## Development

```sh
python3 -m unittest discover -s skills/northstar/tests -v
python3 skills/northstar/scripts/northstar.py --help
```

The engine uses only the Python standard library. Tests never contact live trackers.
