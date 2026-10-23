# Results catalog implementation report

Source and isolated local-review release, verified 2026-10-23T10:09:08.384974+00:00. Production remains
unchanged. The feature branch is `feat/results-catalog-20261023`.

## 1. Implemented behavior

`/results/` now renders a single-column directory of nine projects in stable order.
It has no former result filter form. Nine directly addressable English/Chinese
details contain full goals, foundations, methods, milestones, evaluation definitions,
participation and references. Nine original local SVG thumbnails and eighteen
project-specific schematics illustrate the work without fabricated measurements.

Applications use authenticated wallet accounts and real SQLite persistence.
Owners can view, edit, withdraw and resubmit the same stable account/project
record. Lost receipts retain their original idempotent request. Administrators
can filter, inspect, review, keep internal notes, read history and export CSV.
Public statistics are real aggregates; unavailable values never become zeros.

## 2. Canonical repositories and key files

| Repository | Published commit | Task files changed |
| --- | --- | --- |
| web | `f850c8de81da2fee1b61be2919f3a9a9d0cf590d` | 56 |
| node | `2375da1a40b8f56da15c37f857de6f35feddaadb` | 12 |
| sdk | `012697fcec2a88b006d5dd69435162c4fd530897` | 3 |
| docs | `b61f94a515eaf81679ea822ac45a95447404651e` | 2 |

- Node: `config/research-projects-v1.json`, `config/social-community-v4.sql`,
  `tools/project_recruitment.mjs`, `tools/social_community.mjs`,
  `tools/social_server.mjs` and HTTP/historical compatibility acceptance tests.
- SDK: `web/community-client.mjs`, `tests/community_session_guard.test.mjs`.
- Web: `tools/build_results_catalog.py`, `tools/results_catalog_diagrams.py`,
  `tools/build_results_catalog_release.py`, `src/site.rs`, `tools/export_static.py`,
  `web/results-catalog.mjs`, `web/results-catalog.css`, generated pages/assets and
  `tests/results_catalog_browser.py`.
- Docs: `docs/handbook/results.md` and `docs/handbook/zh/results.md`.
- Infra: the local launcher, additive package builder, this report, acceptance
  record, runbook, component ownership map and verified release pins.

This checkout uses `component.json` ownership maps; it has no separate maintained
`import-manifest.json`. The assembler checks unique ownership and pinned commits.
The retained website baseline is read-only input, not canonical source.

## 3. Routes and APIs

New detail namespace: `/results/projects/{slug}/`. Personal and management shells:
`/results/applications/` and `/results/admin/`, with noindex metadata. Historical
research remains at `/results/publications/`, `/results/{64hex}/` and
`/results/detail/?id=...`. Old directory query links retain their evidence
filters on the publications view. Unknown project slugs return 404.

New endpoints under `/api/community/projects/` provide public `stats`, protected
`me`, interest/preference writes, application submit/update/withdraw/resubmit,
and admin list/detail/summary/review/export. The runbook lists methods and roles.
The existing nginx prefix already covers these routes; CORS is not widened.
`/api/results`, record details and authorized file delivery preserve their contracts.

## 4. Database upgrade and rollback

Additive migration v4 introduces interests, first preferences, applications,
application events and request-idempotency tables. Migration versions 1-3 retain
their original bytes and hashes. Account/project uniqueness prevents duplicate
business records. Actor/action/payload-bound request IDs and transactional
receipts make retries safe; revisions detect conflicting edits and reviews.

Back up SQLite consistently with its backup API or a coordinated writer stop and
WAL checkpoint. Stage all five backend files together, verify their hashes and
module imports in the complete layout, then initialize against an isolated data
copy as the service identity. The runbook specifies the later approved switch.
Rollback restores prior binaries/frontend while retaining current applications,
events and idempotent receipts. Do not drop tables or restore an old database over
newly received records. No production migration was executed for this release.

## 5. Scientific and content state

All nine directions initialize as **Training preparation / Applications open**.
All milestones are planned and all forty measured metric values are null.
The pages distinguish existing connectome/response/reproduction foundations from
future behavioral interfaces and task-specific evidence. P07 requires a versioned
learning mechanism; P08 identifies the virtual body and lower control layer;
P09 separates paired A/B evidence, stimulation cost and scoped non-target changes.
No application count, progress percentage, training batch or capability is invented.

New material is complete in English and Chinese. The existing six-language menu,
English default and saved language preference remain; new content falls back to
English in the other four locales.

## 6. Actual verification

- Browser: 232 checks, 44 page/language/width cases and 36 private synthetic-data
  screenshots. Directory widths: 1440, 768, 390 and 360. Every project detail was
  checked in both languages at desktop/mobile widths. Real service-backed UI
  flows cover edit/withdraw/resubmit, interrupted receipt/retry, wallet switching,
  protected admin review/export and unavailable statistics. A separate 20-check
  workflow console review found only the eight expected injected/denied network
  errors, with no unexpected JavaScript errors.
- Node/SDK: six tests covering actual Ed25519 login, CSRF/Origin, ownership,
  idempotency/conflict, concurrent requests, revisions/history, CSV quoting and
  formula safety, transaction rollback, repeated migration and restart persistence.
  Guard tests cover JSON, error and Blob consumption plus a renewed same-wallet login.
- Existing social regressions: 141 checks. Community syntax and TypeScript pass.
- Native project routing: two tests. Existing product API suite: ten tests.
  The separately invoked retained-package test also passes for real public HTTP
  list/detail, 206 Range recovery, invalid signatures, expiry, corruption and recovery.
- Static export: all eight tests pass. Complete review validation retains 11,751
  atlas types, the OAuth bridge and 92,787 files. Handbook checks validate 26
  guides, 52 Markdown downloads, stable anchors and 183 search sections per locale.
- Workspace safety: five tests. The non-fixture local launcher passes actual
  signature, local persistence, administrator, Origin and private-data checks.
  The five-file backend package passes hash checks and staged module import.
- Source checks reject secret material and verify ownership/English maintenance
  documentation. All ten original worktree heads and dirty statuses are retained.
  The four component source-policy CI runs are bound to the commits in the JSON
  acceptance record. Containing infra CI is verified after its publication.

Representative commands, from the pinned assembled workspace:

```sh
npm run build:web
node --test tests/project_recruitment.mjs tests/community_session_guard.test.mjs
node --test tests/social_community.mjs tests/social_daily_invites.mjs tests/social_github.mjs
npm run lint:community
npm run typecheck:community
cargo test --offline --locked -p flypow --lib site::research_project_tests
cargo test --offline --locked --test product_api
FLYPOW_PUBLIC_PACKAGE=/path/to/retained-public-package cargo test --offline --locked --test product_api full_public_package_download_access_and_damage_boundaries -- --ignored
TMPDIR=/path/to/large-task-temp python3 -B -m unittest discover -s tests -p test_static_export.py -v
python3 tools/validate_static_release.py /path/to/review-export
python3 tools/check_documentation.py /path/to/review-export
python3 tests/results_catalog_browser.py --workspace . --release /path/to/review-export --report /path/to/private-browser-report.json
node tests/results_catalog_local.mjs /path/to/review-export
```

Browser checks require Selenium, Chromium and chromedriver. Complete static export
regression also requires retained WASM/topology resources and enough temporary
disk space. These resources were reused locally, not downloaded or executed.

## 7. Startup and administrator review

See `docs/RESULTS_CATALOG_OPERATIONS.md` for reproducible checkout, build, launcher,
API and operator instructions. The local launcher serves real unseeded persistent
applications on loopback and rejects existing unmarked databases. Supply an
existing administrator public key explicitly; no default admin or password is
created. Sign in with a Wallet Standard message and use `/results/admin/` to
review, filter, read history or export. Contacts remain in private SQLite/CSV.
The local identity service does not configure balance synchronization or financial
handlers. Production continues to use its existing wallet and community services.

## 8. Deployment readiness and boundaries

The review is a complete retained export with 77 scoped changed objects.
The additive backend archive has SHA-256 `43fc7eefdcc8dca6c7738d7dc34a06c8c3d2602eada818cbc014b46a6da38569` and contains
five source/config files, with no database or private runtime configuration.
Pinned sources, migration and rollback instructions are ready for operator review.

Website deployment, production migration/restart, real extension-wallet approval
and physical-device acceptance have not been performed. Production installation
requires a separately approved switch and service-account/configuration checks.
There are no remaining source implementation blockers in this task's scope.
No models were downloaded, no training/mining was launched, no transactions or
notifications were sent, and no main branch was merged.
