#!/usr/bin/env bash
# Add Social without invoking or restarting a scientific/financial driver.
set -euo pipefail
flybrain_upload=${1:?validated public upload directory required}
[[ "$flybrain_upload" == /home/ubuntu/flybrainlabs-community-upload ]]
test -f "$flybrain_upload/tools/social_server.mjs"
test -f "$flybrain_upload/config/social-community-v1.sql"
test -d "$flybrain_upload/node_modules/parse5"
test -d "$flybrain_upload/node_modules/entities"
test -f /etc/flypow/wallet-mining-v3-runtime.json
test ! -e /etc/systemd/system/flybrainlabs-community.service
umask 077
flybrain_backup=/var/backups/flypow/community-$(date -u +%Y%m%dT%H%M%SZ)-$$
mkdir -m 700 "$flybrain_backup"
cp -a /etc/nginx/conf.d/flypow-node.conf "$flybrain_backup/nginx.rollback"
python3 - "$flybrain_backup" <<'PY'
import hashlib,json,pathlib,sqlite3,sys
p=pathlib.Path(sys.argv[1]);runtime=pathlib.Path('/etc/flypow/wallet-mining-v3-runtime.json');c=json.loads(runtime.read_text())
source=sqlite3.connect(c['database']);source.execute('PRAGMA busy_timeout=10000')
backup=sqlite3.connect(str(p/'database-before.sqlite'));source.backup(backup);assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok';backup.close()
tables=['candidate_claims','round_winners','candidate_artifacts','goal_plan_progress','mining_v3_funded_goals','mining_v3_candidates','mining_v3_financial_outbox']
tables=[t for t in tables if source.execute('SELECT 1 FROM sqlite_master WHERE type="table" AND name=?',(t,)).fetchone()]
counts={t:source.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in tables}
p.joinpath('baseline.json').write_text(json.dumps(dict(counts=counts,runtimeHash=hashlib.sha256(runtime.read_bytes()).hexdigest()),indent=2)+'\n');source.close()
PY
sha256sum "$flybrain_backup/database-before.sqlite" > "$flybrain_backup/database-before.sha256"
install -d -o root -g root -m 755 /opt/flypow/runtime/community/node_modules
for flybrain_package in parse5 entities; do
    test ! -e "/opt/flypow/runtime/community/node_modules/$flybrain_package"
    cp -a "$flybrain_upload/node_modules/$flybrain_package" /opt/flypow/runtime/community/node_modules/
done
chown -R root:root /opt/flypow/runtime/community
if [ -e /opt/flypow/node_modules/parse5 ]; then
    /opt/flypow/runtime/node/bin/node --input-type=module -e 'import p from "/opt/flypow/node_modules/parse5/package.json" with {type:"json"};if(p.version!=="7.3.0")process.exit(1)'
else
    ln -s /opt/flypow/runtime/community/node_modules/parse5 /opt/flypow/node_modules/parse5
fi
install -d -o root -g root -m 755 /opt/flypow/web/data
if [ -e /opt/flypow/web/data/economic-policy-v2.json ]; then
    cmp -s "$flybrain_upload/web/data/economic-policy-v2.json" /opt/flypow/web/data/economic-policy-v2.json
else
    install -o root -g root -m 644 "$flybrain_upload/web/data/economic-policy-v2.json" /opt/flypow/web/data/economic-policy-v2.json
fi
for flybrain_file in tools/social_server.mjs tools/social_community.mjs tools/x_public_verification.mjs config/community-allocation-v1.json config/social-community-v1.sql; do
    test ! -e "/opt/flypow/$flybrain_file"
    install -o root -g root -m 644 "$flybrain_upload/$flybrain_file" "/opt/flypow/$flybrain_file"
done
install -o root -g root -m 644 "$flybrain_upload/deploy/target-v2/flybrainlabs-community.service" /etc/systemd/system/flybrainlabs-community.service
install -o root -g root -m 644 "$flybrain_upload/deploy/target-v2/nginx-community.conf" /opt/flypow/deploy/target-v2/nginx-community.conf
systemctl daemon-reload
systemctl enable --now flybrainlabs-community
flybrain_ok=0
for flybrain_attempt in {1..10}; do
    if curl --fail --silent http://127.0.0.1:8791/api/social/health > "$flybrain_backup/health.json"; then flybrain_ok=1; break; fi
    sleep 1
done
if [ "$flybrain_ok" != 1 ]; then systemctl stop flybrainlabs-community; echo 'Community startup failed; private backup retained' >&2; exit 1; fi
python3 - <<'PY'
from pathlib import Path
p=Path('/etc/nginx/conf.d/flypow-node.conf');s=p.read_text();line='    include /opt/flypow/deploy/target-v2/nginx-community.conf;'
anchor='    include /opt/flypow/deploy/target-v2/nginx-wallet-mining-v3.conf;'
if anchor not in s:raise ValueError('Existing authenticated gateway include missing')
if line not in s:p.write_text(s.replace(anchor,anchor+'\n'+line))
PY
if ! nginx -t; then
    cp -a "$flybrain_backup/nginx.rollback" /etc/nginx/conf.d/flypow-node.conf
    systemctl stop flybrainlabs-community
    exit 1
fi
systemctl reload nginx
systemctl is-active --quiet flybrainlabs-community flybrainlabs-wallet-mining-v3 flypow-target-authority flypow-target-verifier-serial
python3 - "$flybrain_backup" <<'PY'
import hashlib,json,pathlib,sqlite3,sys
p=pathlib.Path(sys.argv[1]);before=json.loads((p/'baseline.json').read_text());runtime=pathlib.Path('/etc/flypow/wallet-mining-v3-runtime.json');c=json.loads(runtime.read_text());db=sqlite3.connect(c['database']);counts={t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in before['counts']}
assert before['counts']==counts,'Historical business counts changed; inspect before claiming acceptance'
assert before['runtimeHash']==hashlib.sha256(runtime.read_bytes()).hexdigest(),'Private runtime changed'
assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
migration=db.execute('SELECT version,sha256 FROM social_schema_migrations').fetchone();assert migration==(1,hashlib.sha256(pathlib.Path('/opt/flypow/config/social-community-v1.sql').read_bytes()).hexdigest())
summary=dict(backup=str(p),coherentDatabaseBackup=True,historicalCountsPreserved=True,privateRuntimeUnchanged=True,integrity='ok',migrationVersion=migration[0],migrationHash=migration[1],initialPublicParticipants=db.execute('SELECT COUNT(*) FROM community_profiles').fetchone()[0],initialPointsEntries=db.execute('SELECT COUNT(*) FROM community_points_ledger').fetchone()[0],tokenTransfers=0,financialDriversInvoked=False)
p.joinpath('acceptance.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
PY
