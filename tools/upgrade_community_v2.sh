#!/usr/bin/env bash
# Upgrade only the community process; retain wallet, science and payment services.
set -euo pipefail
flybrain_upload=${1:?validated public upload directory required}
[[ "$flybrain_upload" == /home/ubuntu/flybrainlabs-community-v2-upload ]]
test "$(id -u)" = 0
test -f /etc/flypow/wallet-mining-v3-runtime.json
test -f "$flybrain_upload/manifest.json"
umask 077
python3 - "$flybrain_upload" <<'PY'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]);m=json.loads((p/'manifest.json').read_text())
allowed={'tools/social_community.mjs','tools/social_server.mjs','config/community-allocation-v1.json','config/social-community-v2.sql'}
assert set(m['files'])==allowed
for name,entry in m['files'].items():
 assert hashlib.sha256((p/name).read_bytes()).hexdigest()==entry['newSha256']
 target=pathlib.Path('/opt/flypow')/name
 assert (hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None)==entry['oldSha256'],'Installed source changed; reconcile before update'
assert hashlib.sha256(pathlib.Path('/opt/flypow/config/social-community-v1.sql').read_bytes()).hexdigest()==m['v1MigrationSha256']
PY
flybrain_backup=/var/backups/flypow/community-v2-$(date -u +%Y%m%dT%H%M%SZ)-$$
mkdir -m 700 "$flybrain_backup"
tar -czf "$flybrain_backup/sources-before.tar.gz" -C /opt/flypow tools/social_community.mjs tools/social_server.mjs config/community-allocation-v1.json
gzip -t "$flybrain_backup/sources-before.tar.gz"
systemctl stop flybrainlabs-community
python3 - "$flybrain_backup" <<'PY'
import hashlib,json,pathlib,sqlite3,sys
p=pathlib.Path(sys.argv[1]);runtime=pathlib.Path('/etc/flypow/wallet-mining-v3-runtime.json');config=json.loads(runtime.read_text());source=sqlite3.connect(config['database']);source.execute('PRAGMA busy_timeout=10000');backup=sqlite3.connect(str(p/'database-before.sqlite'));source.backup(backup);assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
tables=['community_points_ledger','social_task_completions','social_x_bindings','community_leaderboard_snapshots','community_leaderboard_snapshot_entries','community_budget_ledger','community_airdrop_allocations','community_airdrop_allocation_entries']
def rows_hash(db,table):return hashlib.sha256(json.dumps(db.execute('SELECT * FROM '+table+' ORDER BY rowid').fetchall(),separators=(',',':')).encode()).hexdigest()
before={'runtimeSha256':hashlib.sha256(runtime.read_bytes()).hexdigest(),'databaseBackupSha256':hashlib.sha256((p/'database-before.sqlite').read_bytes()).hexdigest(),'retainedTables':{t:{'rows':backup.execute('SELECT COUNT(*) FROM '+t).fetchone()[0],'sha256':rows_hash(backup,t)} for t in tables},'v1Migration':backup.execute('SELECT version,sha256 FROM social_schema_migrations WHERE version=1').fetchone()}
(p/'baseline.json').write_text(json.dumps(before,indent=2)+'\n');backup.close();source.close()
PY
for flybrain_file in tools/social_community.mjs tools/social_server.mjs config/community-allocation-v1.json config/social-community-v2.sql; do
    install -o root -g root -m 644 "$flybrain_upload/$flybrain_file" "/opt/flypow/$flybrain_file.community-v2-new"
    mv "/opt/flypow/$flybrain_file.community-v2-new" "/opt/flypow/$flybrain_file"
done
systemctl start flybrainlabs-community
flybrain_ok=0
for flybrain_attempt in {1..15}; do
    if curl --fail --silent http://127.0.0.1:8791/api/social/health > "$flybrain_backup/health.json"; then flybrain_ok=1; break; fi
    sleep 1
done
if [ "$flybrain_ok" != 1 ]; then echo 'Community v2 startup failed; coherent backup retained for reconciliation' >&2; exit 1; fi
systemctl is-active --quiet flybrainlabs-community flybrainlabs-wallet-mining-v3 flypow-target-authority flypow-target-verifier-serial
python3 - "$flybrain_backup" "$flybrain_upload" <<'PY'
import hashlib,json,pathlib,sqlite3,sys
p=pathlib.Path(sys.argv[1]);upload=pathlib.Path(sys.argv[2]);before=json.loads((p/'baseline.json').read_text());runtime=pathlib.Path('/etc/flypow/wallet-mining-v3-runtime.json');db=sqlite3.connect(json.loads(runtime.read_text())['database']);db.execute('PRAGMA busy_timeout=10000')
assert hashlib.sha256(runtime.read_bytes()).hexdigest()==before['runtimeSha256'];assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
for table,entry in before['retainedTables'].items():
 rows=db.execute('SELECT * FROM '+table+' ORDER BY rowid').fetchall()
 assert len(rows)==entry['rows'] and hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()==entry['sha256'],'Existing community evidence changed during update'
assert list(db.execute('SELECT version,sha256 FROM social_schema_migrations WHERE version=1').fetchone())==before['v1Migration']
assert db.execute('SELECT sha256 FROM social_schema_migrations WHERE version=2').fetchone()[0]==hashlib.sha256((upload/'config/social-community-v2.sql').read_bytes()).hexdigest()
assert db.execute("SELECT reward_points FROM social_tasks WHERE task_key='connect_x_identity_v1'").fetchone()[0]==10
health=json.loads((p/'health.json').read_text());assert health['schemaVersion']==2 and not health['tokenExecutionEnabled']
assert not db.execute('SELECT 1 FROM community_profiles WHERE show_x<>0').fetchone()
summary={'backup':str(p),'coherentDatabaseBackup':True,'historicalCommunityRowsAndBytesPreserved':True,'privateRuntimeUnchanged':True,'integrity':'ok','migrationVersion':2,'migrationSha256':hashlib.sha256((upload/'config/social-community-v2.sql').read_bytes()).hexdigest(),'identityPoints':10,'retainedTables':{k:v['rows'] for k,v in before['retainedTables'].items()},'communityRestarts':1,'otherServicesRestarted':0,'tokenTransfers':0,'financialDriversInvoked':False}
(p/'acceptance.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
PY
