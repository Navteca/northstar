# Northstar examples

Commands default to a preview. Add `--apply` only after the user approves the displayed operation. Add `--local-only` when preparing a canonical roadmap change that must be merged before publishing it to external trackers.

## Initialize a roadmap

```sh
python3 skills/northstar/scripts/northstar.py init
python3 skills/northstar/scripts/northstar.py init --apply
```

## Add a ready user story

```sh
python3 skills/northstar/scripts/northstar.py add \
  --title "Team invitations" \
  --priority P1 \
  --status Ready \
  --story "As a workspace admin, I want to invite teammates, so that I can onboard them without support." \
  --acceptance "Admin can invite an email address" \
  --acceptance "An invitation can be accepted once"
```

## Import externally-created work

```sh
python3 skills/northstar/scripts/northstar.py add \
  --title "Usage dashboard" \
  --priority P2 \
  --story "As an account owner, I want to review usage, so that I can manage adoption." \
  --acceptance "Weekly active usage is visible" \
  --origin github \
  --origin-url https://github.com/acme/product/issues/42
```

With `--apply`, Northstar links rather than duplicates the source issue and comments that it was imported into canonical `ROADMAP.md`.

## Reconcile remote drift

```sh
python3 skills/northstar/scripts/northstar.py reconcile RM-024
python3 skills/northstar/scripts/northstar.py reconcile RM-024 \
  --strategy canonical --actor Maya --reason "Restore the approved roadmap state" --apply
```

The first command only reports differences. To import a chosen remote change, use the normal gated `add --origin`, `claim`, `handoff`, `update`, or `close` command; this preserves its audit and validation rules.

## Claim, hand off, and close

```sh
python3 skills/northstar/scripts/northstar.py claim RM-024 \
  --owner Maya --actor Maya \
  --branch feat/rm-024-invitations \
  --wayfinder roadmap/maps/RM-024.md

python3 skills/northstar/scripts/northstar.py handoff RM-024 \
  --actor Maya --to Iker --reason "Pairing ownership transferred"

python3 skills/northstar/scripts/northstar.py close RM-024 \
  --actor Iker \
  --graphify "Updated: graphify-out at abc123" \
  --evidence "GitHub PR #142 and GitLab MR !87"
```
