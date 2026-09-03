# Northstar design and value review

## Thesis

Northstar is worthwhile as the coordination layer between product intent and execution evidence. It answers five questions reliably:

1. What work matters next?
2. Why does it matter?
3. Who owns it, on which branch?
4. Which plan or context should the next teammate or assistant read?
5. What changed, who handed it off, and is the GitHub issue in step?

GitHub Issues, specifications, execution methods, and knowledge graphs answer adjacent questions. Northstar links them and does not replace them.

## Responsibility model

This is the single home for the boundary table; other documents link here.

| Layer | Owns | Does not own |
|---|---|---|
| Northstar | Portfolio order, story, priority, lifecycle, owner lock, branch, issue link, handoff and closeout audit | Implementation planning, code, review, capacity planning, a UI |
| GitHub | Issues, assignees, execution discussion, PRs, service-visible history | Roadmap order or lifecycle truth |
| Wayfinder | Discovery for one large or uncertain item | Portfolio priority, delivery closeout |
| Spec Kit | Formal specification and acceptance boundary | Ownership, reconciliation |
| cc-rpi | Research → Plan → Implement → Validate execution | Roadmap lifecycle, lock, audit |
| Graphify | Optional persistent codebase context | Work lifecycle |

`Plan kind` (how an item becomes clear) and `Execution method` (how approved work is executed) are separate axes so optional companions never become competing lifecycles.

## Why GitHub only

An earlier design mirrored every item to GitHub and GitLab at once. That required a `Home` authority column, two link columns, a saga with an outbox for partial failures, two claim workflows, and two adapters, and it was the source of most of the engine's complexity. The current design has one tracker per repository and one `Issue` column. Remote writes are idempotent, so a failed sync is simply replayed. [docs/research/DUAL_TRACKER_SUPPORT.md](research/DUAL_TRACKER_SUPPORT.md) records how GitLab can be added later without reintroducing that complexity.

## Risks and mitigations

| Risk | Mitigation | Remaining |
|---|---|---|
| Two teammates claim the same item from different clones | Default-branch merge is the lock; the optional claim workflow serializes per item and resolves the claimant from the GitHub actor | Protected branches need a scoped push token |
| Roadmap changes but the issue update fails | Row marked `Error`; journal keeps the event; `retry` replays it idempotently | None structural |
| Hand edits bypass lifecycle gates | Engine enforces the transition table; `policy` re-checks it per pull request | Requires the policy workflow to be installed |
| Markdown table becomes unwieldy | Active-item limit, archival, generated views | Large portfolios need a dedicated planning system |
| Audit trail is rewritten | SHA-256-linked chain detects edits; Git history and protected branches are the trust anchor | Signed commits remain an organization choice |

## Verdict

Northstar fits small and medium engineering teams that want repository-owned product context and auditable handoffs across assistants. It is a team protocol: it pays off when the whole repository routes roadmap changes through it. It should not be presented as a replacement for Jira, Linear, or GitHub Projects.
