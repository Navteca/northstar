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
4. Detect Wayfinder, Graphify, and the Spec Kit CLI (`specify`), but treat companions as explicit profile choices.

Read [PROFILES.md](PROFILES.md) for supported profiles. Select the profile during repository setup, not silently during package installation. Each roadmap item can still choose Direct, Wayfinder, or Spec Kit independently.

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

[companions]
profile = "Core"
wayfinder = false
speckit = false
graphify = false

[policy]
default_route = "Direct"

[identities.Maya]
github = "maya-gh"
gitlab = "maya-gl"
```

Map each teammate's stable roadmap name to enabled-service usernames. Ask before creating or replacing configuration.

## Offer companions

- Wayfinder is recommended only for large, foggy roadmap items. It brings its own workflow dependencies from the skills distribution. If unavailable, explain the benefit and offer to install the approved Navteca skills distribution; never install without consent.
- Graphify is recommended for persistent codebase context, especially on architecture-heavy projects. Northstar still works without it by linking durable repository/tracker evidence. If its skill is present but the `graphify` executable is absent, offer `uv tool install --upgrade graphifyy` with consent.
- Spec Kit is recommended for substantial feature work that needs a durable specification before implementation. If selected and `specify` is absent, offer `uv tool install specify-cli` with consent.
- Do not install Matt Pocock's entire collection merely because Northstar is installed. Keep unrelated skills optional.

## Verify

Validate the roadmap, summarize connected/unavailable services and selected companions, and explain that each item has one `Home` while its GitHub and GitLab links may both be populated. Re-running setup must show the existing mapping before proposing changes. Never install a companion, create a tracker record, or store credentials without explicit consent.
