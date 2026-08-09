# Complete Northstar workflow

This is the user experience from an empty product repository through setup, dual-platform tracking, claim, Wayfinder execution, handoff, Graphify verification, and closeout.

The user speaks naturally. Northstar operates its bundled engine internally, presents human-readable previews, and asks for confirmation before material changes. The user does not need to know engine commands or flags.

## 1. Install Northstar

Install both bundled skills:

```sh
npx skills@latest add Navteca/northstar
```

Choose `northstar` and `setup-northstar` for the desired coding agent.

## 2. Set up the product repository

The user says:

> Set up Northstar for this project. Detect my GitHub and GitLab sessions, but ask before connecting anything.

Northstar then:

1. Checks whether a roadmap already exists.
2. Detects authenticated `gh` and `glab` sessions without reading or storing tokens.
3. Shows the accounts, repositories/projects, GitHub Projects, and GitLab boards it can access.
4. Asks which destinations should synchronize.
5. Collects the GitHub and GitLab usernames for teammates who may claim work.
6. Previews the new `ROADMAP.md`, safe configuration, and audit log.
7. Creates them only after confirmation.

The user reviews and commits this initial configuration through the team's usual process.

## 3. Add a roadmap story

The user says:

> Add a P0 story for workspace invitations and make it Ready. As a workspace admin, I want to invite teammates and choose their roles, so that I can onboard my team without support.
>
> It must let an admin invite a valid email address, choose a role, prevent an invitation from being accepted twice, and record invitation events in the audit trail.

Northstar validates the user-story structure and acceptance criteria, allocates the next permanent ID, and shows a preview such as:

```text
Create RM-001 — Workspace invitations
Priority: P0
Status: Ready
GitHub: create issue and add it to Product roadmap
GitLab: create work item in acme/product
Canonical files: ROADMAP.md + roadmap/items/RM-001.md + audit entry
```

After confirmation, Northstar performs the operation and reports whether both services synchronized. The roadmap contains only the compact row; the complete story remains in its linked brief.

## 4. Refine or reprioritize it

The user says:

> Move RM-001 to P1 because security remediation must go first.

Northstar shows the old and new priority, the reason, and the GitHub/GitLab records that will be notified. After confirmation it updates the canonical roadmap, item history, audit log, and trackers.

## 5. Claim the work

The user says:

> Let Maya pick up RM-001 on `feat/rm-001-invitations`.

Northstar verifies that:

- RM-001 is `Ready` and currently unlocked.
- Its user story and acceptance criteria are complete.
- Maya has mapped GitHub and GitLab identities.
- A target branch was provided.

Northstar invokes Wayfinder to create or refresh `roadmap/maps/RM-001.md`, then previews the exclusive lock and tracker assignments. After confirmation it stages the canonical claim. The claim becomes authoritative when the roadmap change reaches the default branch; Wayfinder re-reads that branch before starting implementation.

Northstar then publishes the merged claim to every linked tracker. Teammates see the owner, branch, status, and claim comment in GitHub and GitLab.

## 6. Execute with Wayfinder

The user says:

> Use Wayfinder to work through RM-001.

Wayfinder follows the linked map and target branch. It keeps implementation decisions and progress attached to RM-001 while Northstar continues to own roadmap state and synchronization policy.

Another teammate may collaborate, but cannot replace Maya as owner without a handoff.

## 7. Hand off ownership if needed

Maya says:

> Hand RM-001 to Iker because I am moving to incident response. Keep the existing branch.

Northstar previews the transfer and, after confirmation:

- Replaces Maya with Iker as the exclusive owner.
- Keeps `feat/rm-001-invitations` and the Wayfinder map.
- Updates both trackers.
- Appends the reason, actor, timestamp, previous owner, new owner, and branch to the item history and global audit.

If Maya is unavailable, a designated product owner or maintainer may request an override. Northstar still requires a reason and labels it as an override in the audit trail.

## 8. Complete acceptance and update Graphify

When implementation is ready, the user says:

> Prepare RM-001 for closeout. The implementation is in GitHub PR #160 and GitLab MR !102. Verify every acceptance criterion and update Graphify.

Wayfinder verifies the delivered behavior and checks the completed acceptance criteria. It updates Graphify and records either:

- `Updated: <map and revision>`, or
- `Verified-no-change: <reason and evidence>` for work that produces no graph change.

Northstar refuses closeout if an acceptance criterion remains unchecked or Graphify evidence is missing.

## 9. Close the item

The user says:

> Close RM-001 now that its acceptance criteria and Graphify update are verified.

Northstar previews the complete closeout:

```text
RM-001: In Progress → Done
Acceptance criteria: 4/4 verified
Graphify: invitation flow updated at abc1234
Delivery: GitHub PR #160; GitLab MR !102
External records: close GitHub #142 and GitLab #87
Audit and roadmap: update required
```

After confirmation, Northstar updates the canonical roadmap and evidence, publishes the closeout to both trackers, and records each result in the synchronization journal. The final row keeps `Status: Done` separate from `Sync: Synced`.

## 10. Detect remote drift

Later, the user says:

> Check whether RM-001 has drifted between the roadmap, GitHub, and GitLab.

Northstar compares canonical fields with both linked records and explains each difference. It asks whether to:

- restore the canonical roadmap state remotely,
- import the selected remote change through its normal gated workflow, or
- leave the difference and mark the row `Drift`.

Northstar never silently chooses a winner.

## 11. Import externally-created work

The user says:

> Import GitHub issue `https://github.com/acme/product/issues/151` as a P1 roadmap candidate. The story is: As an account owner, I want to review workspace usage, so that I can improve adoption. Weekly active usage must be visible.

Northstar previews the import. After confirmation it:

- Allocates a permanent roadmap ID.
- Links the existing GitHub issue rather than duplicating it.
- Creates a GitLab mirror if that destination is configured and approved.
- Records the origin URL and import decision.
- Comments on the source issue that canonical planning now lives in `ROADMAP.md`.

The imported item follows the same refinement, claim, Wayfinder, Graphify, handoff, and closeout rules as native work.
