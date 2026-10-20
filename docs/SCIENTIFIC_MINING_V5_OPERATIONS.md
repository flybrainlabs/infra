# Scientific mining V5 operations

V5 is a separate round family. Repository publication and a website build do not
activate its service, allocate rewards, upgrade the public program or issue FBW.

## Before installation

Use only the previously authorized original node. Inspect the active service,
runtime permissions, program upgrade authority, model hashes, PostgreSQL state,
signed transaction journal and funded V4 catalogs through the approved maintenance
route. Do not print private runtime configuration or key files. Do not elevate
from an SSH account that lacks access.

Retain a complete rollback copy of source, private configuration and service
definitions. Preserve all databases/WAL, model files, archives, scientific
identities, cached browser data and accepted unpaid rewards. Do not rewrite or
repurpose existing V4 tasks to represent V5 experiments.

## Build and acceptance

In an assembled workspace with pinned dependencies:

```sh
cargo test --locked -p flypow-sim-core -p flybrainlabs-mining-v3 --lib
cargo build --locked --release -p flypow-target-protocol --bin exact_trial
cargo build --locked --release -p flypow-sim-core --target wasm32-unknown-unknown
cargo-build-sbf --manifest-path programs/flypow-economy-v2/Cargo.toml
node tools/build_browser.mjs
node tests/session_abi.mjs
node tests/scientific_round_v5_sbf.mjs
```

The complete service recovery test additionally requires the dedicated local
PostgreSQL acceptance socket via `FLYBRAIN_POOL_TEST_SOCKET`. The test refuses
ordinary database endpoints, creates its own database, and uses actual SBF and
native fixture computation. This does not constitute a public Devnet test.
Reject any SBF build containing stack-frame errors even when its tool exits zero.

## Private service configuration

Run `node tools/scientific_service_v5.mjs --config PRIVATE_CONFIG` as the approved
service owner. Keep this JSON outside source and public web roots. Required
fields are:

- `databaseUrl`, `rpcUrl`, two `verifierKeyFiles`, `binary`, `modelDir`,
  `contentDir`, and `outputDir`.
- A V5 `deployment` containing the exact `programId`, `genesisHash`, `policyHash`,
  existing `mint`, `cluster`, `enabled` flag and configured round addresses.
- `rounds`, the finite list of prospectively funded and registered V5 rounds.
- Explicit finite `maxTransactionsPerSigner` and `maxFeeLamportsPerSigner`.
- `allowedOrigins`, containing the authorized website origin; optional loopback
  `port`, default 8795. Bind to loopback behind the original authorized proxy.

The service uses isolated `science-v5:` scopes in the durable queue and signed
packet journal and new `scientific_v5` verification/upload tables. Transaction
allowances count previous signed packets for the same payer. Unknown expired
packets require reconciliation; the service does not silently sign replacement
debits. Two verifier keys here are disclosed as one operator.

Publish only `/api/science/v5/status` and content routes through the original
proxy. PUT uploads bind chain, program, round, claim, content hash and size to the
claim wallet's signature. Enforce the frozen aggregate byte allowance, exact
website origin, request bounds and private filesystem ownership. Do not expose
the native JSON-lines process or a shared mining RPC endpoint to browsers.

## Funding and opening rounds

Review and content-address every question and audit plan before registration.
Verify authority, available project pool atoms, the existing cumulative financial
authorization and all earlier reserved/accepted amounts. A new round reserves ten
equal places from available atoms. It cannot increase a prior authorization.
Release old unused allocations only under their own frozen closure rules; never
release accepted unpaid balances. Unused V5 balances are refundable only after
all its queues are resolved and closure is eligible.

Schedule enough time for mining discovery, the 128-slot challenge registration
window, evidence publication, serialized verification and chain finality. A
future slot hash has proposer bias; deployments needing an unbiased beacon need
a separately registered randomness mechanism. Do not claim statistical robustness
from the two-background fixture or biological accuracy from numeric equivalence.

Only enable the public V5 deployment after the installed program, node and funded
questions match the reviewed hashes. Keep the existing mint and user-owned RPC
configuration. The dedicated mining wallet requires a separate scoped V5
automatic-payment consent, preserves its mnemonic/address, and permits no generic
transfer. Pending rewards are excluded from header token balances.

## Final acceptance and rollback

Measure cold/warm sparse and dense propagation, queue delay, upload, peak memory,
ten-candidate throughput and finalized payment separately on the original node.
Exercise a real personal-RPC browser and wallet through search, input commitment,
fresh challenge, evidence, verified contribution, payment and an approved
successor. Exercise restart, unavailable evidence, deadline and low-balance cases.

Keep the website disabled or show the actual waiting reason when any gate is
missing. Restoring the previous website/source does not delete V5 accounts or
entitlements. If a V5 round has accepted work, retain a compatible settlement
service and the original signed packets until every entitlement is reconciled.
