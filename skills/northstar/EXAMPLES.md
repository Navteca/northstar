# Northstar internal engine recipes

This file is for the agent, CI, and troubleshooting. Users normally express intent in natural language; do not ask them to construct these commands.

For every mutation:

1. Translate the user's intent into an engine operation.
2. Run it without `--apply`.
3. Translate the preview into plain language.
4. Ask for confirmation when required by `SKILL.md`.
5. Repeat with `--apply` internally.

Engine prefix:

```sh
python3 skills/northstar/scripts/northstar.py
```

## Intent mapping

| User wording | Operation |
|---|---|
| “Create/add this story” | `add` |
| “Change priority/status/title” | `update` |
| “Pick this up/start this” | `claim` |
| “Give/transfer this to…” | `handoff` |
| “Check/fix tracker differences” | `reconcile` |
| “Finish/close/deliver this” | `close` |

## Add a ready story

```sh
python3 skills/northstar/scripts/northstar.py add \
  --title "Team invitations" \
  --priority P1 \
  --status Ready \
  --story "As a workspace admin, I want to invite teammates, so that I can onboard them without support." \
  --acceptance "Admin can invite an email address" \
  --acceptance "An invitation can be accepted once"
```

## Import external work

```sh
python3 skills/northstar/scripts/northstar.py add \
  --title "Usage dashboard" \
  --priority P2 \
  --story "As an account owner, I want to review usage, so that I can manage adoption." \
  --acceptance "Weekly active usage is visible" \
  --origin github \
  --origin-url https://github.com/acme/product/issues/42
```

## Claim, hand off, reconcile, and close

```sh
python3 skills/northstar/scripts/northstar.py claim RM-024 \
  --owner Maya --actor Maya \
  --branch feat/rm-024-invitations \
  --wayfinder roadmap/maps/RM-024.md

python3 skills/northstar/scripts/northstar.py handoff RM-024 \
  --actor Maya --to Iker --reason "Pairing ownership transferred"

python3 skills/northstar/scripts/northstar.py reconcile RM-024

python3 skills/northstar/scripts/northstar.py close RM-024 \
  --actor Iker \
  --graphify "Updated: graphify-out at abc123" \
  --evidence "GitHub PR #142 and GitLab MR !87"
```
