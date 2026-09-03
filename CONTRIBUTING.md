# Contributing to Northstar

## Verify before and after changes

```sh
python3 -m unittest discover -s skills/northstar/tests -v
python3 -m py_compile skills/northstar/scripts/*.py skills/setup-northstar/scripts/*.py skills/northstar/tests/*.py
python3 skills/northstar/scripts/northstar.py --root examples/sample-project validate
python3 skills/northstar/scripts/northstar_admin.py --root examples/sample-project policy
python3 skills/northstar/scripts/northstar_admin.py --root examples/sample-project render --check
```

CI runs the same commands on every pull request. The live GitHub contract is opt-in and needs a dedicated sandbox repository.

## Rules that keep Northstar small

- `ROADMAP.md` stays a nine-column Markdown table. Detail goes in the item brief, never in new columns.
- One tracker per repository. GitLab support is a future companion; see `docs/research/DUAL_TRACKER_SUPPORT.md` before proposing it.
- The engine is standard library only and must run standalone from `roadmap/bin/` in a product repository. Never import from the skill directory at runtime.
- Lifecycle rules live once, in `TRANSITIONS` in `northstar.py`. CI policy imports it.
- Both `SKILL.md` files stay under 100 lines. Reference material goes in the one-level `REFERENCE.md`, `OPERATIONS.md`, `EXAMPLES.md`, and `PROFILES.md`. The responsibility table lives only in `docs/DESIGN_AND_VALUE.md`.
- Tests never contact GitHub; mock `northstar.command`.
- When the roadmap schema, lifecycle, or workflow templates change, update `examples/sample-project` and regenerate its views with `render`.

## Publishing

- Stage exact paths; no `git add -A`.
- Commits, pushes, merges, and anything that creates GitHub records need explicit authorization from the repository owner.
- Reuse an existing pull request for the same change rather than opening another.
