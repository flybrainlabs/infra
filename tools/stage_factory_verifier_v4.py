#!/usr/bin/env python3
"""Install reviewed V4 verifier sources beside existing services, without activation."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import tempfile


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upload', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((args.upload / 'manifest.json').read_text())
    require(manifest['schema'] == 'flybrainlabs-factory-verifier-stage-v4'
            and manifest['activate'] is False
            and re.fullmatch(r'[a-f0-9]{64}', manifest['programSha256']), 'Unexpected staging scope')
    root = Path('/opt/flypow/task-factory-v4/releases') / manifest['programSha256'][:16]
    files = manifest['files']
    require('tools/factory_verifier_v4.mjs' in files and len(files) < 128, 'Verifier import graph required')
    with tarfile.open(args.upload / 'bundle.tar.gz') as archive:
        members = archive.getmembers()
        require(len(members) == len(files) and len({m.name for m in members}) == len(files), 'Archive manifest mismatch')
        for member in members:
            path = PurePosixPath(member.name)
            require(member.isfile() and not path.is_absolute() and '..' not in path.parts
                    and path.parts[0] in ('web', 'tools') and path.suffix == '.mjs'
                    and member.name in files, 'Unsafe source path')
            data = archive.extractfile(member).read()
            require(len(data) <= 2 * 1024 * 1024
                    and hashlib.sha256(data).hexdigest() == files[member.name], 'Reviewed source hash mismatch')
    services = ['flybrainlabs-wallet-mining-v3', 'flypow-target-authority',
                'flypow-target-verifier-serial', 'flybrainlabs-community']
    def call(*argv):
        return subprocess.check_output(argv, text=True, stderr=subprocess.PIPE).strip()
    before = call('systemctl', 'show', *services, '-p', 'Id', '-p', 'MainPID')
    require(call('systemctl', 'is-active', *services).splitlines() == ['active'] * 4, 'Existing services must remain healthy')
    runtime = json.loads(Path('/etc/flypow/wallet-mining-v3-runtime.json').read_text())
    require(runtime['testOnly'] is True and runtime['cluster'] == 'devnet', 'Only the existing Devnet node is supported')
    require(runtime['programId'] == manifest['programId'], 'Existing node program mismatch')
    if not args.apply:
        print(json.dumps({'preflightPassed': True, 'sourceFiles': len(files), 'servicesRestarted': 0, 'activated': False}))
        return
    require(os.geteuid() == 0, 'Installation requires the authorized node administrator')
    root.parent.mkdir(parents=True, exist_ok=True)
    require(not root.is_symlink(), 'Unexpected release symlink')
    if not root.exists():
        with tempfile.TemporaryDirectory(prefix='factory-v4-stage-', dir=root.parent) as temporary:
            stage = Path(temporary) / 'release'
            stage.mkdir()
            with tarfile.open(args.upload / 'bundle.tar.gz') as archive:
                for member in archive.getmembers():
                    target = stage / member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.extractfile(member).read())
                    target.chmod(0o644)
            (stage / 'node_modules').symlink_to('/opt/flypow/node_modules', target_is_directory=True)
            for name in files:
                subprocess.run(['/opt/flypow/runtime/node/bin/node', '--check', str(stage / name)],
                               check=True, capture_output=True, text=True)
            code = "await import(" + json.dumps((stage / 'tools/factory_verifier_v4.mjs').as_uri()) + ")"
            subprocess.run(['/opt/flypow/runtime/node/bin/node', '--input-type=module', '-e', code],
                           check=True, capture_output=True, text=True)
            stage.rename(root)
    for name, digest in files.items():
        target = root / name
        require(target.is_file() and not target.is_symlink()
                and hashlib.sha256(target.read_bytes()).hexdigest() == digest, 'Installed source mismatch')
    verifier = json.loads(Path('/etc/flypow/verifier-serial-runtime.json').read_text())
    code = ("import {getModelReadiness} from " + json.dumps((root / 'tools/candidate_verifier_v2.mjs').as_uri())
            + ";console.log(JSON.stringify(await getModelReadiness(" + json.dumps(verifier['binary'])
            + ',' + json.dumps(verifier['modelDir']) + ')))')
    ready = json.loads(call('/opt/flypow/runtime/node/bin/node', '--input-type=module', '-e', code))
    require(ready.get('nativeBinaryReady') is True
            and ready.get('graphRoot') == manifest['graphRoot']
            and ready.get('modelDataRoot') == manifest['modelDataRoot'], 'Existing complete model is not ready')
    require(call('systemctl', 'show', *services, '-p', 'Id', '-p', 'MainPID') == before, 'An existing service restarted')
    receipt = {'schema': 'flybrainlabs-factory-verifier-stage-acceptance-v4',
               'status': 'installed-inactive-awaiting-approved-factory-configuration',
               'sourceFiles': len(files), 'allSourceHashesVerified': True,
               'sourceImportPassed': True, 'completeModelReadinessPassed': True,
               'release': str(root), 'servicesRestarted': 0, 'existingPrivateConfigurationChanged': False,
               'databaseMigrations': 0, 'newPublicTasks': 0, 'newPublicFbwBudgetAtoms': '0',
               'verifierActivated': False, 'completeReplayExecuted': False,
               'independentOperatorsEstablished': False}
    (root / 'staging-acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
