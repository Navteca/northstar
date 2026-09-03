# Northstar capability profiles

Installation and repository setup are separate steps: `npx skills@latest add` installs skill instructions; setup detects local tools and asks which companions to enable. The Skills installer does not resolve dependencies across repositories, so companion installs are explicit.

| Profile | Adds | Install recipe |
|---|---|---|
| Core | Northstar roadmap and setup | `npx skills@latest add Navteca/northstar --skill northstar --skill setup-northstar` |
| Wayfinder | Navteca downstream Wayfinder stack | `npx skills@latest add Navteca/skills --skill wayfinder --skill grilling --skill domain-modeling --skill research --skill prototype --skill to-spec --skill to-tickets --skill implement` |
| Spec Kit | Spec Kit CLI | `uv tool install specify-cli`, then Spec Kit's instructions for the agent environment |
| RPI | cc-rpi execution workflow | Clone [cc-rpi](https://github.com/juan294/cc-rpi) and run its documented `scripts/install.sh` |
| Full | All of the above plus Graphify | Apply each recipe with consent; Graphify is `uv tool install --upgrade graphifyy` |

Ask consent for every external installation. The profile records booleans in `roadmap/northstar.toml`; it does not claim a missing tool was installed.

## Detection

```sh
gh auth status
graphify --version
specify --version
ls .claude/commands/bootstrap AGENTS.md
```

## Route guidance

- **Direct:** the story is clear; implement from the brief.
- **Wayfinder:** the story is large or technically uncertain; create one canonical map on the GitHub issue and link it before pickup.
- **Spec Kit:** the feature needs a formal specification; approve the spec before implementation.
- **RPI execution:** after a plan is approved, cc-rpi runs Research → Plan → Implement → Validate. Orthogonal to the planning route: Direct + RPI, Wayfinder + RPI, and Spec Kit + RPI are all valid.
