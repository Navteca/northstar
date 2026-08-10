# Northstar capability profiles

Installation and repository setup are separate decisions:

1. `npx skills@latest add` installs skill instructions.
2. Setup detects local tools and authenticated sessions, then asks which destinations and companions to enable.
3. Each roadmap item chooses Direct, Wayfinder, or Spec Kit independently.

The standard Skills installer does not resolve dependencies across repositories. These are explicit, reviewable profile recipes.

| Profile | Includes | Install recipe |
|---|---|---|
| Core | Northstar roadmap and setup | `npx skills@latest add Navteca/northstar --skill northstar --skill setup-northstar` |
| Wayfinder | Core + Navteca downstream Wayfinder stack | Then `npx skills@latest add Navteca/skills --skill wayfinder --skill grilling --skill domain-modeling --skill research --skill prototype --skill to-spec --skill to-tickets --skill implement` |
| Spec Kit | Core + Spec Kit CLI/instructions | Ask consent for `uv tool install specify-cli`, then install Spec Kit instructions for the selected agent environment |
| Full | Core + Wayfinder + Spec Kit + Graphify | Apply both companion recipes; ask consent for `uv tool install --upgrade graphifyy` if `graphify` is unavailable |

## Detection

```sh
gh auth status
glab auth status
graphify --version
specify --version
```

Show identities and versions only. Never print tokens. The profile records booleans and a default route in `roadmap/northstar.toml`; it does not claim a missing tool was installed.

## Route guidance

- **Direct:** the story is clear and implementation can begin from the brief.
- **Wayfinder:** the story is large or technically uncertain; create one canonical map and link it before pickup.
- **Spec Kit:** the feature needs a formal specification, acceptance boundaries, or multi-step design; approve the spec before implementation.
