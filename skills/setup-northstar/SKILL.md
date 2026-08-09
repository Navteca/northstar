---
name: setup-northstar
description: Configures Northstar for one repository by initializing its roadmap and detecting authenticated GitHub, GitLab, Wayfinder, and Graphify capabilities. Use when first enabling Northstar, connecting or changing GitHub/GitLab destinations, or verifying roadmap setup.
disable-model-invocation: true
---

# Set up Northstar

Run once per repository and again only to change an integration.

## Inspect

1. Run `python3 skills/northstar/scripts/northstar.py doctor`.
2. Locate `ROADMAP.md` and `roadmap/northstar.toml`.
3. If absent, preview and—with confirmation—run `northstar.py init --apply`.
4. Check authenticated `gh auth status` and `glab auth status`. Never expose, save, or request tokens.
5. Detect Wayfinder and Graphify. Explain any missing closeout dependency before proceeding.

## Select destinations

Show the authenticated accounts and discovered GitHub repositories/Projects and GitLab projects/boards. Ask which exact destinations to synchronize; support either or both. Never select one merely because it is available.

## Configure

Edit `roadmap/northstar.toml`, which stores safe identifiers only:

```toml
version = 1

[github]
enabled = true
repository = "acme/product"
project_title = "Product roadmap"

[gitlab]
enabled = true
project = "acme/product"

[identities.Maya]
github = "maya-gh"
gitlab = "maya-gl"
```

Add a stable identity mapping for each teammate who may claim work. Ask for confirmation before writing or replacing configuration. Never store credentials.

## Verify

Run `northstar.py validate`, summarize connected and unavailable services, and explain that each item may link to GitHub, GitLab, or both. Re-running setup must show the existing mapping before proposing changes.
