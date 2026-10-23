# Reference-based SVG artwork and static delivery

## Scope

The owner requested native SVG illustrations based on the reviewed Imagegen
bitmap compositions, prioritizing page loading speed. Nine project thumbnails
are redrawn as authored vector geometry. The generated bitmap originals remain
private reference material. Raster artwork is not a dependency of this release.

The frontend baseline is `results-catalog-20261023-r1`. Project identities,
translations, training status, the eighteen inline technical diagrams, durable
applications, administrator authentication and historical results stay intact.
The update does not migrate the database or restart any service.

## Artwork

`web/tools/build_project_artwork.py` contains the native paths and geometry.
`web/web/data/project-artwork-v1.json` records composition descriptions, reference
image hashes and SVG hashes. Each drawing uses a small set of gradients for the
charcoal, silver and ivory reference palette. There are no embedded images,
external resources, fonts, filters, animation or scripts in the SVGs.

Content-addressed SVG URLs permit one-year immutable caching without stale-image
replacement. Each image has intrinsic 320 by 200 dimensions. The first image has
high fetch priority; the remaining eight use native lazy loading. The vector
geometry scales across mobile and desktop without multiple raster resolutions.

Nine SVGs total **27,254 original bytes**, **9,037 gzip bytes** or **7,982 Brotli
bytes**. The public Brotli responses measured 8,151 bytes across all nine
images at acceptance. Hosting may select different lossless encodings. These are the totals across all nine image payloads, not the total
initial page transfer size and not a promise about network latency.

## Lossless compression

`web/tools/static_delivery.py` prepares deterministic gzip level 9 and Brotli
quality 11 variants and verifies exact decompression. Compression is prepared
for 194 selected text resources, including the nine SVGs, public styles/scripts,
language dictionaries and relevant HTML pages. Across this set the original
payloads total 10,941,793 bytes, gzip variants 3,324,203 bytes and Brotli variants
2,628,140 bytes. These aggregate resource totals are not an initial-page metric.

`upgrade_rules()` changes the compression and cache sections of the retained
production `.htaccess`. It preserves the deployed CSP, OAuth routes, API
boundaries, legacy evidence routing, module revalidation and network-config
`no-store`. The brochure configuration must not replace the production file.

Prepared HTML, CSS, JS/MJS, JSON and SVG responses negotiate Brotli, gzip or the
original bytes with the appropriate MIME type and `Vary: Accept-Encoding`.
Explicit `q=0` refusals are respected. Missing prepared resources retain the
original path. Security-sensitive runtime configurations retain their cache
restrictions. HTML remains revalidated on repeat visits.

## Rebuild and validation

Assemble the pinned repositories and use `web/tools/requirements-images.txt`.
The existing verified build inputs are required for the complete static-export
tests: WASM, generated browser bundles and the local topology dataset. Reuse
those inputs or perform their documented builds; do not download or replace
models as part of this artwork update. Run large export tests with temporary
storage on a filesystem large enough for the retained topology dataset.

```sh
python3 tools/build_project_artwork.py
python3 tools/build_results_catalog.py
python3 tools/build_artwork_release.py --baseline RETAINED_RESULTS_R1 \
  --output NEW_RELEASE_DIRECTORY --report PRIVATE_BUILD_REPORT
python3 tools/validate_static_release.py NEW_RELEASE_DIRECTORY
python3 -m unittest discover -s tests -p 'test_static_*.py' -v
```

The release builder creates a new directory, preserving the baseline and
replacing changed files independently. Unchanged files may be hardlinked; never
edit a retained release or hardlinked file in place. The validator only admits
known root compression variants whose decompressed bytes match their originals.

The local browser suite passed 232 checks across 44 page/language/width cases.
Eleven static-export/delivery tests passed. Prior hosting negotiation evidence
covers 35 text-delivery cases; seven additional cases verify the native SVG MIME,
immutable cache policy, compression and explicit refusal behavior on the actual
hosting engine. Temporary canary directories were removed.

## Scoped publication and recovery

The candidate includes 402 changed frontend objects over the retained baseline.
A remote favicon Brotli object already matched the candidate exactly, although
it was absent from the retained local baseline. The initial guard stopped before
backup or installation. After read-only comparison, that identical object was
retained and 401 objects were staged, hash-verified and installed: 150 existing
objects and 251 additions. It is included in retention verification.

The operator creates a private archive of the actual old objects and verifies
all expected old hashes before installation. Assets and prepared variants are
installed before the HTML/configuration switch; the metadata is installed last.
All installed hashes and selected retained runtime hashes are checked again.
The backup and operation journal are retained outside the public web root.

Rollback restores only this frontend delta, after checking for concurrent
changes. Preserve current production databases, applications, events, wallet
state, models, candidates, signed transactions and unsettled rights. Do not
replay the earlier community migration or service activation for this update.

See `RESULTS_SVG_DELIVERY_20261023_ACCEPTANCE.json` for the dated production
checks and source pins. Physical devices and actual extension-wallet approval
remain outside the automated browser evidence. Full continuous-mining,
background outbox and long-duration acceptance remain separate work.
