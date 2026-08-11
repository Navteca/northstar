# Northstar reference

## Repository contract

```text
ROADMAP.md                         # canonical compact portfolio index
roadmap/northstar.toml             # safe tracker and identity mapping
roadmap/audit.md                   # append-only lifecycle and handoff audit
roadmap/items/RM-001.md            # complete story, context, and evidence
roadmap/journal/*.json             # per-operation synchronization results
```

## Compact roadmap

```md
| ID | P | Status | Story | Owner | Branch | Home | GitHub | GitLab | Plan | Sync |
|---|---|---|---|---|---|---|---|---|---|---|
| RM-024 | P1 | Planning | [Team invitations](roadmap/items/RM-024.md) | Maya | feat/rm-024-invitations | github | [#142](https://github.com/acme/app/issues/142) | [#87](https://gitlab.com/acme/app/-/issues/87) | [map](https://github.com/acme/app/issues/155) | Synced |
```

- `Home` is the single execution authority: `github`, `gitlab`, or `local`.
- GitHub and GitLab links may coexist. They are visibility and synchronization endpoints, not competing authorities.
- `Plan` is one canonical issue, brief, Spec Kit specification, or Wayfinder map. Each brief records `Plan kind: Direct`, `Wayfinder`, or `Spec Kit`; non-direct routes require a plan before active pickup.
- `Execution method` is orthogonal to planning: `Native` or `RPI` (cc-rpi). RPI may execute a Direct, Wayfinder, or Spec Kit item; it never replaces Northstar's ownership and audit gates.
- Full story, criteria, dependencies, optional expected completion date, origin, durable context, and delivery evidence live in the brief.

## Lifecycle gates

```text
Candidate → Planned → Ready → In Progress → Done
                         ↘ Planning → Ready
                         ↘ Blocked ↗
          ↘ Deferred / Retired
```

- `Ready`: valid story and criteria plus a usable `Home` endpoint.
- `Planning`: exclusive owner, target branch, `Home`, and one `Plan`; the plan kind identifies whether the route is Wayfinder or Spec Kit.
- `In Progress`: exclusive owner, target branch, and `Home`. A plan is optional.
- `Blocked`: retains ownership and context while work cannot proceed.
- `Done`: all criteria checked, durable context evidence, delivery evidence, roadmap/brief update, and recorded sync result.

## Responsibility boundary

| Concern | Authority |
|---|---|
| Portfolio ordering, story, priority, initiative owner, lifecycle | Northstar |
| Discovery decisions for one large/foggy item | Wayfinder map on `Home` |
| Task assignment, commits, reviews, implementation discussion | Home tracker and repository |
| Optional architecture knowledge graph | Graphify |
| High-level lifecycle/handoff audit | `roadmap/audit.md` |
| Detailed technical audit | Git history, PRs/MRs, tracker history, and linked context |

Wayfinder is conditional. It consumes one roadmap item and writes back one map/context pointer. Northstar never expands the entire portfolio into a Wayfinder map, and Wayfinder never reprioritizes the portfolio or closes delivery.

## Synchronization transaction

1. Validate the current roadmap and brief.
2. Preview the intended local and remote changes.
3. Acquire the local lock and write repository files atomically.
4. Update every linked service through authenticated sessions.
5. Save per-service results under `roadmap/journal/`.
6. Set `Sync` to `Synced`, `Partial`, `Error`, `Drift`, or `Local`; append an audit event.

Partial remote success is not rolled back. Reconciliation resumes from the journal and never silently selects a winner.

## Concurrent pickup

The engine prevents simultaneous mutations in one working tree. Across clones, the shared default branch is the lock authority. A pickup is not authoritative until its roadmap change lands there. Competing edits touch the same row, making the conflict visible. Only the merged owner may proceed; every assistant must re-read the canonical row before starting.

## GitHub and GitLab

Northstar uses authenticated `gh` and `glab` sessions. It creates/links issues, assigns owners, posts lifecycle notes, closes delivery issues, and may add GitHub issues to a configured GitHub Project. GitLab boards remain views over project issues/work items. The roadmap does not depend on either product's proprietary project schema.

## Import rule

External work is never silently added. Northstar links the original record, records provenance, creates only approved missing mirrors, and posts a source note that the issue was created outside Northstar and imported so `ROADMAP.md` remains canonical.
