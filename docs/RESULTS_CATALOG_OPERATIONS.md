# Results catalog and recruitment operations

This is a source and local-review release. It does not deploy the website,
migrate production, restart services, send notifications or authorize training,
mining, fees or token transfers. Approve an installation plan separately.

## Source ownership and prerequisites

- `node/config/research-projects-v1.json` is the single versioned project source.
  Node uses it for admission and public state; web generators derive pages,
  translation data and the route allowlist from the same file.
- Node owns `tools/project_recruitment.mjs`, migration v4 and community routing.
- SDK owns `web/community-client.mjs` and the post-body session generation guard.
- Web owns native templates, SVG generation, enhancement scripts, runtime routes,
  static export and the scoped website review builder.
- Docs owns English and Chinese handbook explanations. Infra owns assembly pins,
  the local launcher, additive package builder and this operations guide.

Use the pinned infra release manifest, authenticated access to private `web`,
Python 3.11+, Node 22.13+ (the `node:sqlite` API) and the locked npm dependencies.
Rust route and historical API tests also require the locked Rust toolchain.
A complete retained website export is needed for a scoped review; do not replace
it with an incomplete export that omits the existing atlas or mining assets.

From the source repository parent:

```sh
python3 infra/tools/workspace.py verify --repos .
python3 infra/tools/workspace.py assemble --repos . --output ../fbw-workspace
cd ../fbw-workspace
npm ci
npm run build:web
python3 tools/build_results_catalog.py
```

Canonical generated pages are committed in web. During maintenance, regenerate
inside the web checkout with `--catalog ../node/config/research-projects-v1.json`
before assembly; do not leave unreviewed edits in a disposable assembled tree.
The generator does not download models or start training.
Regenerating handbook HTML also requires `tools/requirements-docs.txt`, including
the pinned Markdown 3.8.2. Install it in a task-specific virtual environment,
then run `tools/build_documentation.py` against the canonical handbook sources.

## Build and run local review

Choose fresh output and task-private data directories. The retained baseline is
read-only input. The scoped builder may hardlink unchanged files; never edit a
review export in place. Change canonical sources and produce a fresh export.

```sh
python3 tools/build_results_catalog_release.py \
  --baseline /path/to/retained-complete-export \
  --output /path/to/new-results-review \
  --report /path/to/private-results-build-report.json
node tools/serve_results_catalog.mjs \
  /path/to/new-results-review /path/to/private-local-recruitment-data \
  8099 YOUR_EXISTING_ADMIN_WALLET_PUBLIC_KEY
```

Open `http://127.0.0.1:8099/results/`. Browse descriptions without signing in.
Connect your existing Wallet Standard wallet and sign a message to submit a real
local application. Use `/results/applications/` for your records and
`/results/admin/` for review. A browser wallet must support loopback origins.
No admin key is supplied by the tool. Omitting the administrator argument grants
no account administrative privileges. Only public keys belong on the command
line; never supply a secret key, seed or production runtime configuration.

The launcher binds to loopback, uses a separately marked persistent `auth.db`,
refuses unmarked existing databases and keeps data outside the public export.
Restart with the same local data directory to retain applications. It runs the
actual wallet-signature authentication and community services, with no synthetic
users, default administrators or fault-injection routes. Balance/history and
financial endpoints are deliberately unconfigured locally; the global wallet
may report synchronization unavailable while recruitment login remains usable.
Production keeps its existing wallet service for those endpoints.

The local launcher is a review tool, not the production service. In production,
`tools/social_server.mjs PRIVATE_RUNTIME_CONFIG` remains the community entrypoint
on loopback port 8791, and the existing wallet service handles SIWS endpoints.
Do not pass the private runtime configuration to a static file server.

## Public and protected routes

Public pages are `/results/`, `/results/projects/{slug}/` and
`/results/publications/`. Personal and management pages are
`/results/applications/` and `/results/admin/`; their HTML is a public shell with
no embedded private records and `noindex` metadata. Server authorization protects
all data, independently of the visibility of links or buttons.

The existing `/results/{64hex}/` and `/results/detail/?id=...` keep historical
record identity. Legacy directory query parameters go to the publications view,
with queries preserved. Unknown project slugs return 404. Existing
`/api/results`, result files, signed download expiry, hashes and Range contracts
remain owned by the historical product service.

New API prefix: `/api/community/projects/`.

| Method | Suffix | Access |
| --- | --- | --- |
| GET | `stats` | Public aggregate counts only |
| GET | `me` | Current authenticated wallet |
| POST | `interests` | Set an explicit interest boolean |
| POST | `preferences` | Set or clear one first preference |
| POST | `applications/submit` | Submit one account/project record |
| POST | `applications/{id}/update` | Owner, current revision |
| POST | `applications/{id}/withdraw` | Owner, current revision |
| POST | `applications/{id}/resubmit` | Owner, current revision |
| GET | `admin/applications` | Administrator, paginated filters |
| GET | `admin/applications/{id}` | Administrator, record and event history |
| GET | `admin/summary` | Administrator, project/role/status aggregates |
| POST | `admin/applications/{id}/review` | Administrator, recent login and revision |
| GET | `admin/export` | Administrator, filtered CSV |

Writes require the existing Origin, Bearer and `X-Mining-CSRF` checks. Server-side
sessions determine identity; bodies cannot supply a different subject wallet.
The existing nginx `/api/community/` location already includes the new prefix.
Retain its allowed origins, body limits and rate limits; no wildcard CORS change
is necessary. Only exact public GET `projects/stats` enters the public allowlist.

## Administrator review and count semantics

Sign in using an existing configured `communityAdminWallets` entry. Filter by
project, role and review status; open Details for device/contact information and
revision history. Review supports submitted, reviewing, waitlisted, selected and
rejected. Owners retain withdrawal control. Internal notes remain team-only;
the separate applicant message is visible to the owner. A revision conflict
requires refresh before another review, rather than silently overwriting it.

Exports are UTF-8 CSV with quoting, newline handling and formula-prefix protection.
They contain private contact data; store them with restricted access. A filtered
export above 10,000 records is rejected; narrow the filters. Pagination limits
and offsets apply to list navigation, not to the selected export scope.

Public application counts include submitted, reviewing, waitlisted and selected;
rejected/withdrawn are excluded. Interest and first preference have independent
counts. Cross-project applicant totals deduplicate authenticated wallets, not
verified natural persons. Admin all-time records and role/status breakdowns
include historical records and are distinct from active public counts. Device
information remains self-reported and never becomes measured capacity.

## Additive database migration

Version 4 creates `project_interests`, `project_preferences`,
`project_applications`, `project_application_events` and
`project_request_idempotency`. Versions 1, 2 and 3 retain their exact bytes and
checksums. Startup verifies the migration history and applies v4 in a transaction;
repeated startup is safe, and a checksum mismatch stops startup.

A unique wallet/project constraint preserves one stable business record across
withdrawal and resubmission. Requests bind an actor, request ID, action and payload
hash; exact retries return the original response and conflicting reuse returns
409. Application writes, audit history, preference/interest updates and idempotent
receipts commit together. A failed transaction does not show success. Updates
require an expected revision. Keep the same request ID while delivery is unknown.

Contacts, application bodies, event snapshots and idempotent response bodies are
private database data. Do not copy them to web assets, logs, Git or public build
reports. Backups and exported CSV have the same privacy requirements.

## Prepare an operator-reviewed installation

Build the five-file additive backend package from the pinned assembly:

```sh
python3 tools/build_results_recruitment_delta.py \
  --workspace . --output /path/to/new-private-community-delta
```

The package contains updated `social_community.mjs` and `social_server.mjs`, new
`project_recruitment.mjs`, migration v4 and the catalog JSON. `manifest.json`
records sizes, hashes and retained migration checksums. It requires the complete
existing community install and its locked dependencies; it is not a standalone
service. Never run the v3 upgrade script with this package: its old fixed allowlist
cannot install these additions.

After explicit production approval, an operator should:

1. Inventory the live community path, service identity, runtime-config permissions,
   Node version, database/WAL path, frontend baseline and proxy. Confirm exact
   deployed migration v1-v3 checksums and all module dependencies against pins.
2. Create a consistent private SQLite backup using SQLite's backup API or `VACUUM
   INTO` to a newly created restricted destination. Do not copy only `auth.db`
   while writers continue in WAL mode. If using a stopped-file backup, stop all
   writers sharing that database, checkpoint, preserve DB/WAL and verify ownership.
3. Retain the prior application binaries and private configuration with original
   UID/GID/modes. Unpack and hash-check the additive package into a staging copy
   of the complete existing service layout, including every new module and config.
4. As the actual service account, traverse every parent directory, import the
   staged modules and initialize against a disposable consistent database copy.
   Verify migrations, health, authentication, aggregate counts and rollback. Do
   not print or copy runtime secrets into the package or report.
5. Pause only the community writer for the approved switch, preserve pending
   records and install all five files together. Start the community service and
   verify migration version 4 and expected hash, health and protected endpoints
   before routing requests to it. The existing wallet/mining identity and proxy
   remain unchanged. Do not run SQL separately and then mark it applied by hand.
6. Publish the reviewed frontend after backend verification. Atomically deploy the
   scoped changed-object manifest, including cache-busted scripts/dictionaries,
   thumbnails and nine physical detail pages. Preserve unrelated baseline assets.
7. Verify real public routing, allowed-origin CORS and existing wallet login using
   a designated review account. Do not inject synthetic applications into production.

This task performs none of these production steps.

## Rollback and retained applications

Frontend rollback uses the retained website baseline. Backend rollback restores
previous binaries/configuration, not an old database over newly received records.
The additive tables may remain safely unused by prior code. Validate the old
binary against a copy containing v4 before switching. Preserve current SQLite,
WAL, event history and idempotent receipts; do not drop new tables or decrement
migration metadata. If a data restore becomes necessary, reconcile every record
received after the backup and approve that separate recovery operation first.
No rollback touches model caches, OPFS state, scientific identities or funds.
