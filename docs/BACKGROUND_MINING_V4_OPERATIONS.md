# V4 background mining and task supply

## Execution lifecycle

The background UI correction retains the document that owns the model Workers
and unlocked dedicated wallet. A V4 visibility change does not request a pause.
Returning to the foreground coalesces a fresh contract read. A late response
cannot revoke an explicit Pause or revive a replaced session.

During an explicitly active V4 mining or preparation session, following a link
to another site page opens that page in another tab. Mining subviews stay in the
existing document. Normal navigation resumes after participation stops. Model
and result caches, wallet storage keys and frozen contract encodings are retained.

The original mining tab and browser must remain open. Browser suspension,
discarding a tab, device sleep, process termination and navigation through the
address bar remain execution boundaries. This release does not install a native
background service or promise computation after browser exit. Existing wallet,
balance, quota, task deadline and input lease checks still apply.

## Task visibility and finite authorization

Both the mining and compute-tasks pages sample the configured pool health
endpoint without credentials. They separately show funded tasks remaining, open
claim windows, service readiness and exhausted new-reward authorization.
Discovery older than 60 seconds is rejected. A failed request or locally stale
sample hides current inventory rather than presenting it as zero.

This display is informational. Catalog signatures, finalized contract state,
wallet consent and existing admission checks authorize computation and payments.
Health output never grants signing authority or replaces those checks.

At the 2026-10-23 06:19 UTC inspection, the pool reported 30 funded scheduled or
active tasks, zero open claim windows and zero remaining new reward allocation.
The original automatic-task authorization totals 6,400 FBW. Validator collateral
sponsorship does not replenish mining rewards. Generating more rewarded tasks
requires the next explicit finite authorization and a fresh audit of funds,
reservations and unpaid rights. Idle zero-window policy is retained.

## Build and deployment

`tools/build_background_mining_release_v4.py` applies the small correction to the
retained complete pre-outbox V4 website. It checks every expected lifecycle
replacement, versions changed imports and independently replaces changed files.
Frozen data, wallet bundle, cache code, home animation and language preferences
are retained. It fails closed on an unexpected baseline.

The broader continuous outbox client remains gated by real mining acceptance.
The future continuous-client builder also includes the new lifecycle and supply
modules. Rebuild it over the latest deployed website instead of restoring an old
candidate over this correction.

Before deployment, run the coordinator regression, supply validation tests and
`tests/background_mining_v4_browser.py`. That browser test uses a real CPU Worker,
isolated health replies and blocked external writes. It proves page lifecycle
and UI behavior, not complete-model mining or rewards. Deployment requires the
exact build report validation, remote baseline checksums and a verified backup.
Rollback restores existing files from that backup and removes only the listed
new paths; never reset profiles, OPFS or model caches.

Real personal-RPC mining, qualified public candidates, background settlement,
finalized rewards and the 24–72 hour full mining soak remain separate gates.

## Wallet entry and catalog continuation correction

The owner subsequently requested the recovery phrase first and password entry
to unlock and enable automatic payments without a separate enable button.
`tools/build_wallet_entry_release_v4.py` builds this correction over the first
background UI release. Creating a wallet shows its words immediately, retains
offline backup verification and encrypts the existing local wallet format.

Typing a valid password attempts local decryption after a brief typing delay.
Correct decryption records the unlocked session's payment scope in memory.
The existing policy activates only after personal RPC, contract identity and
balance checks. Password entry is disclosed as enabling payments for the checked
mining scope; the fee explanation and Lock action remain visible. It does not
start computation, send an on-chain transaction by itself, widen the contract
allowlist or authorize additional task rewards. Reload requires another unlock.
An incorrect password cannot arm payments. Leaving the password form or locking
the wallet cancels a pending unlock. No phrase or password enters the server.

The correction also treats an ended V4 selected catalog as a pool wait, selects
alternatives that require expiry or finalization, and permits guarded continuation
for all existing recovery operations. The unchanged SDK checks current intent,
wallet identity and session generation before a recovery send. Read-only pool
health still does not authorize work. The unfunded future reward boundary remains.

The wallet browser test uses real mnemonic generation, encryption, decryption
and storage with explicit RPC, login and balance fixtures. Its activation result
does not prove a real funded wallet, public candidate or finalized reward.


## Continuous session correction

The current website revision is `mining-continuous-session-20261023-r4`.
The intermediate active-flow R3 build was tested locally and included in R4;
it was not deployed as a separate public revision. R4 overlays the reviewed R2
wallet release and retains its encrypted wallet storage and frozen SDK bundle.

There is no mining time limit, candidate-count stop or stop-after-round mode.
Old minute/count/round options do not stop the V4 runner. Manual Pause, Stop,
wallet Lock and identity checks remain authoritative. A paused or replaced
session cannot be revived by a late network response. Insufficient SOL waits
for a top-up; the next transaction must still cover its network fee and any
required storage deposit. No fee cap or contract allowlist is bypassed.

Temporary network, model or lease-renewal failures preserve mining intent.
A lost assignment cancels that execution at a safe boundary and can reacquire
work without discarding saved backgrounds. Actual browser storage exhaustion
waits for capacity; no saved artifact is deleted to manufacture more space.
These waiting states do not claim that a CPU model is still running.

The submissions display distinguishes completed model runs, local task
qualification, actual chain verification confirmations and confirmed payment.
The historical settlement rule still requires two trusted chain votes;
scientific fleet agreement still requires three matching full-model reports.
The two counts are separate from the task's required model backgrounds.

History lists opened tasks only. Unopened calibrated inventory is shown in the
separate supply section, rather than as predefined rounds. The frozen current
contract permits up to eight queued candidates and one winner per attempt.
Existing task descriptors, reward amounts, deadlines and historical records
remain unchanged. History reads run independently of recovery so that a long
history refresh cannot delay the next eligible task.

`tools/build_continuous_session_release_v4.py` builds this scoped correction.
The browser suite covers the actual shipped modules, hidden-tab computation
with a real fixture CPU Worker, the removed settings, plain result rendering,
and a real lease timer recovering a temporary error. It uses fixture health
and blocks chain writes. It does not prove full-model continuous mining.

## Internal RPC relay recovery

An observation of an actual pending replay on 2026-10-23 captured upstream
`429 Too Many Requests` and `Connection rate limits exceeded`. Separate
complete-model diagnostic replays passed; those diagnostic reports alone did
not establish live fleet agreement, settlement or reward payment.

The authenticated internal relay now serializes upstream reads with an 800 ms
request gap, a finite queue and a finite upstream timeout. Identical concurrent
fresh reads share one in-flight finalized RPC operation and receive their own
JSON-RPC request IDs. A later account admission performs a new chain read;
completed account responses are not cached for fresh checks. Rate-limit
responses start the existing bounded cooldown. Signing methods remain denied
at this read-only relay, and no personal miner RPC key is installed on it.

Only the relay service is moved to the reviewed bundle. Existing scientific
worker identities, their collateral, coordinator runtime, settlement signers,
database/WAL and content archives are retained. Save the old relay unit and
runtime file privately before switching; verify the service user's access,
module syntax, Devnet genesis, authentication and rejected signing routes.
A failed post-start health probe must be reconciled without repeating a
completed restart. Restore the saved unit for rollback; do not alter wallets
or unresolved financial records.


## New public candidate and reward evidence

After relay recovery, an existing owner-submitted candidate with prefix
`3e0541b51413` completed scientific agreement from three distinct configured
identities, two frozen chain settlement votes, and a finalized 200 FBW Devnet
payment. The finalized transaction token-balance delta equals the task reward;
the next task is open. Full report hashes, signatures and the chain receipt
are bound in the acceptance record. No operator miner wallet was unlocked and
no additional reward authorization or collateral funding was used.

This verifies a real public candidate, distributed replay and reward payment.
It does not establish a controlled single-Start personal-RPC browser run, the
full outbox client, simultaneous saved-A/compute-B acceptance, or the 24–72 hour
full mining soak. Those gates retain their separate status.
