#!/usr/bin/env bash
# Enable the bounded dispatcher while retaining existing tasks, money and users.
set -euo pipefail
flybrain_upload=${1:?validated upload directory required}
[[ "$flybrain_upload" == /home/ubuntu/flybrainlabs-continuous-supply-upload ]]
test "$(id -u)" = 0
umask 077
exec 9>/run/lock/flybrainlabs-continuous-supply.lock
flock -n 9
python3 - "$flybrain_upload" <<'PY'
import hashlib,json,pathlib,sys,subprocess,tempfile,shutil
upload=pathlib.Path(sys.argv[1]);m=json.loads((upload/'manifest.json').read_text())
assert hashlib.sha256((upload/'policy.example.json').read_bytes()).hexdigest()==m['policySha256']
assert set(m['files'])=={'tools/wallet_mining_v3.mjs','tools/wallet_rpc_v3.mjs','tools/continuous_task_supply.mjs','tools/approve_task_catalog.mjs'}
for name,e in m['files'].items():
 assert hashlib.sha256((upload/name).read_bytes()).hexdigest()==e['newSha256']
 p=pathlib.Path('/opt/flypow')/name
 assert (hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None)==e['oldSha256'],'Installed sources changed'
assert hashlib.sha256(pathlib.Path('/etc/flypow/wallet-mining-v3-runtime.json').read_bytes()).hexdigest()==m['runtimeHash']
for name,digest in m['retainedHashes'].items():assert hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()==digest
policy_path=pathlib.Path('/etc/flypow/continuous-task-supply.json')
if policy_path.exists():
 cfg=json.loads(pathlib.Path('/etc/flypow/wallet-mining-v3-runtime.json').read_text());authority=json.loads(pathlib.Path('/etc/flypow/authority-config.json').read_text())
 expected=json.loads((upload/'policy.example.json').read_text());expected.update(networkId=authority['networkId'],campaignId=authority['campaignId'],authorityId=cfg['authorityId'],adminKeyPath='/var/lib/flypow/authority/private/admin.key')
 assert json.loads(policy_path.read_text())==expected,'Retained dispatcher policy differs'
assert not pathlib.Path('/etc/flypow/continuous-task-catalog.json').exists()
# Resolve the complete installed import graph before stopping the live gateway.
# A parse-only check cannot detect a missing sibling RPC module.
with tempfile.TemporaryDirectory(prefix='flybrain-supply-import-') as temporary:
 root=pathlib.Path(temporary);(root/'tools').mkdir();(root/'web').symlink_to('/opt/flypow/web',target_is_directory=True);(root/'node_modules').symlink_to('/opt/flypow/node_modules',target_is_directory=True)
 for name in m['files']:shutil.copyfile(upload/name,root/name)
 for name in ['target_dev_identity.mjs','mining_v3_client.mjs','settlement_bridge_v2.mjs']:(root/'tools'/name).symlink_to(pathlib.Path('/opt/flypow/tools')/name)
 code='await import('+json.dumps((root/'tools/wallet_mining_v3.mjs').as_uri())+'); await import('+json.dumps((root/'tools/continuous_task_supply.mjs').as_uri())+');'
 result=subprocess.run(['/opt/flypow/runtime/node/bin/node','--input-type=module','-'],input=code,text=True,capture_output=True)
 assert result.returncode==0,'Node import gate failed before any live change'
PY
flybrain_backup=/var/backups/flypow/continuous-supply-$(date -u +%Y%m%dT%H%M%SZ)-$$
mkdir -m 700 "$flybrain_backup"
systemctl show flypow-target-authority flypow-target-verifier-serial flybrainlabs-community -p Id -p MainPID > "$flybrain_backup/other-services-before.txt"
flybrain_rollback() {
    trap - ERR
    systemctl stop flybrainlabs-wallet-mining-v3 || true
    if [ -f "$flybrain_backup/sources-before.tar.gz" ]; then tar -xzf "$flybrain_backup/sources-before.tar.gz" -C /opt/flypow; fi
    if [ -f "$flybrain_backup/runtime-before.json" ]; then
        cp -p "$flybrain_backup/runtime-before.json" /etc/flypow/wallet-mining-v3-runtime.json.rollback-new
        mv /etc/flypow/wallet-mining-v3-runtime.json.rollback-new /etc/flypow/wallet-mining-v3-runtime.json
    fi
    systemctl start flybrainlabs-wallet-mining-v3
    echo 'Supply update failed; prior runtime restored; all databases and evidence retained' >&2
    exit 1
}
trap flybrain_rollback ERR
systemctl stop flybrainlabs-wallet-mining-v3
python3 - "$flybrain_backup" "$flybrain_upload" <<'PY'
import hashlib,json,os,pathlib,shutil,sqlite3,sys,tarfile
backup,upload=map(pathlib.Path,sys.argv[1:]);m=json.loads((upload/'manifest.json').read_text())
runtime=pathlib.Path('/etc/flypow/wallet-mining-v3-runtime.json');cfg=json.loads(runtime.read_text());authority=json.loads(pathlib.Path('/etc/flypow/authority-config.json').read_text())
assert cfg['cluster']=='devnet' and cfg['testOnly'] is True
assert not cfg.get('continuousSupplyConfig')
shutil.copy2(runtime,backup/'runtime-before.json')
# copy2 preserves mode/time but not ownership. Rollback uses cp -p, so retain
# the service account on the private snapshot as well as its exact bytes.
os.chown(backup/'runtime-before.json',runtime.stat().st_uid,runtime.stat().st_gid)
db=sqlite3.connect(cfg['database'],timeout=30);copy=sqlite3.connect(backup/'authority-before.sqlite');db.backup(copy);assert copy.execute('PRAGMA integrity_check').fetchone()[0]=='ok';copy.close()
tables=['goal_specs','goal_plan_progress','candidate_claims','round_winners','community_points_ledger']
baseline={t:db.execute('SELECT * FROM '+t+' ORDER BY rowid').fetchall() for t in tables}
(backup/'historical-rows.json').write_text(json.dumps(baseline,separators=(',',':'))+'\n');db.close()
with tarfile.open(backup/'sources-before.tar.gz','w:gz') as archive:
 for name,e in m['files'].items():
  if e['oldSha256'] is not None:archive.add(pathlib.Path('/opt/flypow')/name,arcname=name)
for name in m['files']:
 target=pathlib.Path('/opt/flypow')/name
 if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==m['files'][name]['newSha256']:continue
 temporary=target.with_name(target.name+'.supply-new');shutil.copyfile(upload/name,temporary);os.chmod(temporary,0o644);os.replace(temporary,target)
policy=json.loads((upload/'policy.example.json').read_text());policy.update(networkId=authority['networkId'],campaignId=authority['campaignId'],authorityId=cfg['authorityId'],adminKeyPath='/var/lib/flypow/authority/private/admin.key')
admin=pathlib.Path(policy['adminKeyPath']);assert admin.is_file() and admin.stat().st_uid==runtime.stat().st_uid
path=pathlib.Path('/etc/flypow/continuous-task-supply.json')
if not path.exists():
 path.write_text(json.dumps(policy,indent=2)+'\n');os.chmod(path,0o600);os.chown(path,runtime.stat().st_uid,runtime.stat().st_gid)
cfg['continuousSupplyConfig']=str(path);temporary=runtime.with_name(runtime.name+'.supply-new');temporary.write_text(json.dumps(cfg,indent=2)+'\n');shutil.copystat(runtime,temporary);os.chown(temporary,runtime.stat().st_uid,runtime.stat().st_gid);os.replace(temporary,runtime)
PY
gzip -t "$flybrain_backup/sources-before.tar.gz"
systemctl start flybrainlabs-wallet-mining-v3
flybrain_ok=0
for flybrain_attempt in {1..25}; do
    if curl --fail --silent -H 'Origin: https://flybrain.work' http://127.0.0.1:8789/api/mining/v3/configuration > "$flybrain_backup/wallet-public.json"; then flybrain_ok=1; break; fi
    sleep 1
done
[[ "$flybrain_ok" == 1 ]]
systemctl show flypow-target-authority flypow-target-verifier-serial flybrainlabs-community -p Id -p MainPID > "$flybrain_backup/other-services-after.txt"
cmp -s "$flybrain_backup/other-services-before.txt" "$flybrain_backup/other-services-after.txt"
python3 - "$flybrain_backup" "$flybrain_upload" <<'PY'
import hashlib,json,pathlib,sqlite3,sys,urllib.request
backup,upload=map(pathlib.Path,sys.argv[1:]);before=json.loads((backup/'runtime-before.json').read_text());after=json.loads(pathlib.Path('/etc/flypow/wallet-mining-v3-runtime.json').read_text())
assert {k:v for k,v in after.items() if k!='continuousSupplyConfig'}==before
m=json.loads((upload/'manifest.json').read_text())
for name,e in m['files'].items():assert hashlib.sha256((pathlib.Path('/opt/flypow')/name).read_bytes()).hexdigest()==e['newSha256']
for name,digest in m['retainedHashes'].items():assert hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()==digest
db=sqlite3.connect(after['database'],timeout=30);assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
for table,rows in json.loads((backup/'historical-rows.json').read_text()).items():assert [list(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY rowid LIMIT ?', (len(rows),))]==rows,'Historical evidence changed'
state=pathlib.Path('/var/lib/flypow/authority/continuous-task-supply.sqlite');assert state.is_file();s=sqlite3.connect('file:'+str(state)+'?mode=ro',uri=True)
assert s.execute('SELECT COUNT(*) FROM supply_items').fetchone()[0]==0
assert s.execute('SELECT COUNT(*) FROM supply_batches').fetchone()[0]==0
status=s.execute("SELECT value FROM supply_meta WHERE key='status'").fetchone()[0];assert status=='waiting-approved-tasks'
v=json.load(urllib.request.urlopen('http://127.0.0.1:8790/api/target-mining/v2/rounds/current',timeout=10));assert v['round'] is None and v['supply']['pendingGoals']==0
report={'passed':True,'backup':str(backup),'walletRestarts':1,'otherServicesRestarted':0,'sourceFilesInstalled':len(m['files']),'runtimeFinancialFieldsUnchanged':True,'historicalRowsPreserved':True,'dispatcherState':status,'scientificTasksPublished':0,'fundingTransactions':0,'walletGrantsRenewed':0,'roundCountUnchanged':True,'emptyCatalog':True}
(backup/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
PY
trap - ERR
