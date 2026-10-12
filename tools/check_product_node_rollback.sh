#!/usr/bin/env bash
# Non-destructive binary rollback rehearsal; database and all archives retained.
set -euo pipefail
flypow_backup=${1:?verified backup directory required}
[[ "$flypow_backup" == /var/backups/flypow/product-upgrade-* ]]
test -f "$flypow_backup/target_authority.rollback"
test ! -e /opt/flypow/bin/target_authority.product-check-saved
systemctl stop flypow-target-verifier-serial flypow-target-authority
cp -a /opt/flypow/bin/target_authority /opt/flypow/bin/target_authority.product-check-saved
flypow_restore(){
    systemctl stop flypow-target-verifier-serial flypow-target-authority
    mv /opt/flypow/bin/target_authority.product-check-saved /opt/flypow/bin/target_authority
    systemctl start flypow-target-authority flypow-target-verifier-serial
}
trap flypow_restore EXIT
install -o root -g root -m 755 "$flypow_backup/target_authority.rollback" /opt/flypow/bin/target_authority.rollback-check
mv /opt/flypow/bin/target_authority.rollback-check /opt/flypow/bin/target_authority
systemctl start flypow-target-authority
for flypow_check in {1..30}; do
    if curl -fsS http://127.0.0.1:8790/api/target-mining/v2/rounds/current -o "$flypow_backup/rollback-current-round.json"; then
        printf 'Original binary reads migrated database and current signed round.\n'
        exit 0
    fi
    sleep 1
done
exit 1
