# Complete Northstar workflow

This example shows the user experience. The user speaks naturally; the assistant operates Northstar's engine and tracker tools internally.

## 1. Set up one portfolio and two tracker views

The user says:

> Set up Northstar here. Detect my GitHub and GitLab sessions, show me the accounts, and ask which ones should synchronize.

Northstar detects an existing roadmap before creating one, confirms the authenticated accounts, asks for exact destinations and a default `Home`, then previews `ROADMAP.md`, safe configuration, and the audit log. GitHub and GitLab can both be connected; every item still chooses only one execution authority.

Wayfinder and Graphify are reported as optional companions. Northstar offers installation only with explicit consent.

## 2. Add a mandatory user story

The user says:

> Add a P0 item for workspace invitations. As a workspace admin, I want to invite teammates and choose their roles, so that I can onboard my team without support. It must validate email addresses, allow role selection, prevent double acceptance, and record invitation events.

Northstar allocates `RM-001`, creates the linked brief, and creates/links approved tracker issues. The compact row contains the permanent ID, priority, status, owner, one home tracker, both service links, optional plan, and sync health.

## 3. Pick up clear work directly

The user says:

> Let Maya pick up RM-001 on `feat/rm-001-invitations`.

Northstar confirms that the item is `Ready` and unowned and that its target branch is supplied, then previews the exclusive ownership change and both tracker assignments. Once the roadmap update reaches the shared default branch, Maya owns the item and teammates can see that on both services. No Wayfinder map is created because the work is already clear.

## 4. Use Wayfinder only for foggy work

For another item, the user says:

> RM-002 is too ambiguous. Let Iker pick it up on `feat/rm-002-usage-dashboard` for planning and use Wayfinder.

Northstar passes exactly that row and its brief to Wayfinder. Wayfinder creates one map on the row's `Home` tracker, even if both GitHub and GitLab links exist. Northstar writes the map URL to `Plan`, locks the initiative to Iker, marks it `Planning`, and synchronizes the lifecycle note.

Wayfinder resolves decision tickets. When the fog clears, it writes its durable context pointer into the item brief, sets the roadmap item back to `Ready`, and hands off toward specification. It does not implement the feature or mark it `Done`.

## 5. Hand off with an audit trail

The user says:

> Hand RM-001 from Maya to Iker because Maya moved to incident response.

Northstar records the previous owner, new owner, actor, reason, timestamp, and plan context in the item history and global audit. It updates assignments and posts the handoff to both linked trackers. If the current owner is unavailable, a maintainer can request an explicitly audited override.

## 6. Finish and preserve context

The user says:

> RM-001 is finished. Verify every acceptance criterion, record GitHub PR #160 and GitLab MR !102, update Graphify if it is useful, and close it everywhere.

Northstar requires checked criteria, delivery evidence, and durable context for the next teammate. With Graphify installed, that context might be `Graphify: updated invitation flow at abc123`. Without it, `Repository: docs/decisions/invitations.md; GitHub PR #160` is valid. Northstar updates the roadmap after the work, closes linked tracker records, and records each synchronization result independently from `Done`.

## 7. Import work created outside Northstar

The user says:

> Import GitHub issue https://github.com/acme/product/issues/151 as a P1 candidate and mirror it to GitLab.

Northstar links the original instead of duplicating it, records its origin, creates only the approved missing mirror, and comments on the source that it was created outside Northstar and imported to preserve `ROADMAP.md` as the source of truth.

## 8. Reconcile drift

The user says:

> Check RM-001 for roadmap, GitHub, and GitLab drift.

Northstar reports differences and asks whether to restore canonical roadmap state, import a chosen remote change through the normal lifecycle gates, or leave it marked `Drift`. It never silently chooses a winner.
