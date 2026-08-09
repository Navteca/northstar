# Maintaining the Navteca skills distribution

Northstar remains its own skill and repository. Navteca's Wayfinder integration lives in a downstream distribution of Matt Pocock's skills so Wayfinder can understand the Northstar handoff without making Northstar responsible for discovery.

## Branch policy

- `main` mirrors `mattpocock/skills` and is never customized.
- `navteca` is the stable downstream branch and the installation source for the team.
- Short-lived `navteca/*` branches contain each focused change and merge into `navteca`.
- `upstream` points to `mattpocock/skills`; `origin` points to the Navteca fork.

Do not intentionally diverge without limits. Treat the fork as a maintained downstream patch set: generic fixes should be proposed upstream; Navteca-specific roadmap behavior may remain downstream. Keep each customization small, tested, documented, and easy to replay.

## Update cycle

1. Fetch `upstream` and fast-forward the mirror `main` to `upstream/main`.
2. Push the mirror `main` to the Navteca fork.
3. Merge `main` into `navteca` (do not routinely rebase the shared branch).
4. Resolve conflicts in a short-lived integration branch.
5. Run the upstream repository checks plus focused Wayfinder validation.
6. Merge and push `navteca`; review the documented Navteca patch inventory.

Using merges on the team branch preserves a stable shared history and avoids force-pushes. An occasional clean rebase is acceptable before the branch is shared, not after it becomes the team's installation source.

## Patch inventory

Record every downstream-only change in the fork's `NAVTECA.md` with:

- purpose and owner;
- affected skills/docs;
- upstream issue or PR when applicable;
- validation command;
- whether the patch can be removed after a future upstream release.

Install from the stable downstream branch explicitly:

```sh
npx skills@latest add Navteca/skills@navteca
```

Pin a commit for reproducible team rollouts when the installer supports it. Test upgrades in one repository before changing the team-wide installation reference.
