#!/usr/bin/env python3
"""Apply the owner's scoped server update while retaining publication status."""
import argparse
from contextlib import closing
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.request

TARGET = Path('/opt/flypow/tools/continuous_task_supply.mjs')
RUNTIME = Path('/etc/flypow/wallet-mining-v3-runtime.json')
NODE = '/opt/flypow/runtime/node/bin/node'
SERVICE = 'flybrainlabs-wallet-mining-v3'
OTHERS = ['flypow-target-authority', 'flypow-target-verifier-serial', 'flybrainlabs-community']
TABLES = ['goal_specs', 'goal_plan_progress', 'candidate_claims', 'round_winners', 'community_points_ledger']


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def call(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE).strip()


def retained(manifest):
    for path, expected in manifest['retainedHashes'].items():
        require(digest(path) == expected, 'Retained configuration or dependency changed: ' + path)


def read_db(path):
    return sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True, timeout=30)


def supply_state(policy):
    with closing(read_db(policy['stateDatabase'])) as db:
        counts = {table: db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                  for table in ['supply_catalogs', 'supply_items', 'supply_batches']}
        meta = dict(db.execute("SELECT key,value FROM supply_meta WHERE key IN ('status','eventCursor','checkedAt')"))
    require(not any(counts.values()), 'This scoped upgrade requires the observed empty catalog')
    return {'counts': counts, 'meta': meta}


def authority_state():
    with urllib.request.urlopen('http://127.0.0.1:8790/api/target-mining/v2/rounds/current', timeout=10) as response:
        value = json.load(response)
    supply = value['supply']
    require(value.get('round') is None and supply['pendingGoals'] == 0 and supply['remainingUnopenedGoals'] == 0,
            'Mining state changed; inspect before a scoped upgrade')
    return {key: supply[key] for key in ['pendingGoals', 'remainingUnopenedGoals', 'solvedGoals', 'planHash', 'planRevision']}


def health():
    require(call('systemctl', 'is-active', SERVICE) == 'active', 'Wallet service is not active')
    request = urllib.request.Request('http://127.0.0.1:8789/api/mining/v3/configuration',
                                     headers={'Origin': 'https://flybrain.work'})
    with urllib.request.urlopen(request, timeout=3) as response:
        require(response.status == 200, 'Wallet configuration is unavailable')


def atomic_copy(source, target):
    handle, temporary = tempfile.mkstemp(prefix=target.name + '.upgrade-', dir=target.parent)
    try:
        with os.fdopen(handle, 'wb') as output:
            output.write(source.read_bytes())
            output.flush()
            os.fsync(output.fileno())
        shutil.copystat(target, temporary)
        stat = target.stat()
        os.chown(temporary, stat.st_uid, stat.st_gid)
        os.replace(temporary, target)
        directory = os.open(target.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upload', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    manifest = json.loads((args.upload / 'manifest.json').read_text())
    source = args.upload / 'continuous_task_supply.mjs'
    require(manifest['schema'] == 'flybrain-immediate-task-supply-upgrade-v1', 'Unexpected manifest')
    require(manifest['file'] == 'tools/continuous_task_supply.mjs', 'Unexpected source target')
    require(digest(source) == manifest['newSha256'], 'Uploaded source changed')
    require(digest(TARGET) in [manifest['oldSha256'], manifest['newSha256']], 'Installed dispatcher changed')
    retained(manifest)
    config = json.loads(RUNTIME.read_text())
    require(config['cluster'] == 'devnet' and config['testOnly'] is True, 'Only the existing Devnet runtime is authorized')
    policy = json.loads(Path(config['continuousSupplyConfig']).read_text())
    require(not Path(policy['catalogPath']).exists(), 'A catalog was added; inspect before upgrading')
    supply_state(policy)
    before_authority = authority_state()
    health()
    with tempfile.TemporaryDirectory(prefix='flybrain-immediate-import-') as temporary:
        root = Path(temporary)
        (root / 'tools').mkdir()
        shutil.copyfile(source, root / 'tools/continuous_task_supply.mjs')
        (root / 'web').symlink_to('/opt/flypow/web', target_is_directory=True)
        (root / 'tools/target_dev_identity.mjs').symlink_to('/opt/flypow/tools/target_dev_identity.mjs')
        subprocess.run([NODE, '--check', str(source)], check=True, capture_output=True)
        subprocess.run([NODE, '--input-type=module', '-e', 'await import(' + json.dumps((root / 'tools/continuous_task_supply.mjs').as_uri()) + ')'],
                       check=True, capture_output=True)
    if not args.apply:
        print(json.dumps({'preflightPassed': True, 'liveSourceChanged': False, 'servicesRestarted': 0}))
        return
    require(os.geteuid() == 0, 'Apply requires the authorized node administrator')
    identity = manifest['identity']
    require(identity.get('sshVerified') is True and identity.get('sshLogin') == 'flybrainlabs', 'The dedicated project SSH identity is required')
    authorization = manifest.get('deploymentAuthorization', {})
    require(authorization.get('explicitOwnerRequest') is True
            and authorization.get('scope') == 'existing-node-single-dispatcher-update'
            and manifest['sourceCommits']['node'] == '006b875ef10940e62333382a1ce3ba3da81822fe', 'The scoped server deployment must be authorized')
    # This tool performs no GitHub mutation and does not mark an unpublished
    # component as an available pinned release. Repository publication retains
    # its separate matching SSH/API identity and remote verification gates.
    with open('/run/lock/flybrainlabs-continuous-supply.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        retained(manifest)
        require(digest(TARGET) in [manifest['oldSha256'], manifest['newSha256']], 'Concurrent dispatcher change')
        if digest(TARGET) == manifest['newSha256']:
            print(json.dumps({'alreadyInstalled': True, 'sourceSha256': manifest['newSha256'], 'servicesRestarted': 0}))
            return
        backup = Path('/var/backups/flypow') / ('immediate-supply-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + str(os.getpid()))
        backup.mkdir(mode=0o700)
        previous = backup / 'continuous_task_supply.before.mjs'
        shutil.copy2(TARGET, previous)
        other_pids = call('systemctl', 'show', *OTHERS, '-p', 'Id', '-p', 'MainPID')
        try:
            subprocess.run(['systemctl', 'stop', SERVICE], check=True, capture_output=True)
            retained(manifest)
            require(digest(TARGET) == manifest['oldSha256'], 'Dispatcher changed after preflight')
            require(authority_state() == before_authority, 'Authority advanced before replacement')
            history = {}
            for label, path in [('authority', config['database']), ('supply', policy['stateDatabase'])]:
                with closing(read_db(path)) as original, closing(sqlite3.connect(backup / (label + '.sqlite'))) as snapshot:
                    original.backup(snapshot)
                    require(snapshot.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Database backup failed')
                    if label == 'authority':
                        history = {table: snapshot.execute('SELECT * FROM ' + table + ' ORDER BY rowid').fetchall() for table in TABLES}
            supply_state(policy)
            atomic_copy(source, TARGET)
            require(digest(TARGET) == manifest['newSha256'], 'Atomic source verification failed')
            started = int(time.time())
            subprocess.run(['systemctl', 'start', SERVICE], check=True, capture_output=True)
            for attempt in range(25):
                try:
                    health()
                    state = supply_state(policy)
                    require(state['meta'].get('status') == 'waiting-approved-tasks' and int(state['meta'].get('checkedAt', 0)) >= started,
                            'Updated dispatcher has not reported healthy idle state')
                    break
                except Exception:
                    if attempt == 24:
                        raise
                    time.sleep(1)
            retained(manifest)
            require(authority_state() == before_authority, 'Authority state changed during upgrade')
            require(call('systemctl', 'show', *OTHERS, '-p', 'Id', '-p', 'MainPID') == other_pids, 'Another service restarted')
            with closing(read_db(config['database'])) as db:
                for table, rows in history.items():
                    require(db.execute('SELECT * FROM ' + table + ' ORDER BY rowid LIMIT ?', (len(rows),)).fetchall() == rows,
                            'Historical evidence changed: ' + table)
            report = {'deployed': True, 'sourceSha256': digest(TARGET), 'backup': str(backup), 'walletRestarts': 1,
                      'otherServicesRestarted': 0, 'historicalRowsPreserved': True, 'privateConfigurationUnchanged': True,
                      'newTasks': 0, 'newFunding': 0, 'dispatcherStatus': state['meta']['status']}
            (backup / 'acceptance.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report))
        except BaseException:
            subprocess.run(['systemctl', 'stop', SERVICE], check=True, capture_output=True)
            atomic_copy(previous, TARGET)
            require(digest(TARGET) == manifest['oldSha256'], 'Rollback source verification failed')
            subprocess.run(['systemctl', 'start', SERVICE], check=True, capture_output=True)
            raise RuntimeError('Upgrade failed; previous source restored; databases and private state retained') from None


if __name__ == '__main__':
    main()
