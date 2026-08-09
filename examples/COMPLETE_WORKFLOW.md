# Complete Northstar workflow

This example takes a story from an empty repository through GitHub and GitLab setup, claim, Wayfinder execution, handoff, Graphify verification, and closeout. Commands preview unless `--apply` is present.

Set a convenient alias for the examples below:

```sh
NORTHSTAR="python3 skills/northstar/scripts/northstar.py"
```

## 1. Install and inspect

```sh
npx skills@latest add Navteca/northstar
$NORTHSTAR doctor
```

Run `/setup-northstar`. Review the detected authenticated `gh` and `glab` accounts, choose the exact repositories/projects and execution views, and approve the generated `roadmap/northstar.toml`. Add identity mappings for every teammate who can claim work.

## 2. Initialize the canonical roadmap

```sh
$NORTHSTAR init
$NORTHSTAR init --apply
$NORTHSTAR validate
```

Commit the initial `ROADMAP.md`, configuration, and audit log through the team’s normal review process.

## 3. Create a complete roadmap item

Preview it:

```sh
$NORTHSTAR add \
  --title "Workspace invitations" \
  --priority P0 \
  --status Ready \
  --story "As a workspace admin, I want to invite teammates and choose their roles, so that I can onboard my team without support." \
  --acceptance "An admin can invite a valid email address" \
  --acceptance "The admin can select a workspace role" \
  --acceptance "An invitation expires and can be accepted only once" \
  --acceptance "Invitation events appear in the audit trail"
```

After approval, repeat it with `--apply`. With GitHub and GitLab enabled, Northstar creates both tracker records, links them in the row, journals the results, and sets `Sync` to `Synced`, `Partial`, or `Error`.

Review `roadmap/items/RM-001.md`, then commit the canonical change.

## 4. Reprioritize or refine before execution

```sh
$NORTHSTAR update RM-001 \
  --priority P1 \
  --actor Product \
  --reason "Security remediation moved ahead of invitation work"
```

Review the preview, repeat with `--apply`, and commit the roadmap/audit change.

## 5. Claim it safely

Create or refresh `roadmap/maps/RM-001.md` with Wayfinder. Then stage the canonical claim locally:

```sh
$NORTHSTAR claim RM-001 \
  --owner Maya \
  --actor Maya \
  --branch feat/rm-001-invitations \
  --wayfinder roadmap/maps/RM-001.md \
  --local-only
```

After approval, repeat with `--apply`. Commit and merge/push the row change to the default branch. The lock is authoritative only when the default branch names Maya as owner.

Publish the canonical claim to both trackers:

```sh
$NORTHSTAR reconcile RM-001
$NORTHSTAR reconcile RM-001 \
  --strategy canonical \
  --actor Maya \
  --reason "Publish merged claim" \
  --apply
```

Wayfinder may now begin implementation on `feat/rm-001-invitations`.

## 6. Perform an audited handoff if needed

The current owner previews and applies:

```sh
$NORTHSTAR handoff RM-001 \
  --actor Maya \
  --to Iker \
  --reason "Maya moved to incident response" \
  --local-only
```

Commit the canonical owner change, then run canonical reconciliation to update both trackers. If Maya is unavailable, a designated maintainer uses `--override`; the reason remains mandatory and appears in the item history and global audit.

## 7. Execute with Wayfinder and Graphify

Wayfinder maintains the linked map as decisions are resolved. During delivery:

1. Check each completed acceptance criterion in `roadmap/items/RM-001.md`.
2. Link the pull request and/or merge request.
3. Update Graphify after code changes.
4. Record either `Updated: <map and revision>` or `Verified-no-change: <reason and evidence>` in the close command.

Northstar rejects closeout while any acceptance criterion remains unchecked.

## 8. Close canonically, then publish

Preview the close:

```sh
$NORTHSTAR close RM-001 \
  --actor Iker \
  --graphify "Updated: invitation flow at commit abc1234" \
  --evidence "GitHub PR #160 and GitLab MR !102" \
  --local-only
```

After approval, add `--apply`, commit the `Done` roadmap state, and merge/push it. Then publish that canonical state:

```sh
$NORTHSTAR reconcile RM-001 \
  --strategy canonical \
  --actor Iker \
  --reason "Publish verified closeout" \
  --apply

$NORTHSTAR validate
```

The final state has checked acceptance criteria, delivery evidence, Graphify evidence, a complete audit trail, closed GitHub/GitLab records, and `Sync: Synced`.

## 9. Handle externally-created work

If a GitHub issue was created outside Northstar, preview an explicit import:

```sh
$NORTHSTAR add \
  --title "Workspace usage dashboard" \
  --priority P1 \
  --status Candidate \
  --story "As an account owner, I want to review workspace usage, so that I can improve adoption." \
  --acceptance "Weekly active usage is visible" \
  --origin github \
  --origin-url https://github.com/acme/product/issues/151
```

After approval, repeat with `--apply`. Northstar links the existing GitHub issue, creates only any configured missing mirror, records its origin, and comments that the work is now governed by canonical `ROADMAP.md`.
