# Northstar

Northstar is a repository-owned product-roadmap skill for teams that want a compact shared portfolio, clean pickup and handoff, dual GitHub/GitLab visibility, and an auditable trail without adopting another planning database.

It intentionally does less than an implementation planner. Northstar owns **what is in the roadmap, why it matters, its priority, lifecycle, and initiative owner**. Wayfinder can optionally explore one large, foggy item. GitHub/GitLab and the repository hold execution detail.

## Install

```sh
npx skills@latest add Navteca/northstar
```

Select `northstar` and `setup-northstar`, then ask the assistant to set up Northstar in a product repository. Users are not expected to learn or run Northstar's internal engine.

Requirements: Python 3.11 or newer. Remote synchronization uses user-approved authenticated `gh` and/or `glab` sessions; Northstar never stores credentials.

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

One `Home` tracker is authoritative for execution context even when both service links exist. The target branch is required for actively owned work. `Plan` is generic and optional; a Wayfinder map belongs there only when discovery is genuinely needed. Expected completion dates remain optional in the linked brief.

## Companions

- **Wayfinder:** recommended for a single large/foggy item. It creates exactly one map on `Home`, writes the link/context back, and returns the item to Northstar when planning clears.
- **Graphify:** recommended for durable architecture context, not required for every project. Closeout always needs durable evidence, which may instead be repository docs, decisions, commits, PRs/MRs, and tracker links.

This makes Northstar a hybrid internally but a skill experientially: the deterministic engine protects concurrent edits and synchronization; the assistant operates it.

See the [sample roadmap](examples/sample-project/ROADMAP.md), [complete workflow](examples/COMPLETE_WORKFLOW.md), and [fork maintenance guide](docs/FORK_MAINTENANCE.md).

## Development

```sh
python3 -m unittest discover -s skills/northstar/tests -v
python3 skills/northstar/scripts/northstar.py --help
```

The engine uses only the Python standard library. Tests never contact live trackers.
