#!/usr/bin/env bash
# Run with sudo on the authorized development node after staging verified files.
set -euo pipefail
test "$(id -un)" = root
test -f /home/ubuntu/flypow-product-authority
test -f /etc/flypow/authority-config.json
test -f /var/lib/flypow/authority/target-v2.sqlite
test -d /var/backups/flypow
flypow_product_backup=/var/backups/flypow/product-$(date -u +%Y%m%dT%H%M%SZ)
umask 077
mkdir "$flypow_product_backup"
# Quiesce both owners, including SQLite/WAL and all private upload state.
trap 'systemctl start flypow-target-authority; systemctl start flypow-target-verifier-serial' EXIT
systemctl stop flypow-target-verifier-serial
systemctl stop flypow-target-authority
tar -czf "$flypow_product_backup/before.tar.gz" -C / etc/flypow var/lib/flypow/authority opt/flypow/bin/target_authority etc/systemd/system/flypow-target-authority.service etc/systemd/system/flypow-target-authority.service.d
gzip -t "$flypow_product_backup/before.tar.gz"
sha256sum "$flypow_product_backup/before.tar.gz" > "$flypow_product_backup/SHA256SUMS"
install -o root -g root -m 0755 /home/ubuntu/flypow-product-authority /opt/flypow/bin/target_authority
install -o root -g root -m 0644 /home/ubuntu/publish_product_plan.mjs /opt/flypow/tools/publish_product_plan.mjs
install -o flypow -g flypow -m 0600 /home/ubuntu/flypow-product-plan.json /opt/flypow/deploy/product-plan-draft.json
printf 'Verified coherent backup: %s\n' "$flypow_product_backup"
# The EXIT trap starts both services even if any check above fails.
