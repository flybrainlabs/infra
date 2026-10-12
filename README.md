# Flybrain infra

Build, release and operations for [Flybrain](https://flybrain.work/).

## Scope

Pinned multi-repository assembly, source ownership and publication checks, systemd/nginx examples, release validation, backup and rollback tooling. Production runtime data and credentials are external to every repository.

## Source map

- `tools/workspace.py`
- `tools/check_sources.py`
- `tools/publish_components.py`
- `deploy/`
- `release-manifest.json`

Each imported file has one owning repository. `component.json` maps maintained
files into the shared build layout. Dependencies are pinned by commit in the
[infrastructure release manifest](https://github.com/flybrainwork/infra/blob/main/release-manifest.json).

## Build and test

Use Rust 1.90 or newer (the source uses edition 2024), Node 22 or newer and Python
3.11 or newer. Optional scientific Python dependencies are in
`tools/requirements-research.txt` in the assembled workspace. SBF builds require
the compatible Solana/Agave build tools.

First assemble the exact source revisions:

```sh
git clone https://github.com/flybrainwork/infra.git flybrain/infra
python3 flybrain/infra/tools/workspace.py checkout --repos flybrain
python3 flybrain/infra/tools/workspace.py assemble --repos flybrain --output flybrain-workspace
cd flybrain-workspace
npm ci
```

Run the applicable checks from the assembled workspace:

```sh
python3 -B -m unittest discover -s ../flybrain/infra/tests -p test_workspace.py -v
python3 ../flybrain/infra/tools/check_sources.py --repos ../flybrain
```

This transition keeps the existing cross-component import paths intact. Cloning
this repository alone does not supply its external components. The assembler
creates a disposable build layout; all maintained edits belong to the owning
repositories. Use `workspace.py sync` for intentional changes made in that layout,
then review the component diffs and validate them before publication.

Full-model and browser integration checks require existing, verified local
resources and explicit arguments. They do not download a model or reset a
browser profile by default. Isolated chain checks require their own local bank;
production funds and addresses are never substituted.

## Development policy

- All maintained documentation, commit messages, issues, PRs and release notes
  are written in English. Product interfaces may remain bilingual.
- Completed, verified updates are committed and pushed automatically to
  `flybrainwork/infra` using normal fast forwards.
- Keys, wallets, customer inputs, node databases, private artifacts, browser
  profiles and model caches stay outside Git and website exports.
- Production payment and reward configuration remains disabled until its actual
  asset identities, authorities, funds and operating gates are satisfied.

See [AGENTS.md](AGENTS.md), the
[development guide](https://github.com/flybrainwork/docs/blob/main/docs/DEVELOPMENT.md),
[architecture](https://github.com/flybrainwork/docs/blob/main/docs/ARCHITECTURE.md)
and [status](https://github.com/flybrainwork/docs/blob/main/docs/STATUS.md).

## License and provenance

Project code retains the declared `MIT OR Apache-2.0` license. Data descriptors
and third-party assets retain their own source attribution and licenses; this
code license does not relicense MaleCNS data or third-party libraries. The
import preserves numerical/identity fixtures and does not reinterpret existing
scientific or financial records. See [NOTICE](NOTICE).
