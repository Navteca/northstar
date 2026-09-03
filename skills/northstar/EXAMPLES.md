# Northstar engine recipes

For the agent, CI, and troubleshooting. Run without `--apply` to preview, confirm when `SKILL.md` requires it, then apply. In a set-up repository use `roadmap/bin/northstar.py`.

| User wording | Operation |
|---|---|
| "Create/add this story" | `add` |
| "Import issue #151" | `add --origin github --origin-url <issue URL>` |
| "Change priority/status/title", "this is blocked" | `update` |
| "Pick this up/start this" | `pickup` |
| "Use Wayfinder/Spec Kit for this" | `pickup --planning --plan-kind … --plan …` or `link-plan` |
| "Give/transfer this to…" | `handoff` |
| "Check/fix issue drift" | `reconcile` |
| "Finish/close/deliver this" | `close` |

```sh
N=roadmap/bin/northstar.py

python3 $N add --title "Team invitations" --priority P1 --status Ready \
  --story "As a workspace admin, I want to invite teammates, so that I can onboard them without support." \
  --acceptance "Admin can invite an email address" \
  --acceptance "An invitation can be accepted once" --apply

python3 $N pickup RM-024 --owner Maya --branch feat/rm-024-invitations --apply

python3 $N pickup RM-025 --owner Maya --branch feat/rm-025-workspace-roles \
  --planning --plan-kind Wayfinder --plan https://github.com/acme/product/issues/155 --apply

python3 $N link-plan RM-025 --actor Maya --status Ready --plan-kind Wayfinder \
  --plan https://github.com/acme/product/issues/155 --reason "Map cleared and context captured" --apply

python3 $N pickup RM-026 --owner Iker --branch feat/rm-026-billing \
  --planning --plan-kind "Spec Kit" --execution-method RPI --plan docs/specs/rm-026-billing.md --apply

python3 $N update RM-024 --actor Maya --status Blocked --reason "Waiting on vendor API keys" --apply

python3 $N handoff RM-024 --actor Maya --to Iker --reason "Pairing ownership transferred" --apply

python3 $N close RM-024 --actor Iker \
  --context "Graphify: updated graphify-out at abc123; docs/decisions/invitations.md" \
  --evidence "GitHub PR #142" --apply
```

Without Graphify, `--context "Repository: docs/decisions/invitations.md; GitHub PR #142"` is valid.
