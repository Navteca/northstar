# Northstar internal engine recipes

These recipes are for the agent, CI, and troubleshooting. Users normally express intent in natural language. Preview every mutation without `--apply`, translate it, confirm when required by `SKILL.md`, then apply internally.

```sh
python3 skills/northstar/scripts/northstar.py
```

| User wording | Operation |
|---|---|
| “Create/add this story” | `add` |
| “Change priority/status/title” | `update` |
| “Pick this up/start this” | `pickup` |
| “Use Wayfinder for this” | `pickup --planning --plan …` or `link-plan` |
| “Specify this feature before implementation” | `pickup --planning --plan-kind "Spec Kit" --plan …` or `link-plan --plan-kind "Spec Kit"` |
| “Give/transfer this to…” | `handoff` |
| “Check/fix tracker differences” | `reconcile` |
| “Finish/close/deliver this” | `close` |

```sh
python3 skills/northstar/scripts/northstar.py add \
  --title "Team invitations" --priority P1 --status Ready --home github \
  --story "As a workspace admin, I want to invite teammates, so that I can onboard them without support." \
  --acceptance "Admin can invite an email address" \
  --acceptance "An invitation can be accepted once"

python3 skills/northstar/scripts/northstar.py pickup RM-024 \
  --owner Maya --actor Maya --branch feat/rm-024-invitations

python3 skills/northstar/scripts/northstar.py pickup RM-025 \
  --owner Maya --actor Maya --branch feat/rm-025-workspace-roles --planning \
  --plan-kind Wayfinder --plan https://github.com/acme/product/issues/155

python3 skills/northstar/scripts/northstar.py link-plan RM-025 \
  --actor Maya --status Ready \
  --plan-kind Wayfinder \
  --plan https://github.com/acme/product/issues/155 \
  --reason "Wayfinder map cleared and context captured"

python3 skills/northstar/scripts/northstar.py pickup RM-026 \
  --owner Iker --actor Iker --branch feat/rm-026-billing \
  --planning --plan-kind "Spec Kit" --execution-method RPI \
  --plan docs/specs/rm-026-billing.md

python3 skills/northstar/scripts/northstar.py handoff RM-024 \
  --actor Maya --to Iker --reason "Pairing ownership transferred"

python3 skills/northstar/scripts/northstar.py close RM-024 \
  --actor Iker \
  --context "Graphify: updated graphify-out at abc123; PR #142" \
  --evidence "GitHub PR #142 and GitLab MR !87"
```

For a project without Graphify, valid context can instead be `Repository: docs/decisions/invitations.md; GitHub PR #142`.
