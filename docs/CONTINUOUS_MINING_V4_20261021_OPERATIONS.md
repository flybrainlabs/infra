# Continuous V4 operations and release gates

## Current package boundary

Source publication and inactive packages do not activate the node, expand FBW
or signer authorization, merge main, enable V5, issue tokens or broadcast public
financial transactions. This release keeps the current V4 protocol and frozen
scientific identity. On October 21 the owner authorized privileged maintenance
of the original node. The matching service is now installed and healthy. Two
bounded operator expiry transactions finalized during authenticated demand
acceptance; no miner transaction or new reward allocation was made. See
`CONTINUOUS_MINING_V4_ORIGINAL_NODE_20261021.json` for the deployment boundary.

Use `release-manifest.json` for final component revisions. Starting revisions
are recorded in the accompanying acceptance JSON. The website candidate is
`continuous-mining-v4-20261021-r15d`; validate its build report before deployment.

## Build and inspect

From the assembled pinned workspace:

```sh
node tools/build_browser.mjs
node tools/factory_pool_inspect_v4.mjs /etc/flypow/factory-pool-v4-runtime.json
python3 tools/prepare_factory_pool_v4.py --workspace . --output /path/to/fresh-inactive-package
```

The inspect command opens no signer, performs no migration, makes no new
signature and allocates no budget. It reads the existing schema and verified
chain state. Its bounded output reports truncation. Missing schema/access is a
preflight failure, not a reason to initialize a fresh database.

The package builder follows source dependencies and includes the additive SQL,
calibration tool, inactive example, unit and operating instructions. It includes
no model, database, private runtime, wallet, key or activation step. The full
model and native binary must be the previously approved versions; do not replace
or redownload retained state during source maintenance.

## Deployment sequence and retained recovery procedure

The October 21 deployment backed up the original unit, private configuration,
SQLite and PostgreSQL state, journals, content and partial uploads before the
service switch. An initial candidate directory permission failure occurred
before any migration; the unchanged original service was restored, the new
directory was corrected, and imports passed before the successful switch.
The migration retained the original job identities, raw signed packets and
scientific inventory. The calibration tool hash was explicitly reviewed for
exclusive locking, frozen checkpoints, kernel timeout and cooperative yielding;
scientific rules and finite reward/signer scopes were preserved.

The following sequence also applies to subsequent maintenance:

1. Record existing release hashes, original SQLite and PostgreSQL schema/data,
   WAL, content roots, upload grants, model cache, signed packets and pending
   rights. Use the existing backup procedure; do not copy secrets into reports.
2. Verify the package hashes and authorized remote source revisions. Populate
   the inactive example from existing private configuration. Recheck actual
   reward balance, current allocations/unpaid rights and original signer/fee
   allowances without expanding any authorization.
3. Preserve active jobs and pause future production while switching the service
   executable. Apply the additive `config/factory-pool-v4.sql` with the existing
   migration lock. The isolated migration was exercised twice. Retain all old
   tables, rows, signed payloads and SQLite files.
4. Run read-only inspection. Start the matching node with the existing authorized
   service manager, identity and paths. The optional example unit is
   `deploy/target-v2/flybrainlabs-factory-pool-v4.service`; review its resource
   limits against the original host before installation. It is not installed by
   the package builder.
5. Check `/api/task-factory/v4/health`: fresh discovery, actual open inventory,
   database/content/native readiness, queue age, estimated replay workload,
   quarantined history, storage growth and authorization state. Required
   capabilities include `continuous-v4-20261021`, `signed-catalog-history-v4`
   and `resumable-upload-v4`.
6. Exercise controlled original-record recovery and a finite authorized Devnet
   personal-RPC workflow through final reward balance. Complete T22/T36 and the
   outstanding matrix items before declaring acceptance. Then deploy the
   matching website through the existing static release procedure.

The service entry point is:

```sh
node --max-old-space-size=192 tools/factory_pool_service_v4.mjs /etc/flypow/factory-pool-v4-runtime.json
```

Stop/restart through the installed service manager using its existing authorized
maintenance entry. The process handles SIGTERM/SIGINT. Do not start a second
uncoordinated legacy producer over the same runtime. A future maintenance
permission failure must be handled through the existing approved administrator
entry.

## Configuration and observation

`deploy/target-v2/factory-pool-v4.example.json` includes open-task watermarks,
demand TTL, native serialization, replay/admission estimates, finite storage,
upload reservation expiry and partial retention. Keep `enabled=false` until the
operator's existing activation conditions are met. Scientific generation also
needs the existing approved policy, inventory, tool hash and finite supply
ceiling. No automatic token minting or reward expansion is introduced.

Background reconciliation runs about every 15 seconds; discovery about every
5 seconds. Unknown packets remain immutable/quarantined and observable.
Calibration/catalog, keeper, replay and payment are independent lanes. A shared
native lane is limited to one replay process and cooperative calibration.
HTTP liveness is separate from `businessReady`; discovery failures preserve the
last success time and report unready until resynchronized. Bootstrap time
estimates must be replaced by measured host-specific bounds through the
existing reviewed configuration process.

For a read-only 24–72 hour observation after the live gates are met:

```sh
python3 tools/continuous_mining_soak_v4.py \
  --health https://approved-node.example/api/task-factory/v4/health \
  --hours 24 --interval 30 --output /path/to/fresh-observation \
  --stop-file /path/to/stop-observation
```

The observer never starts mining or signs. It records JSONL health/process
samples and the actual observed duration. It can stop by signal or stop file.
Health observations alone do not establish browser work or rewards. Collect a
parallel browser execution/save/outbox/settlement timeline and actual native
CPU/RAM/disk measurements. No long-duration run is claimed by this delivery.

## Rollback and recovery

Stop new browser dispatch and future catalog production first. Preserve all
OPFS candidate directories/index journals, salts, transaction journals, upload
partials, immutable content, DB/WAL and calibration checkpoints. Allow already
broadcast packets to reconcile under their original operation IDs.

Do not drop additive columns or roll back to a writer that cannot understand the
new upload expiry/history records. Prefer a forward repair with the compatible
reader/reconciler retained. If a website revert is necessary, keep access to a
compatible original-result recovery build. Wallet refresh requires a new unlock
and explicit session consent; it never recreates signing authority from disk.
An old unsigned/unknown receipt is not permission to make a replacement payment.

## Remaining acceptance gates

The original node completed actual cold calibration competing with historical
complete-model replay under one native process, a 100% single-core CPU quota
and 512 MiB memory cap. The measured replay wait was 14.7 seconds. Aggregate RSS
peaked at 373,132 KiB; cgroup memory including file cache peaked at 488,947,712
bytes. New submitted-candidate competition still needs combined acceptance.

A read-only 24-hour backend observer is running. Its samples establish only
actual backend observation duration and readiness; browser/native candidate and
reward timelines remain separate evidence.

The October 22 continuation rechecked the installed 39-file node package and
33 website baseline paths without reinstalling or transferring the website.
At 05:53 UTC, 1,705 backend samples covered 51,124 seconds: no sampled HTTP
failures, 28 discovery-related unready samples and at most four consecutive
unready samples. The last sample was ready. This is still short of 24 hours and
does not establish mining continuity. See
`CONTINUOUS_MINING_V4_20261022_RECHECK.json` for the observation times and limits.

`CONTINUOUS_MINING_V4_STORAGE_BROWSER_20261022.json` records actual Chromium
termination at six OPFS save/handoff boundaries, recovery from the retained
profile and shared candidate locking between two real tabs. Its scientific
events and submission service are fixtures. Scarce-funds wallet concurrency,
real candidate verification and reward acceptance remain separate gates.

The complete qualified-candidate sequence “save A, compute B while A uploads or
settles” has not yet been observed with the real full model and native verifier
in one end-to-end run. Real personal RPC/payment/reward acceptance, actual
new-candidate competition, physical mobile devices and the full mining long
soak remain unaccepted. See every T01–T36 row in the evidence JSON. Keep the
matching website release gated until these results exist.

## Live personal RPC and source access

The October 22 network recheck passed the owner's personal Helius key against
the deployed Devnet genesis, finalized slot, executable program and factory
account owner. Real Chromium also verified the key through the published UI
and revalidated it after refreshing the same tab. These requests reached the
provider; the earlier proxy CONNECT 405 is a historical failure. No proxy bypass,
shared RPC fallback, wallet unlock or financial transaction was used.

The assembled workspace includes a repeatable read-only browser check:

```sh
python3 tests/personal_rpc_live_v4_browser.py \
  --workspace /path/to/assembled-workspace \
  --profile /private/path/to/preserved-acceptance-profile \
  --key-file /private/path/to/helius-api-key \
  --report /private/path/to/browser-report.json
```

The private key file must have mode `0600`. The browser honors the configured
HTTPS proxy and the key stays in its default tab storage. Reports export public
states and RPC method names only. They exclude browser logs, screenshots,
credentials and provider URLs. The test also probes browser CORS and bounded
Range access for all three frozen official sources.

For model preparation evidence, add `--prepare-model` with a preserved test
profile. This invokes the existing prepare-only handler, verifies the frozen
model identity and records whether the model was built or restored. It creates
no wallet and never starts mining. This narrower model preparation check does
not establish the single-Start mining workflow, a qualified candidate,
submission, settlement, reward payment or a mining soak. See
`CONTINUOUS_MINING_V4_NETWORK_20261022.json` for actual results and timestamps.
