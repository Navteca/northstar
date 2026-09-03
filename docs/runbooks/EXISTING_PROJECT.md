# Runbook: Northstar in an existing project

For a repository that already has code, open GitHub issues, and possibly a hand-written `ROADMAP.md` or `TODO.md`. Works with Claude Code and Codex.

Time: about 30 minutes plus the import pass. Prerequisites: Git, Python 3.11+, Node (for `npx`), and `gh` logged in with write access to the repository.

## 1. Decide what the roadmap is for

Northstar tracks product-level items, not every bug. Before importing, agree on:

- which open issues are roadmap items (typically epics, features, larger stories);
- who the teammates are and their GitHub logins;
- whether an existing `ROADMAP.md` should be replaced or kept alongside under another name.

If a `ROADMAP.md` exists and is not a Northstar table, rename it first (`git mv ROADMAP.md docs/ROADMAP_LEGACY.md`); `init` refuses to overwrite.

## 2. Install the skills

Claude Code:

```bash
npx skills@latest add Navteca/northstar --skill northstar --skill setup-northstar -a claude-code -y
```

Codex:

```bash
npx skills@latest add Navteca/northstar --skill northstar --skill setup-northstar -a codex -y
```

Use both `-a` flags if the team mixes agents. The canonical copy is `.agents/skills/`; Claude Code reads it through symlinks in `.claude/skills/`. Commit both directories.

## 3. Run setup on a branch

```bash
git checkout -b chore/northstar
```

Then in the agent (`/setup-northstar` in Claude Code, `$setup-northstar` or plain language in Codex):

> Set up Northstar in this repository, linked to acme/product. Teammates: Maya is maya-gh, Iker is iker-gh. Install the policy workflow only.

Setup previews every write. Confirm the repository, identities, vendored engine in `roadmap/bin/`, and `.github/workflows/northstar-policy.yml`. Leave companions off unless the team already uses them.

Add an owner for the roadmap paths when the repository has a `CODEOWNERS` file (setup offers a snippet; replace the placeholder team).

## 4. Import existing issues

For each issue that belongs on the roadmap:

> Import https://github.com/acme/product/issues/151 as a P1 Ready item. As an account owner, I want to see weekly usage, so that I can help inactive teams. Criteria: weekly active users for twelve weeks; filter by team; empty states explained.

The agent links the original issue instead of creating a new one, records `Origin: github` in the brief, and posts one comment on the issue saying it is now governed by `ROADMAP.md`. Issues need a real user story and criteria; if the source issue lacks them, write them now, this is the point of the exercise.

Issues already being worked on: import them as `Ready`, then have the current assignee pick them up so the owner lock and branch are recorded:

> Let Maya pick up RM-003 on feat/usage-dashboard.

Batch tip: paste a list of issue URLs with priorities and let the agent walk through them; it still previews each `add`.

## 5. Open the pull request

```bash
git add ROADMAP.md roadmap .github CODEOWNERS .gitignore .claude .agents 2>/dev/null
git commit -m "chore: adopt Northstar roadmap"
git push -u origin chore/northstar
gh pr create --fill
```

The policy workflow runs on this PR because it touches `ROADMAP.md`. Merge when green. From now on the default branch is the lock: a pickup counts once its row change lands there.

## 6. Switch the team over

- Announce that new roadmap-level work is created through Northstar, and that the assistant refuses to close an item without checked criteria, evidence, and context.
- Point people at the "Talk to Northstar" examples in the README.
- Keep filing bugs and small tasks as plain issues; only roadmap items get an `RM-###`.

## 7. Optional operations, later

Ask for them individually once the basics stick: `claim` for serialized server-side pickup, `reconcile` for daily drift reports, `maintenance` for archival and views, `notify` for webhooks. If `main` is protected, the pushing workflows need a `NORTHSTAR_PUSH_TOKEN` secret. Details in the `northstar` skill's OPERATIONS.md.

## Troubleshooting

- `init` refused: an old `ROADMAP.md` exists. Rename it, rerun.
- Import rejected: `--origin-url` must be a `github.com/<owner>/<repo>/issues/<n>` URL.
- Validation fails on an imported item: the user story must read "As a/an/the …, I want …, so that …" and have at least one `- [ ]` criterion.
- `Sync: Error`: the row changed but the issue call failed. "Retry failed syncs" or `python3 roadmap/bin/northstar_admin.py retry`.
- Two people picked up the same item on different branches: the second PR conflicts on that row. Only the merged owner proceeds; the other re-reads the row and picks something else or asks for a handoff.
