# Validation participants and complete replay

FBW users participate in scientific validation under the admission and evidence
policy of each task. Membership is an operational configuration rather than a
fixed product-wide count. Each participant runs a complete-model worker on a
separate host and signs its own replay reports.

## Scientific validation and settlement

`factory_validator_worker_v4.mjs` reads finalized task and submission accounts,
checks the registered model and content hashes, and executes every required
background through the native replay engine. A signed attestation binds the
worker identity, request nonce, task, submission, complete report and report hash.

`FactoryValidatorFleetV4` checks the configured participant identities, distinct
keys, signatures, nonce, report scope and freshness. It groups numerical results
by complete output and metrics, excluding host timing. Only a group meeting the
configured minimum can proceed. Divergence, missing evidence and infrastructure
faults retain the candidate for reconciliation rather than producing a fabricated
scientific rejection.

The task coordinator stores the signed participant evidence in its durable replay
report. Existing settlement accounts, admitted settlement keys, signature domains,
transaction allowances and funded budgets retain their frozen rules. Adding a
validation participant does not rewrite historical on-chain membership or issue
assets. Worker attestation keys and settlement signing roles have separate duties.

## Package and configure a participant

Assemble the pinned release, install its locked dependencies, and build the worker:

```sh
node tools/build_validator_worker_v4.mjs --workspace /srv/flybrain-workspace --output /var/tmp/validator-worker.mjs
```

The package contains executable source. Model files, Node.js, runtime configuration
and keys are supplied through their private operational channels. Validate the
artifact hash, full graph and parameter-file hashes, native capabilities and the
complete import graph under the actual service account before activation.

Create a new identity outside repositories and website exports:

```sh
umask 077
node /var/tmp/validator-worker.mjs --initialize-key /etc/flypow/private/participant.key
```

The initializer refuses to replace an existing key and returns only its public
key. Retain the private identity across restarts and rollback.

The worker configuration contains `id`, `identityFile`, `tokenFile`, `modelDir`,
`binary`, `outputDir`, `relayUrl`, `port` and the approved deployment `trust`
object. Start the service with `--worker PRIVATE_CONFIG.json`. The identity and
output directory belong to its dedicated service account. Private configuration
must preserve its restrictive owner, group and mode during backup and restore.
Code and model parent directories must permit that account to traverse them.

The relay configuration contains `tokenFile`, `contentDir`, `rpcUpstream` and its
loopback `port`. Start it with `--relay PRIVATE_CONFIG.json`. It streams only
content-addressed artifacts and permits an explicit read-only RPC method set.
Keep the upstream RPC credential private to the relay.

## Authenticated transport

Worker and relay listeners bind to loopback. Use authenticated SSH forwarding
between hosts, pinned host keys and a dedicated forwarding identity. Limit its
authorized key to the required loopback destinations and listeners. Expose no
worker or content listener directly to the public network.

The coordinator fleet configuration uses schema `flybrain-validator-fleet-v1`,
`tokenFile`, `minimumAttestations` and a `members` array. Each member supplies a
distinct `id`, Ed25519 public key and loopback forwarding URL. Choose the minimum
against the task's evidence and availability requirements. The service loads the
fleet through the private `validationFleetFile` runtime setting.

## Activation and recovery

Before changing the coordinator, retain its original unit and runtime file with
their ownership and permissions. Stage a new release beside the running one and
resolve the complete module graph in the deployed directory layout. Verify worker
health, matching model identities, authenticated chain reads and signed native
replay on every configured host.

Enable each worker, relay and SSH transport at boot. Retire the superseded serial
verification service so a reboot cannot duplicate a participant's work. Stop the
coordinator gracefully, change only its reviewed release and fleet setting, and
restart. Preserve the existing task, supply, calibration and financial allowances.
On activation failure, restore the retained unit and private configuration with
their original ownership and modes before restarting the preceding service.

Read business readiness together with fleet readiness. Restart a worker and its
transport separately; confirm that the same public identity returns and the
coordinator recovers. Read-only RPC must reject transaction submission, and worker
health must reject unauthenticated requests.

## Validation commands and evidence

```sh
node tests/factory_validator_fleet_v4.mjs
node tests/factory_validator_quorum_v4.mjs
node tests/factory_pool_capacity_v4.mjs
```

The fleet checks cover signed agreement, disagreement, tampering, nonce binding,
duplicate identity rejection and loopback destinations. Native integrity checks
generate and verify complete frozen-model backgrounds on the actual hosts.
Their scope is separate from replay of a newly revealed public candidate or a
finalized reward transaction. The dated acceptance record identifies which
evidence was obtained without creating new funding or public financial actions.

The public introduction describes voluntary user participation, the declared task
policy, complete-model replay and signed evidence. Keep deployment inventories,
host addresses, access keys, authentication tokens and private archives outside
public builds. Public product copy does not prescribe the participant count.

## Deadline and slow-member handling

The coordinator derives the replay collection budget from finalized chain time
and the task verification deadline, retaining the configured confirmation margin
for the existing settlement path. The fleet applies the shorter of this budget
and its worker request timeout. The optional private `requestTimeoutMs` setting
is a positive integer at most 600000; omission retains the existing upper bound.
No funding, task descriptor, participant identity or signature domain changes.

A collection may complete when the agreed signed group meets its configured
minimum and no unfinished group can overtake it. For the current three-of-four
policy this allows three matching reports to proceed while one member is slow.
For a minority threshold the collector waits when a larger result remains
possible. An unattainable quorum produces a retryable infrastructure outcome;
missing or mismatching evidence is not a fabricated scientific rejection.

Completion or expiry cancels outstanding HTTP waits. A remote native process may
still finish and persist its signed report. A busy member can reject another
request; it never supplies a duplicate vote. Late responses cannot modify the
returned report. Existing accepted evidence remains shared across the frozen
settlement signers, whose chain eligibility and deadline are rechecked before
financial submission. Node counts do not imply multiplied candidate throughput.

The quorum test uses loopback HTTP and fixture science. The
capacity tests retain finite budget and shared native-lane checks. PostgreSQL
recovery tests must use a newly isolated acceptance socket, never the production
database. Native self-checks and these suites are separate from real candidate,
finalized reward and continuous-mining acceptance.
