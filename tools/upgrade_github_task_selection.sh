#!/usr/bin/env bash
# Replace only the GitHub task selection sources, retaining all historical state.
set -euo pipefail
flybrain_upload=${1:?validated upload directory required}
[[ "$flybrain_upload" == /home/ubuntu/flybrainlabs-github-task-selection-upload ]]
test "$(id -u)" = 0
umask 077
exec 9>/run/lock/flybrainlabs-github-task-selection.lock
flock -n 9
python3 - "$flybrain_upload" <<'PY'
import hashlib,json,pathlib,sys
upload=pathlib.Path(sys.argv[1]);manifest=json.loads((upload/'manifest.json').read_text())
assert set(manifest['files'])=={'tools/social_github.mjs','tools/social_community.mjs','config/github-community-tasks-v2.json'}
for name,entry in manifest['files'].items():
 assert hashlib.sha256((upload/name).read_bytes()).hexdigest()==entry['newSha256']
 target=pathlib.Path('/opt/flypow')/name
 assert (hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None)==entry['oldSha256'],'Installed source changed; reconcile first'
for name,value in manifest['retainedHashes'].items():assert hashlib.sha256((pathlib.Path('/opt/flypow')/name).read_bytes()).hexdigest()==value
PY
flybrain_backup=/var/backups/flypow/github-task-selection-$(date -u +%Y%m%dT%H%M%SZ)-$$
mkdir -m 700 "$flybrain_backup"
systemctl show flybrainlabs-wallet-mining-v3 flypow-target-authority flypow-target-verifier-serial -p Id -p MainPID -p ExecMainStartTimestamp > "$flybrain_backup/other-services-before.txt"
flybrain_rollback() {
    trap - ERR
    systemctl stop flybrainlabs-community || true
    if [ -f "$flybrain_backup/sources-before.tar.gz" ]; then
        tar -xzf "$flybrain_backup/sources-before.tar.gz" -C /opt/flypow
        if [ -f "$flybrain_backup/new-manifest-marker" ]; then
            rm -f /opt/flypow/config/github-community-tasks-v2.json
        fi
    fi
    systemctl start flybrainlabs-community
    echo 'Task selection update failed; previous sources restored and database evidence retained' >&2
    exit 1
}
trap flybrain_rollback ERR
systemctl stop flybrainlabs-community
python3 - "$flybrain_backup" "$flybrain_upload" <<'PY'
import hashlib,json,pathlib,sqlite3,sys,tarfile
backup,upload=map(pathlib.Path,sys.argv[1:]);runtime=pathlib.Path('/etc/flypow/wallet-mining-v3-runtime.json');private=pathlib.Path('/etc/flypow/github-community.json')
db=sqlite3.connect(json.loads(runtime.read_text())['database']);db.execute('PRAGMA busy_timeout=10000');copy=sqlite3.connect(backup/'database-before.sqlite');db.backup(copy);assert copy.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
tables=['community_points_ledger','social_task_completions','social_repeat_completions','social_x_bindings','community_registrations','community_invites','community_referral_rewards','social_post_uses','community_leaderboard_snapshots','community_leaderboard_snapshot_entries','community_airdrop_allocations','community_airdrop_allocation_entries','community_budget_ledger','community_admin_audit','social_verification_audit','social_tasks','social_github_task_targets','social_github_bindings','social_github_credentials']
def digest(rows):return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
baseline={'runtimeHash':hashlib.sha256(runtime.read_bytes()).hexdigest(),'privateConfigHash':hashlib.sha256(private.read_bytes()).hexdigest(),'migrationHashes':dict(copy.execute('SELECT version,sha256 FROM social_schema_migrations')),'tables':{t:{'rows':copy.execute('SELECT COUNT(*) FROM '+t).fetchone()[0],'hash':digest(copy.execute('SELECT * FROM '+t+' ORDER BY rowid').fetchall())} for t in tables}}
(backup/'baseline.json').write_text(json.dumps(baseline,indent=2)+'\n')
with tarfile.open(backup/'sources-before.tar.gz','w:gz') as archive:
 for name,entry in json.loads((upload/'manifest.json').read_text())['files'].items():
  file=pathlib.Path('/opt/flypow')/name
  if entry['oldSha256'] is not None:archive.add(file,arcname=name)
  elif name=='config/github-community-tasks-v2.json':(backup/'new-manifest-marker').touch()
copy.close();db.close()
PY
gzip -t "$flybrain_backup/sources-before.tar.gz"
for flybrain_file in config/github-community-tasks-v2.json tools/social_github.mjs tools/social_community.mjs; do
    install -o root -g root -m 644 "$flybrain_upload/$flybrain_file" "/opt/flypow/$flybrain_file.task-selection-new"
    mv "/opt/flypow/$flybrain_file.task-selection-new" "/opt/flypow/$flybrain_file"
done
systemctl start flybrainlabs-community
flybrain_ok=0
for flybrain_attempt in {1..15}; do
    if curl --fail --silent http://127.0.0.1:8791/api/social/health > "$flybrain_backup/health.json"; then flybrain_ok=1; break; fi
    sleep 1
done
[[ "$flybrain_ok" == 1 ]]
systemctl show flybrainlabs-wallet-mining-v3 flypow-target-authority flypow-target-verifier-serial -p Id -p MainPID -p ExecMainStartTimestamp > "$flybrain_backup/other-services-after.txt"
cmp -s "$flybrain_backup/other-services-before.txt" "$flybrain_backup/other-services-after.txt"
python3 - "$flybrain_backup" "$flybrain_upload" <<'PY'
import hashlib,json,pathlib,sqlite3,sys,urllib.request
backup,upload=map(pathlib.Path,sys.argv[1:]);baseline=json.loads((backup/'baseline.json').read_text());runtime=pathlib.Path('/etc/flypow/wallet-mining-v3-runtime.json');private=pathlib.Path('/etc/flypow/github-community.json');db=sqlite3.connect(json.loads(runtime.read_text())['database']);db.execute('PRAGMA busy_timeout=10000')
assert hashlib.sha256(runtime.read_bytes()).hexdigest()==baseline['runtimeHash'];assert hashlib.sha256(private.read_bytes()).hexdigest()==baseline['privateConfigHash'];assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert {str(v):h for v,h in db.execute('SELECT version,sha256 FROM social_schema_migrations')}==baseline['migrationHashes']
for table,entry in baseline['tables'].items():
 rows=db.execute('SELECT * FROM '+table+' ORDER BY rowid LIMIT ?', (entry['rows'],)).fetchall()
 assert len(rows)==entry['rows'] and hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()==entry['hash'],'Historical rows changed; reconcile the retained backup'
with urllib.request.urlopen('http://127.0.0.1:8791/api/social/tasks',timeout=10) as response:tasks=json.load(response)['tasks']
selected=sorted(t['id'] for t in tasks if t['category']=='github');assert selected==['github_connect_v1','github_star_infra_v1','github_star_miner_v1','github_star_node_v1']
health=json.loads((backup/'health.json').read_text());assert health['githubConfigured'] and not health['githubEngagementRewardsEnabled'] and not health['tokenExecutionEnabled']
manifest=json.loads((upload/'manifest.json').read_text())
for name,entry in manifest['files'].items():assert hashlib.sha256((pathlib.Path('/opt/flypow')/name).read_bytes()).hexdigest()==entry['newSha256']
for name,value in manifest['retainedHashes'].items():assert hashlib.sha256((pathlib.Path('/opt/flypow')/name).read_bytes()).hexdigest()==value
report={'passed':True,'backup':str(backup),'changedSourceFiles':3,'migrationRepeated':False,'historicalRowsPreserved':True,'privateConfigurationUnchanged':True,'activeGitHubTaskIds':selected,'engagementRewardsEnabled':False,'communityRestarts':1,'otherServicesRestarted':0,'retainedRowCounts':{t:e['rows'] for t,e in baseline['tables'].items()},'sourceHashes':{f:e['newSha256'] for f,e in manifest['files'].items()},'chainTransactions':0}
(backup/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
db.close()
PY
trap - ERR
