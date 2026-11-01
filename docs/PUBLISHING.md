# Publishing to GitHub and HACS

Target repository: `matzem79/home-assistant-energy-costs`.
Current integration version: **0.2.3**. The local `origin` remote uses HTTPS:
`https://github.com/matzem79/home-assistant-energy-costs.git`.
Code and original artwork use the MIT license in `LICENSE`.

## Publication status

The source and release tooling are prepared locally. At the last remote check,
the target repository was not accessible under the configured GitHub account;
no successful push or GitHub release had been confirmed. Verify the current
remote state before creating anything. Preparation does not create a repository,
publish a release, or submit the integration to the HACS default catalog.

## Local checks and packaging

Run these commands in the local `energy-costs` project directory:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q custom_components scripts
python3 scripts/build_release.py
git diff --check
git status --short
```

The package is `dist/energy-costs-0.2.3.zip`. It contains the integration,
including `brand/`, plus README, changelog, and license. Local histories, editor
files, caches, tests, and build tools are excluded. Build outputs are ignored by Git.

The tests use HA boundary doubles. They do not replace a full HA/hassfest run.
Manual icon display has been confirmed. Before a public release, verify setup,
options, restart persistence, history import, and installation/update through HACS.
The integration requires HA 2026.1; local icon display requires HA 2026.3.

## HTTPS authentication

The previous SSH push failed with `Permission denied (publickey)`. The local
remote was changed to HTTPS and configured to use the GitHub CLI credential
helper. No token is stored in the remote URL or repository files.

Check the account, remote, and local commits:

```sh
gh auth status
git remote -v
git status --short
git log -1 --oneline
```

If authentication is missing or expired:

```sh
gh auth login --hostname github.com --git-protocol https --web
```

On another checkout, configure the existing remote and repository-local helper:

```sh
git remote set-url origin https://github.com/matzem79/home-assistant-energy-costs.git
git config --local --replace-all credential.https://github.com.helper ''
git config --local --add credential.https://github.com.helper '!gh auth git-credential'
```

## Create the public repository and push

**The repository must be public for HACS.** A normal Git push does not create a
missing GitHub repository. Create the empty target, then push the committed source:

```sh
gh repo create matzem79/home-assistant-energy-costs --public --description "Independent import and export electricity cost accounting for Home Assistant"
git push -u origin main
```

Alternatively, create an empty public repository on GitHub with owner `matzem79`
and name `home-assistant-energy-costs`. Do not initialize a README, license, or
`.gitignore` there: these already exist in the local history. Then push `main`.
Do not add `origin` again if it is already configured.

If the repository already exists, inspect it instead of recreating it:

```sh
gh repo view matzem79/home-assistant-energy-costs --json nameWithOwner,url,isPrivate
```

If it is private, change its visibility to public in GitHub's repository settings
before distributing the HACS installation instructions. Add repository topics:

```sh
gh repo edit matzem79/home-assistant-energy-costs --add-topic home-assistant --add-topic hacs --add-topic custom-integration --add-topic energy
```

After pushing, check the branch and CI:

```sh
git status -sb
gh run list --limit 5
```

## HACS distribution

The repository contains a single integration at `custom_components/energy_costs/`
and the required integration manifest fields. Root `hacs.json` sets the display
name, minimum HA version, and `render_readme: true`. HACS reads that README for
its repository description.

Use the [README installation instructions](../README.md#installation-with-hacs)
to add the public URL as a custom repository of type **Integration**, download it,
restart HA, and add Energy Costs under Devices & services. Verify this flow on a
live HACS installation before claiming it has been tested.

HACS uses the integration directory from the selected release tag or default
branch. `zip_release` is intentionally not enabled: the generated ZIP contains
an outer `custom_components/` directory and is for manual installation. Published
releases provide version choices; a draft release is not a published version.

Adding the project to the HACS default catalog is a separate submission process.
Users can add this custom repository without that catalog listing.

Official references:

- [HACS general repository requirements](https://hacs.dev/docs/publish/start/)
- [HACS integration requirements](https://www.hacs.dev/docs/publish/integration/)
- [HACS custom repositories](https://hacs.dev/docs/faq/custom_repositories/)

## Create a versioned release

After CI and the manual HA/HACS checks pass:

```sh
git tag -a v0.2.3 -m "Energy Costs 0.2.3"
git push origin v0.2.3
```

The tag workflow checks that the tag matches `manifest.json`, runs the tests,
builds the manual-install ZIP, and creates a **draft release** on GitHub.
Review and publish that draft to make it a released version for users and HACS.
Pushing `main` alone does not create a release. For future versions, update the
manifest, changelog, documented version, and tag consistently.
