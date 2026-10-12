#!/usr/bin/env bash
# On the existing node: preserve scientific state and install the finite gateway.
set -euo pipefail
flybrain_upload=${1:?validated public upload directory required}
flybrain_private=${2:?private signer/config upload directory required}
[[ "$flybrain_upload" == /home/ubuntu/flybrainlabs-wallet-v3-upload ]]
[[ "$flybrain_private" == /home/ubuntu/flybrainlabs-wallet-v3-private ]]
test -f "$flybrain_upload/target_authority"
test -d "$flybrain_upload/node_modules/@solana/web3.js"
test -f "$flybrain_private/runtime.json"
test -f "$flybrain_private/relayer.json"
umask 077
flybrain_backup=/var/backups/flypow/wallet-v3-$(date -u +%Y%m%dT%H%M%SZ)-$$
mkdir -m 700 "$flybrain_backup"
if systemctl is-active --quiet flybrainlabs-wallet-mining-v3; then systemctl stop flybrainlabs-wallet-mining-v3; fi
systemctl stop flypow-target-verifier-serial flypow-target-authority
trap 'systemctl start flypow-target-authority flypow-target-verifier-serial' EXIT
flybrain_paths=()
for flybrain_path in var/lib/flypow/authority etc/flypow opt/flypow/bin opt/flypow/tools opt/flypow/web opt/flypow/config opt/flypow/deploy etc/nginx/conf.d/flypow-node.conf; do
    if [ -e "/$flybrain_path" ]; then flybrain_paths+=("$flybrain_path"); fi
done
tar -cf "$flybrain_backup/before.tar" -C / "${flybrain_paths[@]}"
tar -tf "$flybrain_backup/before.tar" > "$flybrain_backup/contents.txt"
sha256sum "$flybrain_backup/before.tar" > "$flybrain_backup/SHA256SUMS"
python3 - "$flybrain_backup" <<'PY'
import json,sqlite3,pathlib,sys
p=pathlib.Path(sys.argv[1]);db=sqlite3.connect('/var/lib/flypow/authority/target-v2.sqlite')
p.joinpath('business-counts.json').write_text(json.dumps({t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['candidate_claims','round_winners','candidate_artifacts','goal_plan_progress']},indent=2)+'\n')
PY
cp -a /etc/nginx/conf.d/flypow-node.conf "$flybrain_backup/nginx.rollback"
cp -a /opt/flypow/bin/target_authority "$flybrain_backup/target_authority.rollback"
cp -a /opt/flypow/bin/target_trial "$flybrain_backup/target_trial.rollback"
for flybrain_bin in target_authority target_trial; do
    install -o root -g root -m 755 "$flybrain_upload/$flybrain_bin" "/opt/flypow/bin/$flybrain_bin.wallet-new"
    mv "/opt/flypow/bin/$flybrain_bin.wallet-new" "/opt/flypow/bin/$flybrain_bin"
done
for flybrain_dir in tools web config; do
    install -d -o root -g root -m 755 "/opt/flypow/$flybrain_dir"
    cp -a "$flybrain_upload/$flybrain_dir/." "/opt/flypow/$flybrain_dir/"
    chown -R root:root "/opt/flypow/$flybrain_dir"
done
install -d -o root -g root -m 755 /opt/flypow/runtime/wallet-v3
if [ ! -e /opt/flypow/runtime/wallet-v3/node_modules ]; then mv "$flybrain_upload/node_modules" /opt/flypow/runtime/wallet-v3/node_modules; fi
if [ ! -e /opt/flypow/node_modules ]; then ln -s /opt/flypow/runtime/wallet-v3/node_modules /opt/flypow/node_modules; fi
install -o flypow -g flypow -m 600 "$flybrain_private/runtime.json" /etc/flypow/wallet-mining-v3-runtime.json
install -o flypow -g flypow -m 600 "$flybrain_private/relayer.json" /etc/flypow/private/wallet-v3-relayer.json
install -d -o flypow -g flypow -m 700 /var/lib/flypow/authority/private/wallet-mining-v3-results
install -o root -g root -m 644 "$flybrain_upload/deploy/target-v2/flybrainlabs-wallet-mining-v3.service" /etc/systemd/system/flybrainlabs-wallet-mining-v3.service
install -o root -g root -m 644 "$flybrain_upload/deploy/target-v2/nginx-wallet-mining-v3.conf" /opt/flypow/deploy/target-v2/nginx-wallet-mining-v3.conf
python3 - <<'PY'
from pathlib import Path
p=Path('/etc/nginx/conf.d/flypow-node.conf');text=p.read_text();line='    include /opt/flypow/deploy/target-v2/nginx-wallet-mining-v3.conf;'
if line not in text:text=text.replace('    include /opt/flypow/deploy/target-v2/nginx-api.conf;', '    include /opt/flypow/deploy/target-v2/nginx-api.conf;\n'+line)
p.write_text(text)
PY
if ! nginx -t; then
    cp -a "$flybrain_backup/nginx.rollback" /etc/nginx/conf.d/flypow-node.conf
    cp -a "$flybrain_backup/target_authority.rollback" /opt/flypow/bin/target_authority
    cp -a "$flybrain_backup/target_trial.rollback" /opt/flypow/bin/target_trial
    exit 1
fi
systemctl daemon-reload
systemctl start flypow-target-authority flypow-target-verifier-serial
systemctl enable --now flybrainlabs-wallet-mining-v3
systemctl reload nginx
systemctl is-active flypow-target-authority flypow-target-verifier-serial flybrainlabs-wallet-mining-v3
python3 - "$flybrain_backup" <<'PY'
import sqlite3,json,pathlib,sys
p=pathlib.Path(sys.argv[1]);db=sqlite3.connect('/var/lib/flypow/authority/target-v2.sqlite');before=json.loads(p.joinpath('business-counts.json').read_text());after={t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in before};assert before==after,'Historical business state changed during upgrade';print(json.dumps(dict(backup=str(p),historicalCountsPreserved=True,counts=after)))
PY
