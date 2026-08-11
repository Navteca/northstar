# Northstar capability profiles

Installation and repository setup are separate decisions:

1. `npx skills@latest add` installs skill instructions.
2. Setup detects local tools and authenticated sessions, then asks which destinations and companions to enable.
3. Each roadmap item chooses Direct, Wayfinder, or Spec Kit independently.
4. An item may additionally choose the `RPI` execution method; this is orthogonal to its planning route.

The standard Skills installer does not resolve dependencies across repositories. These are explicit, reviewable profile recipes.

| Profile | Includes | Install recipe |
|---|---|---|
| Core | Northstar roadmap and setup | `npx skills@latest add Navteca/northstar --skill northstar --skill setup-northstar` |
| Wayfinder | Core + Navteca downstream Wayfinder stack | Then `npx skills@latest add Navteca/skills --skill wayfinder --skill grilling --skill domain-modeling --skill research --skill prototype --skill to-spec --skill to-tickets --skill implement` |
| Spec Kit | Core + Spec Kit CLI/instructions | Ask consent for `uv tool install specify-cli`, then install Spec Kit instructions for the selected agent environment |
| RPI | Core + cc-rpi execution workflow | Ask consent to clone [cc-rpi](https://github.com/juan294/cc-rpi) and run its documented `scripts/install.sh`; Northstar does not install it silently |
| Full | Core + Wayfinder + Spec Kit + Graphify + RPI | Apply selected companion recipes and ask consent for every external installation |

## Detection

```sh
gh auth status
glab auth status
graphify --version
specify --version
```

For cc-rpi, inspect the project for `.claude/commands/bootstrap` or an `AGENTS.md` file that identifies the compatibility layer. cc-rpi is a project bootstrap and execution methodology, not a tracker or planning database.

Show identities and versions only. Never print tokens. The profile records booleans and a default route in `roadmap/northstar.toml`; it does not claim a missing tool was installed.

## Operational workflows

Setup may copy templates from `assets/github/` or `assets/gitlab/` after approval:

- policy validation for roadmap-changing merge requests;
- serialized server-side pickup on the single `Home` authority;
- scheduled drift reporting;
- archival and generated-view maintenance;
- optional webhook notification delivery.

The repository's opt-in live contract workflow requires dedicated sandbox projects. Never reuse production trackers for contract tests.

`assets/common/CODEOWNERS.snippet` is a template only. Replace its placeholder with an approved team before merging it into an existing CODEOWNERS file, then protect the default branch. The claim/maintenance bot may need a narrowly scoped bypass to update only Northstar paths.

Preview template installation before applying it:

```sh
python3 setup-northstar/scripts/install_operational_assets.py --service github
python3 setup-northstar/scripts/install_operational_assets.py --service github --apply
```

For GitLab, use `--service gitlab` and include the generated `.gitlab-ci.northstar.yml` from the project's main `.gitlab-ci.yml`.

## Route guidance

- **Direct:** the story is clear and implementation can begin from the brief.
- **Wayfinder:** the story is large or technically uncertain; create one canonical map and link it before pickup.
- **Spec Kit:** the feature needs a formal specification, acceptance boundaries, or multi-step design; approve the spec before implementation.
- **RPI execution:** after a plan is approved, run cc-rpi's Research → Plan → Implement → Validate phases. Keep the Northstar item locked and update its roadmap/brief after each meaningful phase and at closeout.
