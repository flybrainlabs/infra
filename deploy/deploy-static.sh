#!/usr/bin/env bash
# Existing cPanel website updater. The default is a non-mutating dry run.
set -Eeuo pipefail

FLYPOW_PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
FLYPOW_SSH_CONFIG="${FLYPOW_SSH_CONFIG:-/home/mars/.ssh/flybrain-deploy-eK9r7J/config}"
FLYPOW_RELEASE_DIR=""
FLYPOW_MODE="dry-run"
FLYPOW_MODE_SET=0
FLYPOW_BACKUP=""

usage() {
    printf '%s\n' \
      'Usage: bash deploy/deploy-static.sh --release DIRECTORY [--check | --dry-run | --apply]' \
      '       [--ssh-config FILE]' \
      'Default: dry run, no remote files changed. --apply creates a full backup before updating.'
}

while (($#)); do
    case "$1" in
        --release|--ssh-config)
            (($# >= 2)) || { usage >&2; exit 2; }
            if [[ "$1" == --release ]]; then FLYPOW_RELEASE_DIR="$2"; else FLYPOW_SSH_CONFIG="$2"; fi
            shift 2 ;;
        --check|--dry-run|--apply)
            ((FLYPOW_MODE_SET == 0)) || { printf '%s\n' 'Choose exactly one mode.' >&2; exit 2; }
            FLYPOW_MODE="${1#--}"; FLYPOW_MODE_SET=1; shift ;;
        --help|-h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done

[[ -n "$FLYPOW_RELEASE_DIR" && -d "$FLYPOW_RELEASE_DIR" ]] || { usage >&2; exit 2; }
[[ -f "$FLYPOW_SSH_CONFIG" ]] || { printf 'SSH config not found: %s\n' "$FLYPOW_SSH_CONFIG" >&2; exit 2; }
for FLYPOW_COMMAND in python3 ssh rsync; do command -v "$FLYPOW_COMMAND" >/dev/null; done
python3 "$FLYPOW_PROJECT_DIR/tools/validate_static_release.py" "$FLYPOW_RELEASE_DIR"
FLYPOW_RELEASE_DIR="$(cd -- "$FLYPOW_RELEASE_DIR" && pwd -P)"

# Enforce pinned-host authentication even if a copied config is edited later.
FLYPOW_SSH=(ssh -T -F "$FLYPOW_SSH_CONFIG" -o BatchMode=yes -o StrictHostKeyChecking=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=4)
FLYPOW_RESOLVED_HOST=""; FLYPOW_RESOLVED_USER=""; FLYPOW_RESOLVED_PORT=""
FLYPOW_RESOLVED_CONFIG="$("${FLYPOW_SSH[@]}" -G flybrain-work)"
while read -r FLYPOW_SETTING FLYPOW_VALUE; do
    case "$FLYPOW_SETTING" in
        hostname) FLYPOW_RESOLVED_HOST="$FLYPOW_VALUE" ;;
        user) FLYPOW_RESOLVED_USER="$FLYPOW_VALUE" ;;
        port) FLYPOW_RESOLVED_PORT="$FLYPOW_VALUE" ;;
    esac
done <<< "$FLYPOW_RESOLVED_CONFIG"
[[ "$FLYPOW_RESOLVED_HOST" == server241.web-hosting.com && "$FLYPOW_RESOLVED_USER" == flybwhiv && "$FLYPOW_RESOLVED_PORT" == 21098 ]] || { printf '%s\n' 'SSH config resolves to a different host, account or port; refusing deployment.' >&2; exit 2; }
# rsync parses the quoted -F argument itself; reject ambiguous shell characters.
[[ "$FLYPOW_SSH_CONFIG" != *'"'* && "$FLYPOW_SSH_CONFIG" != *$'\n'* ]] || { printf '%s\n' 'Invalid SSH config path.' >&2; exit 2; }
FLYPOW_RSH="ssh -T -F \"$FLYPOW_SSH_CONFIG\" -o BatchMode=yes -o StrictHostKeyChecking=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=4"

"${FLYPOW_SSH[@]}" flybrain-work 'set -e; test "$(id -un)" = flybwhiv; test -d /home/flybwhiv/public_html; test ! -L /home/flybwhiv/public_html; test ! -L /home/flybwhiv/flypow-deploy; printf "Verified account and directory: "; id -un; ls -ld /home/flybwhiv/public_html'
if [[ "$FLYPOW_MODE" == check ]]; then
    printf '%s\n' 'Release and SSH checks passed. No remote files changed.'
    exit 0
fi

FLYPOW_RSYNC=(rsync -rtz --checksum --delay-updates --itemize-changes -e "$FLYPOW_RSH")
if [[ "$FLYPOW_MODE" == dry-run ]]; then
    "${FLYPOW_RSYNC[@]}" --dry-run "$FLYPOW_RELEASE_DIR/" flybrain-work:/home/flybwhiv/public_html/
    printf '%s\n' 'Dry run finished. Nothing was uploaded, deleted or replaced. Use --apply to publish.'
    exit 0
fi

FLYPOW_DEPLOY_ID="manual-$(date -u +%Y%m%dT%H%M%SZ)-$$"
FLYPOW_BACKUP="/home/flybwhiv/flypow-deploy/$FLYPOW_DEPLOY_ID/before-public_html.tar.gz"
trap 'printf "Deployment did not complete. Existing backup (if created): %s\nNo automatic rollback or deletion was performed.\n" "$FLYPOW_BACKUP" >&2' ERR
printf 'Creating a full backup outside the website: %s\n' "$FLYPOW_BACKUP"
# Only fixed account paths and an internally generated timestamp are interpolated.
"${FLYPOW_SSH[@]}" flybrain-work "set -e; umask 077; test ! -e /home/flybwhiv/flypow-deploy/$FLYPOW_DEPLOY_ID; mkdir -p /home/flybwhiv/flypow-deploy; chmod 700 /home/flybwhiv/flypow-deploy; mkdir /home/flybwhiv/flypow-deploy/$FLYPOW_DEPLOY_ID; tar --use-compress-program='gzip -1' -cf $FLYPOW_BACKUP -C /home/flybwhiv/public_html . & FLYPOW_BACKUP_PID=\$!; while kill -0 \"\$FLYPOW_BACKUP_PID\" 2>/dev/null; do printf 'Backup is running...\\n'; sleep 15; done; wait \"\$FLYPOW_BACKUP_PID\"; gzip -t $FLYPOW_BACKUP; sha256sum $FLYPOW_BACKUP"

# No --delete, --inplace, -a, or permission/owner/group synchronization.
# Preserve unrelated files and the cPanel document-root permissions.
"${FLYPOW_RSYNC[@]}" "$FLYPOW_RELEASE_DIR/" flybrain-work:/home/flybwhiv/public_html/
python3 "$FLYPOW_PROJECT_DIR/tools/check_public_site.py" --base-url https://flybrain.work/ --release "$FLYPOW_RELEASE_DIR"
printf 'Published and verified: https://flybrain.work/\nBackup retained: %s\n' "$FLYPOW_BACKUP"
