# Multi-repository migration acceptance

Date: 2026-10-12. Owner: `flybrainlabs`.

## Imported source and ownership

Ten repositories contain actual maintained components, English READMEs,
development agreements, licenses/notices and source maps. The original import
covered 707 files. English operating documents and the workspace entrypoint bring
the assembled source map to 715 files. One file has one owner; conflicts and
traversal are rejected. The former checkout remains available locally with its
push URL disabled. No former remote repository, draft PR or live service was
modified by the repository import.

The source baseline is local `39645aaa5c74fe5cd9f981bf572a21a24b7311ec`, tree
`d6490a0fde3655fc8ee57f015f45135eafbfb8b8`. Marketplace catalog/migration and
checked service-domain changes were imported as explicit development work,
not described as a deployed commercial service.

`import-manifest.json` records content hashes and intentional changes. The frozen
protocol vectors and 1,024-byte Submission fixture retain their exact bytes.
Historical Chinese documents/screenshots and all ignored caches/runtime data
remain in the retained local source, outside the new maintained repositories.

## Actual commands and outcomes

The commands below ran from the newly assembled workspace, using the retained
locked dependencies and cached native/WASM outputs. They did not download the
official model or reset a browser profile.

| Verification | Outcome |
| --- | --- |
| `cargo test --locked -p flypow --lib --test target_authority --test product_api --test explorer --test market_catalog -- --test-threads=2` | 52 passed, one existing test ignored |
| `cargo test --locked -p flypow-receipt-v1 -p flypow-task-catalog -p flypow-campaign-core -p flypow-target-protocol -p flypow-economic-core -p flypow-service-core -p flypow-sim-core` | 35 passed; binary/doc test targets also completed |
| `cargo check --locked -p flypow-campaign-program -p flypow-economy-v2-program` | Both existing Solana programs compile on the host |
| `npm run build:web` | Browser bundles built successfully |
| `python3 -B -m unittest discover -s tests -p test_static_export.py -v` with disk-backed `TMPDIR` | Eight passed, including complete executable static packaging and English downloads |
| Infrastructure `test_workspace.py` | Three passed: unique ownership/traversal, cache retention/edit sync and concurrent-edit rejection |
| Source/workflow/English documentation checks | Passed for all ten components |
| Known private wallet/SSH material comparison | Passed; no secret values printed |

The following nine client regression scripts completed successfully:

- `tests/target_protocol_v2.mjs` (native/JavaScript/Python identity and predicates)
- `tests/receipt_v1.mjs`
- `tests/mining_workflow.mjs`
- `tests/goal_output_recovery.mjs`
- `tests/preparation_cancellation_v3.mjs`
- `tests/mining_pool.mjs`
- `tests/service_outbox.mjs`
- `tests/wallet_crypto.mjs`
- `tests/settlement_transport.test.mjs`

Fault-injection/client tests are identified as such; they are not physical-device,
production-fund or independent-operator acceptance.

## Failures resolved during the import

An old native test expected a Chinese whitepaper title. It now verifies the
English document required by the owner while keeping the legacy URL compatible.
The brochure test expected superseded preview copy and hardcoded metrics; it now
checks the actual product routes, real-state placeholders, disabled computation
controls and dynamic policy locations. Disabled brochure controls no longer have
an `aria-describedby` pointing to a missing notice.

The native/JavaScript vector test initially lacked its build-output path in the
new layout; pointing the disposable layout at verified retained outputs resolved
it. A complete export initially exceeded the 256 MiB `/tmp` tmpfs. Re-running in
disk-backed scratch storage passed without deleting model or anatomy caches.

## Publication identity and limitations

### Local account-transition verification

The current `flybrainlabs` source layout contains 716 uniquely owned build files.
The project-identity document, READMEs, component owners, CI ownership checks and
publication targets now use the account selected by the owner. Existing model
and browser caches, protocol identifiers and frozen vector bytes are retained.

The following checks were rerun for this account and display-name transition:

| Verification | Outcome |
| --- | --- |
| `cargo test --locked -p flypow --lib -- --test-threads=2` | 24 passed |
| Static export `test_static_export.py` | Eight passed |
| Infrastructure `test_workspace.py` | Three passed |
| `npm run build:web` | Browser bundles built |
| Current sources and all existing Git blob history | Known private material absent; 802 historical blobs checked |
| English documentation, ownership and source publication paths | Passed |

These checks used retained local dependencies and caches. They did not download
official model data, reset browser profiles or change a live deployment.

On 2026-10-12 the owner selected `flybrainlabs` as the project name and the GitHub
account and authorized recreating all ten repositories. The replacement SSH key
has been verified as `flybrainlabs`; GitHub CLI/API authentication and repository
permissions are checked separately before creation and upload. All current
component origins use `git@github-flybrainlabs:flybrainlabs/<component>.git`.

The earlier `flybrainwork` attempt created ten repositories and verified four
initial uploads before GitHub reported an account suspension. The protocol upload
was unconfirmed and six uploads remained pending. Its local commits and verified
Git bundles are retained as historical provenance, not current publication proof.

The current release manifest records the new account's actual publication status
and verified dependency pins. It stays incomplete until every required component
has been uploaded and checked. No force push, remote deletion, repository transfer
or former-account fallback is part of the current migration.

This acceptance covers repository assembly, component code and source publication.
It does not claim a fresh live deployment, a new SBF service-market integration,
physical-device restoration, external biological accuracy or formal payments.
Those gates remain in the English project status document.

## Completed flybrainlabs source publication

All ten public repositories were created under `flybrainlabs` and their write
permissions verified. The actual component sources and English documents were
uploaded to `main` using normal pushes, and every remote commit was checked.
The dependency revisions and completion status are in
[the release manifest](../release-manifest.json); structured evidence is in
[the acceptance record](../migration-acceptance.json).

A separate clean checkout cloned all ten repositories from GitHub, fetched the
nine exact dependency pins and assembled the project using the published tools.
All 716 owned source files matched the maintained, tested sources byte for byte.
The clean checkout also passed the English documentation, ownership and private
material source checks across 803 files. The final infrastructure revision is the
commit containing this document and its release manifest.

The maintained source workspace is `/workspace/flybrainlabs`; the disposable
build workspace is `/workspace/flybrainlabs-workspace`. Every component records
the current project name, English publication policy and automatic publication
requirement in its development agreement. Retained model, result, browser and
node state was preserved throughout the migration. Official model download bytes
were zero, and this source publication did not redeploy the live website or node.
