# Multi-repository migration acceptance

Date: 2026-10-12. Owner: `flybrainwork`.

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

SSH and GitHub CLI/API both authenticate as `flybrainwork`. Every component origin
uses the dedicated SSH alias. English source policies run on GitHub push/PR events.
Actual publication commits and dependency pins are recorded after each normal
push. No force push or historical repository transfer is used.

This acceptance covers repository assembly, component code and source publication.
It does not claim a fresh live deployment, a new SBF service-market integration,
Android/physical GPU restoration, external biological accuracy or formal payments.
Those gates remain in the English project status document.

### Actual publication status

All ten remote repositories were created. Four initial uploads were accepted and
verified: web, node, miner and explorer. The protocol upload received a GitHub
Internal Server Error. A retry and independent read checks then returned an
account-suspension error; the API confirms HTTP 403. Remaining uploads, including
this infrastructure documentation, are blocked by the platform.

Local component commits and the pending release manifest are complete. The
manifest explicitly marks publication incomplete. It must not be represented as
a remotely available release until account restoration and remaining verified
normal pushes. Fresh remote bootstrap is not claimed as passed during suspension.
