# Results catalog production publication

Verified on 2026-10-23 following the owner's explicit publication request.

## Published feature

The public catalog is https://flybrain.work/results/ at revision
`results-catalog-20261023-r1`. Nine projects have directly accessible English
and Chinese details, nine thumbnails and eighteen project schematics. All
projects remain in preparation with applications open; no training measurements
or progress are invented.

Owner applications are at `/results/applications/`. Administration is at
`/results/admin/`, using the existing configured administrator wallet and
message-based login. Application writes use the existing authenticated community
service and durable SQLite records. No new administrator, password or financial
authorization was introduced.

## Installation and retained state

The reviewed 77-object frontend overlay was applied over the then-current
`mining-continuous-session-20261023-r4` baseline. Prior objects were archived and
verified before transfer; installed hashes match the reviewed artifact. Existing
home, mining, dedicated-wallet and model/atlas assets remain. The complete old
review export was not used to replace the active website.

The five-file community delta was staged in the actual dependency layout. A
consistent backup of the live shared SQLite database was exercised as the
service account: new migration, repeat initialization and prior-code rollback
all passed without changing prior table content. The production switch then
created a fresh consistent backup and applied additive migration v4 through the
service initializer. Migrations v1-v3, prior community records and private
runtime configuration were retained. The compatible health DTO still reports
schemaVersion 3; actual database migration version 4 was checked separately.

The community service was stopped and started once. Wallet, task coordination,
scientific validation, relay and other service process snapshots did not change.
The existing proxy configuration required no change or reload. Recovery indexes,
database copies and credentials remain restricted operational data.

## Public verification

- 111 read-only checks passed, including 48 public object hashes, eight retained
  R4 object hashes, nine project details in both languages, desktop/mobile
  layouts, loaded images, live statistics, login-protected personal/admin
  shells and unknown-project HTTP 404. No unexpected browser errors occurred.
- Four public backend checks verified statistics, unauthenticated denial for
  owner/admin records and rejection of an untrusted Origin.
- The existing public-result API/detail and old query/deep-link routing passed.
  A legitimate signed download returned HTTP 206 and exactly the requested
  16-byte range. The temporary download capability was not recorded.

Public acceptance did not create applicants, authenticate a real extension
wallet, start computation, transfer funds or send notifications. Real
extension-wallet and physical-device confirmation remain separate evidence.
The prior full continuous-mining acceptance backlog is unchanged.

## Recovery and future changes

The original source review was not an authorization to deploy. This specific
publication was authorized by the later owner request. Future changes use their
own applicable authorization and the current live baseline.

For recovery, use the retained changed-object archive and prior community code.
Preserve current SQLite/WAL, application/event records and idempotent receipts.
Do not restore an old database over applications received after publication.
See `RESULTS_CATALOG_OPERATIONS.md` and the machine-readable
`RESULTS_CATALOG_20261023_PUBLICATION.json` for scope and verification.
