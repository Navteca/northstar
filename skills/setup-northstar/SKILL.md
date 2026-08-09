---
name: setup-northstar
description: Configures Northstar for one repository, detects an existing roadmap and authenticated GitHub/GitLab sessions, and offers optional Wayfinder and Graphify companions. Use when first enabling Northstar, connecting or changing tracker destinations, or checking roadmap integration health.
disable-model-invocation: true
---

# Set up Northstar

Run once per repository and again to change an integration.

## Inspect before changing anything

1. Run the bundled `doctor` operation and locate `ROADMAP.md` plus `roadmap/northstar.toml`.
2. If a roadmap exists, validate and preserve it. If absent, preview initialization and ask before applying.
3. Detect authenticated `gh` and `glab` sessions. Show account names without exposing or storing tokens.
4. Detect Wayfinder and Graphify, but treat both as optional companions.

## Select tracker destinations

Show the authenticated accounts and accessible repository/project choices. Ask which exact GitHub destination, GitLab destination, or both should synchronize. For dual tracking, ask which service is the default `Home`; individual rows may override it. Never select a session merely because it exists.

Store safe identifiers only:

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

Map each teammate's stable roadmap name to enabled-service usernames. Ask before creating or replacing configuration.

## Offer companions

- Wayfinder is recommended only for large, foggy roadmap items. It brings its own workflow dependencies from the skills distribution. If unavailable, explain the benefit and offer to install the approved Navteca skills distribution; never install without consent.
- Graphify is recommended for persistent codebase context, especially on architecture-heavy projects. Northstar still works without it by linking durable repository/tracker evidence. If its skill is present but the `graphify` executable is absent, offer `uv tool install --upgrade graphifyy` with consent.
- Do not install Matt Pocock's entire collection merely because Northstar is installed. Keep unrelated skills optional.

## Verify

Validate the roadmap, summarize connected/unavailable services and optional companions, and explain that each item has one `Home` while its GitHub and GitLab links may both be populated. Re-running setup must show the existing mapping before proposing changes.
