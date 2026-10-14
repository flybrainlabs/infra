#!/usr/bin/env bash
# Upgrade the community service alone with a coherent backup and retained history.
set -euo pipefail
flybrain_upload=${1:?validated upload directory required}
[[ "$flybrain_upload" == /home/ubuntu/flybrainlabs-community-v3-upload ]]
test "$(id -u)" = 0
test -f "$flybrain_upload/manifest.json"
umask 077
python3 - "$flybrain_upload" <<'PY'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]);m=json.loads((p/'manifest.json').read_text())
allowed={'tools/social_community.mjs','tools/social_server.mjs','tools/social_github.mjs','tools/github_provider.mjs','config/social-community-v3.sql','config/github-community-tasks-v1.json','deploy/target-v2/nginx-community.conf'}
assert set(m['files'])==allowed
for name,entry in m['files'].items():
 assert hashlib.sha256((p/name).read_bytes()).hexdigest()==entry['newSha256']
 target=pathlib.Path('/opt/flypow')/name
 assert (hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None)==entry['oldSha256'],'Installed source changed; reconcile before upgrade'
for version in (1,2):
 assert hashlib.sha256(pathlib.Path('/opt/flypow/config/social-community-v'+str(version)+'.sql').read_bytes()).hexdigest()==m['migrationHashes'][str(version)]
PY
flybrain_backup=/var/backups/flypow/community-v3-$(date -u +%Y%m%dT%H%M%SZ)-$$
mkdir -m 700 "$flybrain_backup"
cp -a /opt/flypow/deploy/target-v2/nginx-community.conf "$flybrain_backup/nginx-community.rollback"
systemctl show flybrainlabs-wallet-mining-v3 flypow-target-authority flypow-target-verifier-serial -p Id -p MainPID -p ExecMainStartTimestamp > "$flybrain_backup/other-services-before.txt"
flybrain_upgrade_failed() {
    trap - ERR
    if [ -f "$flybrain_backup/sources-before.tar.gz" ]; then
        tar -xzf "$flybrain_backup/sources-before.tar.gz" -C /opt/flypow
    fi
    cp -a "$flybrain_backup/nginx-community.rollback" /opt/flypow/deploy/target-v2/nginx-community.conf
    if nginx -t; then systemctl reload nginx; fi
    systemctl start flybrainlabs-community
    echo 'Community upgrade failed; previous code restored and database evidence retained' >&2
    exit 1
}
trap flybrain_upgrade_failed ERR
systemctl stop flybrainlabs-community
python3 - "$flybrain_backup" "$flybrain_upload" <<'PY'
import hashlib,json,pathlib,shutil,sqlite3,sys,tarfile
p,upload=map(pathlib.Path,sys.argv[1:]);runtime=pathlib.Path('/etc/flypow/wallet-mining-v3-runtime.json');c=json.loads(runtime.read_text());database=pathlib.Path(c['database'])
source=sqlite3.connect(database);source.execute('PRAGMA busy_timeout=10000');backup=sqlite3.connect(p/'database-before.sqlite');source.backup(backup);assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
# The SQLite backup is coherent and includes committed WAL contents. Retain raw
# database/WAL/SHM copies as a separate operational archive, not a coherent image.
raw=[]
for suffix in ('','-wal','-shm'):
 file=pathlib.Path(str(database)+suffix)
 if file.exists():
  target=p/('raw-database'+suffix);shutil.copy2(file,target);raw.append({'file':target.name,'bytes':target.stat().st_size})
tables=['community_points_ledger','social_task_completions','social_repeat_completions','social_x_bindings','community_registrations','community_invites','community_referral_rewards','social_post_uses','community_leaderboard_snapshots','community_leaderboard_snapshot_entries','community_airdrop_allocations','community_airdrop_allocation_entries','community_budget_ledger','community_admin_audit','social_verification_audit','community_distribution_rules']
def digest(rows):return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
before={'runtimeSha256':hashlib.sha256(runtime.read_bytes()).hexdigest(),'databaseBackupSha256':hashlib.sha256((p/'database-before.sqlite').read_bytes()).hexdigest(),'migrationHashes':{str(v):h for v,h in backup.execute('SELECT version,sha256 FROM social_schema_migrations')},'retainedTables':{t:{'rows':backup.execute('SELECT COUNT(*) FROM '+t).fetchone()[0],'sha256':digest(backup.execute('SELECT * FROM '+t+' ORDER BY rowid').fetchall())} for t in tables},'rawDatabaseCopies':raw}
(p/'baseline.json').write_text(json.dumps(before,indent=2)+'\n')
with tarfile.open(p/'sources-before.tar.gz','w:gz') as archive:
 for name in json.loads((upload/'manifest.json').read_text())['files']:
  file=pathlib.Path('/opt/flypow')/name
  if file.exists():archive.add(file,arcname=name)
backup.close();source.close()
PY
gzip -t "$flybrain_backup/sources-before.tar.gz"
for flybrain_file in tools/social_community.mjs tools/social_server.mjs tools/social_github.mjs tools/github_provider.mjs config/social-community-v3.sql config/github-community-tasks-v1.json deploy/target-v2/nginx-community.conf; do
    install -o root -g root -m 644 "$flybrain_upload/$flybrain_file" "/opt/flypow/$flybrain_file.community-v3-new"
    mv "/opt/flypow/$flybrain_file.community-v3-new" "/opt/flypow/$flybrain_file"
done
if ! nginx -t; then
    cp -a "$flybrain_backup/nginx-community.rollback" /opt/flypow/deploy/target-v2/nginx-community.conf
    echo 'OAuth route validation failed; source/database backup retained' >&2
    false
fi
systemctl start flybrainlabs-community
flybrain_ok=0
for flybrain_attempt in {1..15}; do
    if curl --fail --silent http://127.0.0.1:8791/api/social/health > "$flybrain_backup/health.json"; then flybrain_ok=1; break; fi
    sleep 1
done
if [ "$flybrain_ok" != 1 ]; then echo 'Community v3 startup failed; reconcile using the retained backup' >&2; false; fi
systemctl reload nginx
systemctl is-active --quiet flybrainlabs-community flybrainlabs-wallet-mining-v3 flypow-target-authority flypow-target-verifier-serial
systemctl show flybrainlabs-wallet-mining-v3 flypow-target-authority flypow-target-verifier-serial -p Id -p MainPID -p ExecMainStartTimestamp > "$flybrain_backup/other-services-after.txt"
cmp -s "$flybrain_backup/other-services-before.txt" "$flybrain_backup/other-services-after.txt"
python3 - "$flybrain_backup" "$flybrain_upload" <<'PY'
import hashlib,json,pathlib,sqlite3,sys
p,upload=map(pathlib.Path,sys.argv[1:]);before=json.loads((p/'baseline.json').read_text());runtime=pathlib.Path('/etc/flypow/wallet-mining-v3-runtime.json');db=sqlite3.connect(json.loads(runtime.read_text())['database']);db.execute('PRAGMA busy_timeout=10000')
assert hashlib.sha256(runtime.read_bytes()).hexdigest()==before['runtimeSha256'];assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
after={}
for table,entry in before['retainedTables'].items():
 rows=db.execute('SELECT * FROM '+table+' ORDER BY rowid LIMIT ?', (entry['rows'],)).fetchall()
 assert len(rows)==entry['rows'] and hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()==entry['sha256'],'Historical rows changed during upgrade'
 after[table]=db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
for version in (1,2):assert db.execute('SELECT sha256 FROM social_schema_migrations WHERE version=?',(version,)).fetchone()[0]==before['migrationHashes'][str(version)]
v3=hashlib.sha256((upload/'config/social-community-v3.sql').read_bytes()).hexdigest();assert db.execute('SELECT sha256 FROM social_schema_migrations WHERE version=3').fetchone()[0]==v3
assert db.execute("SELECT COUNT(*) FROM social_tasks WHERE category='github'").fetchone()[0]==12
assert not db.execute('SELECT 1 FROM community_profiles p WHERE p.total_points<>COALESCE((SELECT SUM(points_delta) FROM community_points_ledger l WHERE l.wallet=p.wallet),0)').fetchone()
health=json.loads((p/'health.json').read_text());assert health['schemaVersion']==3 and health['githubConfigured'] and not health['githubEngagementRewardsEnabled'] and not health['tokenExecutionEnabled']
summary={'backup':str(p),'coherentDatabaseBackup':True,'rawDatabaseWalCopies':before['rawDatabaseCopies'],'historicalRowsPreserved':True,'privateWalletRuntimeUnchanged':True,'integrity':'ok','migrationVersion':3,'migrationSha256':v3,'retainedCountsBefore':{t:e['rows'] for t,e in before['retainedTables'].items()},'retainedCountsAfter':after,'githubTasks':12,'githubBindings':db.execute('SELECT COUNT(*) FROM social_github_bindings').fetchone()[0],'githubConfigured':True,'engagementRewardsEnabled':False,'communityRestarts':1,'otherServicesRestarted':0,'productionFixtureUsersCreated':0,'chainTransactions':0}
(p/'acceptance.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
PY
trap - ERR
