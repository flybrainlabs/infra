# flybrainlabs infra

Build, release and operations for [flybrainlabs](https://flybrain.work/).

`flybrainlabs/web` is private. Complete workspace checkout requires an authorized
identity for that component. Use an authenticated HTTPS credential helper or
pass `--transport ssh` to `workspace.py checkout`. The operator environment uses
`--ssh-host github-flybrainlabs` with `GIT_SSH_COMMAND='ssh -F
/workspace/.ssh/config'`; keys remain outside repositories. Public components
retain their existing visibility.

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
[infrastructure release manifest](https://github.com/flybrainlabs/infra/blob/main/release-manifest.json).

## Build and test

Use Rust 1.90 or newer (the source uses edition 2024), Node 22 or newer and Python
3.11 or newer. Optional scientific Python dependencies are in
`tools/requirements-research.txt` in the assembled workspace. SBF builds require
the compatible Solana/Agave build tools.

First assemble the exact source revisions:

```sh
git clone https://github.com/flybrainlabs/infra.git flybrainlabs/infra
python3 flybrainlabs/infra/tools/workspace.py checkout --repos flybrainlabs
python3 flybrainlabs/infra/tools/workspace.py assemble --repos flybrainlabs --output flybrainlabs-workspace
cd flybrainlabs-workspace
npm ci
```

Run the applicable checks from the assembled workspace:

```sh
python3 -B -m unittest discover -s ../flybrainlabs/infra/tests -p test_workspace.py -v
python3 ../flybrainlabs/infra/tools/check_sources.py --repos ../flybrainlabs
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
  `flybrainlabs/infra` using normal fast forwards.
- Keys, wallets, customer inputs, node databases, private artifacts, browser
  profiles and model caches stay outside Git and website exports.
- Production payment and reward configuration remains disabled until its actual
  asset identities, authorities, funds and operating gates are satisfied.

See [AGENTS.md](AGENTS.md), the
[development guide](https://github.com/flybrainlabs/docs/blob/main/docs/DEVELOPMENT.md),
[architecture](https://github.com/flybrainlabs/docs/blob/main/docs/ARCHITECTURE.md)
and [status](https://github.com/flybrainlabs/docs/blob/main/docs/STATUS.md).

## License and provenance

Project code retains the declared `MIT OR Apache-2.0` license. Data descriptors
and third-party assets retain their own source attribution and licenses; this
code license does not relicense MaleCNS data or third-party libraries. The
import preserves numerical/identity fixtures and does not reinterpret existing
scientific or financial records. See [NOTICE](NOTICE).

## Wallet mining V3

The finite Solana Devnet wallet-mining extension is described in the
[execution and acceptance record](https://github.com/flybrainlabs/docs/blob/main/docs/WALLET_MINING_V3_EXECUTION.md)
and [canonical Result layout](https://github.com/flybrainlabs/docs/blob/main/docs/WALLET_MINING_V3_RESULT_LAYOUT.md).
Use the assembled workspace for cross-component imports and pinned release
verification. Public receipts are in the contracts repository under
`deploy/wallet-mining-v3/`; private signers, signed journals and full response
archives remain outside source repositories. The two-unit acceptance budget is
complete. Future paid work requires a new prospectively frozen finite plan.
Actual extension-wallet and physical-device confirmation remain separate gates.


## Community deployment

`deploy/target-v2/flybrainlabs-community.service` runs the separate Social process on 8791; `nginx-community.conf` proxies its paths with existing request limits. `tools/upgrade_community.sh` creates a coherent database backup, applies an additive migration, preserves runtime hashes and business counts, and leaves existing financial/scientific services running. Install only public Social files plus pinned parse5/entities dependencies. Read `docs/social-community-system.md` before rollback; do not erase legitimate post-backup writes.

## Task Factory V4 Devnet deployment

`docs/TASK_FACTORY_V4_DEPLOYMENT.json` records the program upgrade, preserved
V3 accounts, inactive verifier installation and read-only chain preview. The
existing product UI remains V3; no new factory or reward budget is enabled.

Run `tools/deploy_task_factory_v4.mjs` from the assembled workspace with the
reviewed public plan, exact ELF, existing authority key path, an operator-only
transport directory and a public report path. Its default is read-only preflight;
`--apply` performs only the bounded existing-program upgrade. It checks Devnet
genesis, SBPF v3 activation, authority, ELF hashes and rent/fee ceilings, retains
the previous executable, journals signed transport before sending, simulates the
upgrade and verifies finalized bytes. It cannot initialize or fund a factory.
Private keys and signed journals never belong in the repository or public build.

`tools/stage_factory_verifier_v4.py UPLOAD [--apply]` runs on the authorized
original node. It checks an exact source manifest, imports the verifier and
checks existing complete-model hashes. Installation is beside V3, changes no
private runtime or database and restarts no service. It does not activate a
verifier, select a catalog or authorize a reward budget.
