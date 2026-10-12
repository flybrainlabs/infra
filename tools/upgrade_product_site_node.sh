#!/usr/bin/env bash
# Run with sudo on the established cloud node after staging validated objects.
# No bootstrap, key rotation, schema deletion or formal asset operation.
set -euo pipefail
flypow_upload=${1:?validated upload directory required}
flypow_package=${2:?64-lowercase-hex public package identity required}
[[ "$flypow_package" =~ ^[a-f0-9]{64}$ ]]
[[ "$flypow_upload" == /home/ubuntu/flypow-product-upload-* ]]
test -f "$flypow_upload/target_authority"
test -f /var/lib/flypow/authority/private/admin.key
umask 077
flypow_backup=/var/backups/flypow/product-upgrade-$(date -u +%Y%m%dT%H%M%SZ)-$$
mkdir -m 700 "$flypow_backup"
flypow_nginx=/etc/nginx/conf.d/flypow-node.conf
systemctl stop flypow-target-verifier-serial flypow-target-authority
trap 'systemctl start flypow-target-authority flypow-target-verifier-serial' EXIT
tar -czf "$flypow_backup/before.tar.gz" -C / var/lib/flypow/authority etc/flypow opt/flypow/bin/target_authority opt/flypow/deploy/target-v2 etc/nginx/conf.d/flypow-node.conf etc/systemd/system/flypow-target-authority.service etc/systemd/system/flypow-target-authority.service.d
gzip -t "$flypow_backup/before.tar.gz"
sha256sum "$flypow_backup/before.tar.gz" > "$flypow_backup/SHA256SUMS"
cp -a /opt/flypow/bin/target_authority "$flypow_backup/target_authority.rollback"
cp -a "$flypow_nginx" "$flypow_backup/nginx.rollback"
install -o root -g root -m 755 "$flypow_upload/target_authority" /opt/flypow/bin/target_authority.product-new
mv /opt/flypow/bin/target_authority.product-new /opt/flypow/bin/target_authority
install -o root -g root -m 644 "$flypow_upload/product_ops.mjs" /opt/flypow/tools/product_ops.mjs
mkdir -p /opt/flypow/deploy/product-v2
install -o root -g root -m 644 "$flypow_upload/nginx-product-api.conf" /opt/flypow/deploy/product-v2/nginx-product-api.conf
# The previous ^~ fallback suppresses sibling product API regex locations.
sed -i 's|location \^~ /api/ { return 404; }|location /api/ { return 404; }|' /opt/flypow/deploy/target-v2/nginx-api.conf
if ! grep -Fq 'include /opt/flypow/deploy/product-v2/nginx-product-api.conf;' "$flypow_nginx"; then
    sed -i '/include \/opt\/flypow\/deploy\/target-v2\/nginx-api.conf;/a\    include /opt/flypow/deploy/product-v2/nginx-product-api.conf;' "$flypow_nginx"
fi
if ! nginx -t; then
    cp -a "$flypow_backup/nginx.rollback" "$flypow_nginx"
    cp -a "$flypow_backup/target_authority.rollback" /opt/flypow/bin/target_authority.rollback-new
    mv /opt/flypow/bin/target_authority.rollback-new /opt/flypow/bin/target_authority
    tar -xzf "$flypow_backup/before.tar.gz" -C / opt/flypow/deploy/target-v2
    exit 1
fi
install -d -o flypow -g flypow -m 700 /var/lib/flypow/authority/public-staging
flypow_stage=/var/lib/flypow/authority/public-staging/$flypow_package
if [ ! -e "$flypow_stage" ]; then cp -a "$flypow_upload/public-package" "$flypow_stage"; fi
chown -R flypow:flypow "$flypow_stage"
chmod -R u=rwX,go= "$flypow_stage"
systemctl start flypow-target-authority flypow-target-verifier-serial
systemctl reload nginx
systemctl is-active flypow-target-authority flypow-target-verifier-serial
sha256sum /opt/flypow/bin/target_authority
printf 'Verified private backup: %s\n' "$flypow_backup"
