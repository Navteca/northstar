# Runbook: Northstar in a new project

For a repository that has no roadmap yet. Works with Claude Code and Codex; the only difference is how the skill is installed and how you address it.

Time: about 15 minutes. Prerequisites: Git, Python 3.11+, Node (for `npx`), and `gh` logged in to an account that can write to the target GitHub repository.

## 1. Create the repository

```bash
mkdir my-product && cd my-product && git init -b main
gh repo create acme/my-product --private --source . --push
```

Skip if the repository already exists on GitHub but has no roadmap; this runbook still applies.

## 2. Install the skills

Claude Code:

```bash
npx skills@latest add Navteca/northstar --skill northstar --skill setup-northstar -a claude-code -y
```

Codex:

```bash
npx skills@latest add Navteca/northstar --skill northstar --skill setup-northstar -a codex -y
```

Both at once: repeat `-a` (`-a claude-code -a codex`). Skills land in `.claude/skills/` for Claude Code and `.agents/skills/` for Codex. Commit these directories so teammates and CI agents get the same instructions. Add `-g` instead to install for your user only.

Check:

```bash
npx skills ls
```

## 3. Run setup

Start the agent in the repository root and say:

> Set up Northstar here and link it to acme/my-product on GitHub. Map me as <Name> with GitHub login <login>. Install the policy workflow.

In Claude Code you can also type `/setup-northstar`. In Codex mention `$setup-northstar` or just ask in plain language.

The agent will, in this order, and asking before each write:

1. Run `doctor`, find no roadmap, and preview `init`.
2. Show the `gh` account and confirm the repository.
3. Write `ROADMAP.md`, `roadmap/northstar.toml`, and `roadmap/audit.md`.
4. Add the `[identities.<Name>]` mapping.
5. Vendor the engine to `roadmap/bin/` and copy `northstar-policy.yml` to `.github/workflows/`.
6. Offer companions (Wayfinder, Spec Kit, Graphify, cc-rpi). Decline unless you already use them.

Expected result:

```text
ROADMAP.md
roadmap/northstar.toml
roadmap/audit.md
roadmap/bin/northstar.py
roadmap/bin/northstar_admin.py
.github/workflows/northstar-policy.yml
```

Commit it:

```bash
git add ROADMAP.md roadmap .github .gitignore .claude .agents 2>/dev/null; git commit -m "chore: add Northstar roadmap"
git push
```

## 4. Add the first stories

> Add a P1 story: as a workspace admin, I want to invite teammates and choose their roles, so that I can onboard my team without support. Criteria: an admin can invite an email address; the admin can pick a role; an invitation can be accepted once.

The agent previews, then creates `RM-001`, its brief under `roadmap/items/`, and, with your approval, the GitHub issue `[RM-001] …`. Repeat for the next few items. Set `--status Ready` items you want people to be able to pick up; leave the rest `Planned`.

## 5. Daily use

| You say | What happens |
|---|---|
| "What should I work on next?" | The agent reads `ROADMAP.md` and proposes the highest-priority `Ready` item. |
| "Let me pick up RM-001 on feat/rm-001-invitations" | Row moves to `In Progress`, you become owner, the issue is assigned to you. |
| "RM-001 is blocked on vendor keys" | Row moves to `Blocked`; the issue gets a comment. |
| "Hand RM-001 to Iker because I am on incident duty" | Ownership transfers with a reason; audit and issue updated. |
| "RM-001 is done, PR #12" | Criteria must be checked; brief, row, audit, and issue are closed together. |
| "Check RM-001 for drift" | Compares the row with the issue and asks how to resolve differences. |

Every change goes through a branch and pull request like any other file. The policy workflow rejects illegal lifecycle moves and stale generated views.

## 6. Optional: team operations

Ask setup for them later, one at a time:

> Install the Northstar claim workflow.

- **claim**: teammates dispatch the "Northstar claim" workflow from the Actions tab with the item ID and branch; the claimant is whoever dispatched it.
- **reconcile**: daily drift report.
- **maintenance**: weekly archive of old `Done` rows and regenerated views/dashboard.
- **notify**: lifecycle events to a Slack/Teams/generic webhook (`NORTHSTAR_WEBHOOK_URL` secret).

If `main` is protected, add a `NORTHSTAR_PUSH_TOKEN` secret for the workflows that push.

## Troubleshooting

- `Sync: Error` on a row: the roadmap changed but GitHub did not. Say "retry failed syncs" or run `python3 roadmap/bin/northstar_admin.py retry`.
- "No GitHub identity mapping for owner": add `[identities.<Name>] github = "<login>"` to `roadmap/northstar.toml`.
- Policy check fails on a PR: the PR moved an item illegally or edited generated views by hand. Ask the agent to redo the change through Northstar.
- The agent does not recognize Northstar: confirm the skill directory is present with `npx skills ls`, and restart the agent session.
