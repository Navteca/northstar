---
name: setup-northstar
description: Configures Northstar for one repository. Detects an existing roadmap and the authenticated GitHub session, vendors the engine into roadmap/bin, offers optional CI workflows and companions (Wayfinder, Spec Kit, Graphify, cc-rpi). Use when first enabling Northstar, linking a GitHub repository, or checking roadmap integration health.
---

# Set up Northstar

Run once per repository and again to change an integration.

## Inspect before changing anything

1. Run `scripts/northstar.py doctor` (beside the `northstar` skill) and locate `ROADMAP.md` plus `roadmap/northstar.toml`.
2. If a roadmap exists, validate and preserve it. If absent, preview `init` and ask before applying.
3. Run `gh auth status`. Show the account name; never print or store tokens.
4. Detect Wayfinder, Graphify (`graphify`), Spec Kit (`specify`), and cc-rpi (`.claude/commands/bootstrap` or an `AGENTS.md` mentioning it). Treat each as an explicit choice.

## Link GitHub

Ask which repository (`owner/name`) should hold the issues and, optionally, which GitHub Project title to add them to. Ask before creating or replacing configuration. Store safe identifiers only:

```toml
version = 1

[github]
enabled = true
repository = "acme/product"
project_title = "Product roadmap"

[companions]
profile = "Core"
wayfinder = false
speckit = false
graphify = false
rpi = false

[policy]
default_route = "Direct"

[identities.Maya]
github = "maya-gh"
```

Map each teammate's stable roadmap name to their GitHub login. `doctor` lists owners that are missing a mapping; without one, pickup cannot assign the issue and the claim workflow cannot resolve the actor.

## Vendor the engine and offer workflows

Run `scripts/install_operational_assets.py --root <repo>` to preview, then `--apply` after approval. It copies the engine to `roadmap/bin/` and the selected workflow templates to `.github/workflows/`; `--workflow policy --workflow claim` limits the set. Never pass `--force` unless the user approved replacing each reported conflict. It also adds `roadmap/.northstar.lock` to `.gitignore`; everything else under `roadmap/` is versioned.

Recommend `policy` for every team. Offer `claim`, `reconcile`, `maintenance`, and `notify` only when the team asks for them; each is described in the `northstar` skill's OPERATIONS.md. If the default branch is protected, the `claim`, `maintenance`, and `notify` workflows need a `NORTHSTAR_PUSH_TOKEN` secret that may bypass protection for roadmap paths.

Offer the `assets/common/CODEOWNERS.snippet` after asking for the actual maintainer team; never install a placeholder owner.

## Offer companions

Read [PROFILES.md](PROFILES.md). Select the profile during setup, not silently during package installation. Each roadmap item still chooses Direct, Wayfinder, or Spec Kit independently.

- Wayfinder: for large, foggy items. If absent, explain the benefit and offer the Navteca skills distribution; never install without consent.
- Spec Kit: for features that need a formal specification. If `specify` is absent, offer `uv tool install specify-cli`.
- Graphify: for durable codebase context at closeout. If absent, offer `uv tool install --upgrade graphifyy`.
- cc-rpi: an execution method, not a roadmap. Point to the [upstream instructions](https://github.com/juan294/cc-rpi); never clone it silently.

## Verify

Run `validate` and `doctor`, summarize the linked repository, mapped identities, installed workflows, and selected companions. Re-running setup must show the existing configuration before proposing changes.
