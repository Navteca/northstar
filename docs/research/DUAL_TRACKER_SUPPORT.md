# Dual tracker support (GitHub + GitLab) without the old complexity

Research note, 2026-09-03. Sources are official docs or first-party pages only, cited inline.

## Question

Northstar is being simplified to GitHub-only. How should it later support GitHub and GitLab at the same
time without re-growing what it just removed: dual `GitHub`/`GitLab` link columns, a saga with outbox and
retry for partial remote failure, two independent server-side claim workflows, and a `Home` authority field?

## Summary / Recommendation

**Pick (b) with (a)'s projection model: one tracker per repo, chosen by config; GitLab as an optional
one-way projection run from CI, never as a peer.** Concretely:

1. The core engine keeps a tiny `Tracker` seam (create, comment, assign, close, find-by-marker) with exactly
   one implementation selected per repo in `northstar.config` (`tracker = github | gitlab`). The table keeps
   one `Issue` column. There is no `Home` field because there is only one tracker; "home" is the config.
2. Every remote write is idempotent by construction: the issue body and every comment carry a marker
   `[northstar:RM-001]` / `[northstar:RM-001][op:<event>:<sha-of-audit-row>]`; the engine searches for the
   marker before creating, and treats "found" as success. This removes the need for an outbox: a failed
   command is simply re-run.
3. A mirror to the *other* platform, if a team wants one, is a separate CI job (`northstar mirror`) that
   projects the canonical issue one way. It never writes back, never gets a table column, and its own state
   lives on the mirror side (a marker in the mirrored issue's description). It can live in a companion
   skill (`northstar-gitlab`), so the core never imports GitLab code.
4. One claim authority: the CI of the canonical tracker. GitHub Actions `concurrency` groups and GitLab CI
   `resource_group` both serialize, but with different queue semantics; the config choice picks one and the
   engine documents only that one. Default-branch merge stays the final arbiter as today.
5. Neither platform offers an idempotency key for issue/comment creation, neither retries webhooks for you,
   and GitLab's mirroring is git-only, so "sync" cannot be delegated to either vendor; a search-then-write
   projection is the only primitive that is safe to retry on both.

Rejected: two live trackers per item (the pre-simplification design). Every bidirectional-sync product
surveyed ends in last-write-wins or manual conflict review; the one first-party tracker integration GitLab
ships (Jira) is one-canonical-plus-projection.

## Findings

### 1. GitHub issues: REST/GraphQL and `gh`

- Create is `POST /repos/{owner}/{repo}/issues` (`title`, `body`, `assignees`, `labels`); update/close/assign is
  `PATCH /repos/{owner}/{repo}/issues/{n}` with `state`, `state_reason` (`completed|not_planned|reopened|duplicate`)
  and `assignees`. No idempotency mechanism; the docs warn "Creating content too quickly ... may result in
  secondary rate limiting." <https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28>
- Comments: `POST /repos/{owner}/{repo}/issues/{n}/comments`, `PATCH /repos/{owner}/{repo}/issues/comments/{id}`;
  list supports `since`. No dedup. <https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28>
- List endpoints cannot filter by body text; body/comment text search is only `GET /search/issues`
  (30 req/min authenticated, 1,000 results max, `incomplete_results` may be true, eventual consistency), with
  `in:body`, `in:comments`, `repo:` qualifiers. <https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28>
  <https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests>
- Secondary limits: 100 concurrent requests, 900 points/min, and "No more than 80 content-generating requests
  per minute and no more than 500 content-generating requests per hour." Best practice: mutate serially, wait
  1 s between writes, honor `retry-after`. <https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api>
  <https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api>
- GraphQL `clientMutationId` is "A unique identifier for the client performing the mutation" (echoed back,
  not an idempotency key). <https://docs.github.com/en/enterprise-cloud@latest/graphql/reference/mutations>
- `gh issue create` prints the issue URL; flags include `--assignee`, `--label`, `--project`, `--recover`, no JSON
  output. `gh issue list --search '<query>' --json number,url --state all` exposes search syntax and is the
  natural "find by marker" call. <https://cli.github.com/manual/gh_issue_create> <https://cli.github.com/manual/gh_issue_list>
- Projects v2 is GraphQL-only (`addProjectV2ItemById(projectId, contentId)`), and "if you attempt to add an item
  that already exists in the project, the system will return the existing item's ID" - the one natively
  idempotent write on GitHub's side. Relevant only as an optional label/board projection.
  <https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects>
- Webhooks: `X-GitHub-Delivery` is a GUID per event and "will be the same" on redelivery; receivers must
  answer in 10 s; GitHub does not auto-retry, you poll deliveries and call the redeliver endpoints.
  `issues` actions include `opened|edited|closed|reopened|assigned|unassigned|...`; `issue_comment` has
  `created|edited|deleted`. <https://docs.github.com/en/webhooks/webhook-events-and-payloads>
  <https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks>
  <https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries>

### 2. GitLab issues: REST and `glab`

- Create `POST /projects/:id/issues` (`title`, `description`, `assignee_ids`, `labels`; `iid` and `created_at`
  settable only by admin/owner). Edit `PUT /projects/:id/issues/:issue_iid` with `state_event=close|reopen`,
  `assignee_ids`, `add_labels`/`remove_labels`. `id` is global, `iid` is per-project and is what URLs and
  API paths use. List supports `search` + `in=title,description`, `labels`, `state`, `iids[]`. No idempotency
  for create; a "content creation rate limit" applies. <https://docs.gitlab.com/ee/api/issues.html>
- Notes: `POST /projects/:id/issues/:iid/notes` (body up to 1,000,000 chars), list sortable only, "notes
  cannot be searched by body content" through the notes API. <https://docs.gitlab.com/ee/api/notes.html>
  Project search `scope=notes` does search comment bodies but "is available only when advanced search is
  enabled" (Elasticsearch); `scope=issues` needs nothing extra. <https://docs.gitlab.com/api/search/>
  Consequence: on GitLab, put the marker in the issue *description* (searchable everywhere), not only in
  comments.
- Rate limits on GitLab.com: issue creation 200/min, notes 60/min, search API 10/min per IP.
  Self-managed: notes default 300/min, issues limit disabled by default.
  <https://docs.gitlab.com/user/gitlab_com/#rate-limits-on-gitlabcom> <https://docs.gitlab.com/rate_limits/content_creation/>
- Work items: issues are now one work-item type; `/issues/:iid` redirects to `/work_items/:iid` with the same
  IID and "the functionality and APIs for issues remain operational". <https://docs.gitlab.com/user/work_items/>
  (GraphQL `workItemCreate` details not verified from the reference page; see open questions.)
- `glab issue create -t -d -a -l -y`, `glab issue note <iid> -m`, `glab issue list --search --in --output json
  --jq`, and `glab api` (REST + GraphQL, `:fullpath`/`:id` placeholders, `--paginate`). Success output of
  `create` is not specified in docs. <https://docs.gitlab.com/cli/issue/create/> <https://docs.gitlab.com/cli/issue/note/>
  <https://gitlab.com/gitlab-org/cli/-/raw/main/docs/source/issue/list.md> <https://docs.gitlab.com/cli/api/>
- Webhooks: `X-Gitlab-Event: Issue Hook | Note Hook`; issue `object_attributes.action` is
  `open|close|reopen|update`, note action `create|update`. `Idempotency-Key` (17.4) and `webhook-id` (19.0) are
  a "unique ID consistent across webhook retries"; `X-Gitlab-Event-UUID` is shared by recursive webhooks.
  Failing hooks are auto-disabled after 4 (temporary) / 40 (permanent) consecutive failures. GitLab's own
  tracker describes current delivery as the "drop" policy; retry policies are an open proposal.
  <https://docs.gitlab.com/ee/user/project/integrations/webhook_events.html>
  <https://docs.gitlab.com/user/project/integrations/webhooks/> <https://gitlab.com/gitlab-org/gitlab/-/work_items/355721>

### 3. GitLab's native GitHub integration

- The GitHub importer copies issues, PRs, comments, labels, milestones, reviews, wiki, releases, but it is a
  one-time migration; "Re-import" makes a new copy. Unmapped authors become the project creator.
  <https://docs.gitlab.com/ee/user/project/import/github.html>
- Pull mirroring (Premium/Ultimate) syncs "branches, tags, and commits" only, every 30 min; the importer page
  states mirroring "does not sync any new or updated pull requests", and by extension no issues.
  <https://docs.gitlab.com/ee/user/project/repository/mirror/pull.html>
- Two-way GitHub<->GitLab sync including issues is a still-open feature request (gitlab-foss#47249).
  <https://gitlab.com/gitlab-org/gitlab-foss/-/issues/47249>
- Verdict: no vendor primitive keeps issues aligned; any mirror is Northstar's own code.

### 4. Server-side serialized claims

- GitHub Actions `concurrency`: groups are repository-wide across workflows (include `github.workflow` to
  scope), case-insensitive; default `queue: single` keeps at most one pending run and *replaces* the pending one
  when another arrives; `queue: max` keeps up to 100 pending in FIFO (ordering "not guaranteed");
  `cancel-in-progress` is incompatible with `queue: max`. `issues`/`issue_comment`/`workflow_dispatch` only
  run the workflow file on the default branch.
  <https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/control-the-concurrency-of-workflows-and-jobs>
  <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency>
  <https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows>
- GitLab CI `resource_group`: project-wide across pipelines, waiting jobs are *queued*, never cancelled
  ("Waiting for resource"); process modes `unordered` (default), `oldest_first`, `newest_first`,
  `newest_ready_first`; one resource per group. There is no issue-event pipeline trigger; webhook-driven triggers
  cover "push and tag events", so a claim on GitLab must be started via the trigger API (`POST
  /projects/:id/trigger/pipeline` with `variables[...]`) or `glab`, not by commenting on an issue.
  <https://docs.gitlab.com/ee/ci/resource_groups/index.html> <https://docs.gitlab.com/ci/triggers/>
- Consequence: the two primitives differ in the case that matters for claims (a dropped pending run on
  GitHub vs a queued one on GitLab). Running both means two different correctness arguments. Run one.

### 5. Existing sync tools and the "one canonical, one projection" pattern

- Unito (commercial): flow direction governs *creation* only; field updates can still flow both ways;
  their own explainer says conflicts reduce to last-write-wins, field-level rules, or manual review, and
  "One-way sync works when you have a clear source of truth and other systems just need to reflect that
  data." <https://guide.unito.io/how-to-change-flow-direction> <https://unito.io/blog/bidirectional-sync/>
- indeedeng/issue-sync (archived 2021): GitHub->Jira one-way; links via Jira custom fields `GitHub ID`,
  `GitHub Number`, `Last Issue-Sync Update`; explicitly "will NOT mirror issues from JIRA to GitHub".
  <https://github.com/indeedeng/issue-sync/blob/master/README.md>
- GitLab's Jira integration: Jira is canonical; GitLab pushes comments, links, and one transition on
  commit/MR mentions and lets users view Jira issues inside GitLab; GitLab does not create/edit ordinary
  Jira issues. <https://docs.gitlab.com/ee/integration/jira/index.html> <https://docs.gitlab.com/integration/jira/issues/>
- No maintained open-source GitHub<->GitLab *issue* sync bot surfaced; results were git mirroring tools.
- Industry pattern: one system owns identity and lifecycle; the other side stores the foreign key (custom
  field or marker) and receives a projection. Northstar already has the canonical side: `ROADMAP.md`.

### 6. Idempotency primitives available for a retry-safe one-way projection

| Need | GitHub | GitLab |
|---|---|---|
| Server-side idempotency key on create | none (`clientMutationId` is a label) | none |
| Find existing by marker | `gh issue list --search 'in:body "[northstar:RM-001]"' --state all` (30/min search API) | `GET /projects/:id/issues?search=[northstar:RM-001]&in=description` (no Elasticsearch needed) |
| Find existing comment by marker | `search/issues in:comments` or list comments since `t` and scan | list notes and scan (notes search needs advanced search) |
| Natively idempotent write | `addProjectV2ItemById` returns existing item | subscribe endpoints return 304 |
| Webhook dedup key | `X-GitHub-Delivery` (stable on redelivery) | `Idempotency-Key` / `webhook-id` |
| Vendor retry of webhooks | no (manual redelivery API) | no ("drop" policy) |

Because a real duplicate can still slip through between search and create (search is eventually consistent
on GitHub), the projection must also tolerate two issues with the same marker: prefer the lowest number,
close the other with `state_reason=duplicate` (GitHub) or `state_event=close` + note (GitLab).

## Architecture proposal

```
 ROADMAP.md + roadmap/items/RM-001.md      (canonical; git merge is the arbiter)
        |
        v  northstar add/claim/update/close  (core engine, stdlib only)
 +-------------------+     Tracker seam: ensure_issue, ensure_comment, set_assignee, set_state
 | tracker = github  |---> gh  ---> github.com/o/r/issues/142   <- the ONE `Issue` column
 |  or               |
 | tracker = gitlab  |---> glab --> gitlab.com/g/p/-/issues/87
 +-------------------+
        |  (optional, CI only, one-way, no table column)
        v  northstar-gitlab mirror   (companion skill; reads canonical issue + brief, writes projection)
 gitlab.com/g/p/-/issues/9   description starts with  [northstar:RM-001][mirror-of:github:o/r#142]
```

**Core engine (skills/northstar/scripts/northstar.py)**
- `Tracker` protocol with two thin adapters, each ~80 lines, both shelling out (`gh`, `glab`). Config picks one:
  `tracker = "github"|"gitlab"`, plus `repo`/`project` path. `validate` rejects a second tracker key.
- Table schema: `| ID | P | Status | Story | Owner | Branch | Issue | Plan | Sync |`. `Issue` holds one URL;
  the adapter is inferred from the URL host, so the table needs no `Home` and no second column.
- Idempotent verbs: `ensure_issue(item)` = search marker in body/description, else create with marker as the
  first line; `ensure_comment(item, op_id, text)` = list comments since the item's last audit timestamp and
  scan for `[northstar:RM-001][op:claim:9f3a]`, else post. `op_id` is derived from the audit row, so a re-run
  of the same command produces the same id and the same no-op. Assign/close are naturally idempotent PATCHes.
- Failure handling: no outbox, no journal of pending destinations. A failed remote call leaves `Sync =
  Pending` in the table and prints the exact command to re-run; re-running is safe by construction. The
  existing `reconcile` stays as a read-only report (canonical vs tracker) and does not need a GitLab leg.
- Rate limits: one write at a time, `sleep 1` between mutations, honor `retry-after` (GitHub) and 429 (GitLab).

**Companion skill (`northstar-gitlab`, or `northstar-mirror`)**
- Owns the mirror job template (`.gitlab-ci.yml` or `.github/workflows/northstar-mirror.yml`), scheduled
  or triggered by the canonical tracker's `issues` webhook -> `POST /projects/:id/trigger/pipeline`.
- Projection rules: create-if-missing by marker, overwrite title/description/labels/state from canonical,
  append only *new* canonical comments (dedup by `[op:...]`). Never writes back; drift from edits on the
  mirror is reported, not merged. Mirror URL is recorded in the *brief* (`Mirror:` field), not the table.
- Keeps all GitLab-specific knowledge (iid vs id, description-search, notes rate limit) out of the core.

**Claim workflow: one authority**
- Ship exactly one server-side claim template per tracker and install only the one matching `tracker`.
  GitHub: `concurrency: {group: northstar-claim-${{ github.repository }}, queue: max}` (so a second claimant
  waits instead of being dropped); GitLab: `resource_group: northstar-claim` with `oldest_first`.
- The workflow commits the claim to the default branch; the merge is the lock. The tracker comment is a
  projection of that commit, not the lock itself, so a lost webhook or dropped run costs a retry, not
  correctness.

**Why (b)+(a) over pure (a) or pure (c)**
- Pure (a) hard-codes GitHub as canonical; GitLab-only teams (self-managed, no GitHub) would be excluded.
  The adapter seam costs one interface and gives them parity with no combinatorics.
- Pure (c) would force the companion to re-implement add/claim/close for GitLab, duplicating the engine's
  lifecycle logic; the seam keeps lifecycle in one place and leaves only the mirror to the companion.
- Trade-off accepted: a team that wants full two-way collaboration on both platforms is out of scope; they
  get a read-only mirror. This is the same stance GitLab takes toward Jira.

## Open questions

1. GitLab GraphQL `workItemCreate` / work-item IIDs: the reference page was too large to confirm input
   fields; verify before relying on GraphQL instead of REST issues (REST is sufficient today).
2. Should the marker be a label (`northstar:RM-001`) in addition to a body line? Labels are filterable on both
   list endpoints without search quotas (GitHub `labels=`, GitLab `labels=`) but count against label limits
   and clutter the UI.
3. Search quotas for large roadmaps: 30/min (GitHub search) and 10/min per IP (GitLab.com search API) bound a
   bulk `reconcile`; a cached `Issue` URL in the table avoids search in the common path, so only `add` pays.
4. Should `Sync` remain a column at all once retries are idempotent, or move into the brief's history?
5. Which side hosts the mirror job when canonical is GitHub: GitHub Actions calling `glab` (needs a GitLab
   token in GitHub secrets) or GitLab CI polling GitHub (needs a GitHub token in GitLab). Either works;
   recommend the canonical side, so one CI owns all writes.
