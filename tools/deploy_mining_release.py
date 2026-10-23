#!/usr/bin/env python3
"""Deploy a previously validated scoped release with verified backup and hashes."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import re

def deploy(a):
    build=json.loads(a.build_report.read_text());release=Path(build['release']);changes=build['changed_files'];paths=sorted(changes)
    validation=json.loads(a.validation.read_text())
    if build.get('schema')=='flybrainlabs-mining-asset-overlay-v1':
        # A small UI correction inherits the retained, validated data release.
        # Only independently copied modules and entry metadata may be replaced.
        if not paths or len(paths)>32 or any(not (re.fullmatch(r'assets/(?:[a-z0-9-]+|vendor/generated/factory-wallet-v4)\.mjs(?:\.gz)?',p) or p in ('mining/index.html','tasks/index.html','release.json')) for p in paths):raise ValueError('Overlay exceeds the mining asset scope')
        baseline=Path(build['baseline']);metadata=baseline/'release.json'
        if not baseline.is_dir() or hashlib.sha256(metadata.read_bytes()).hexdigest()!=build['baselineMetadataSha256']:raise ValueError('Retained baseline changed')
        if validation.get('schema')!='flybrainlabs-mining-asset-overlay-validation-v1' or validation.get('passed') is not True or validation.get('buildSha256')!=hashlib.sha256(a.build_report.read_bytes()).hexdigest():raise ValueError('Need validation of this exact asset overlay')
        if not build.get('atlas_unchanged') or not build.get('independent_copy'):raise ValueError('Overlay must retain scientific data and independent changed files')
        for name,c in changes.items():
            if (release/name).is_symlink() or (release/name).stat().st_nlink!=1:raise ValueError('Overlay baseline or independent file check failed')
            if c['old_sha256']:
                if not (baseline/name).is_file() or hashlib.sha256((baseline/name).read_bytes()).hexdigest()!=c['old_sha256']:raise ValueError('Overlay baseline check failed')
            elif (baseline/name).exists() or (baseline/name).is_symlink():raise ValueError('New overlay path already exists in baseline')
    else:
        if not build['atlas_unchanged'] or not build['independent_copy']:raise ValueError('Need verified independent full release')
        if not (validation.get('static_only') or validation.get('oauth_bridge_verified')) or validation.get('types')!=11751:raise ValueError('Need successful complete-atlas validation and an explicitly reviewed optional OAuth bridge')
    for name,c in changes.items():
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unsafe release path')
        if hashlib.sha256((release/name).read_bytes()).hexdigest()!=c['new_sha256']:raise ValueError('Release changed after verification')
    ssh=['ssh','-T','-F',str(a.ssh_config),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=4']
    config=dict(line.split(None,1) for line in subprocess.check_output(ssh+['-G',a.host],text=True).splitlines() if ' ' in line)
    if (config['hostname'],config['user'],config['port'])!=('server241.web-hosting.com','flybwhiv','21098'):raise ValueError('Unexpected deployment destination')
    webroot='/home/flybwhiv/public_html';backup_root='/home/flybwhiv/flypow-deploy'
    preconditions=f'set -e; test "$(id -un)" = flybwhiv; test -d {webroot}; test ! -L {webroot}; test ! -L {backup_root}; '
    def remote(command):return subprocess.check_output(ssh+[a.host,preconditions+command],text=True)
    def hashes(names):
        if not names:return {}
        result=remote(f'cd {webroot}; '+shlex.join(['sha256sum','--']+names));return {line.split(None,1)[1].strip():line.split()[0] for line in result.splitlines()}
    existing=[p for p in paths if changes[p]['old_sha256']];added=[p for p in paths if not changes[p]['old_sha256']]
    if hashes(existing)!={p:changes[p]['old_sha256'] for p in existing}:raise ValueError('Remote baseline changed; inspect before deploying')
    if added:remote('for flypow_release_path in '+shlex.join(webroot+'/'+path for path in added)+'; do test ! -e "$flypow_release_path"; done')
    identifier='mining-optimization-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+str(os.getpid());backup=backup_root+'/'+identifier+'/before.tar.gz'
    backup_out=remote(f'umask 077; test ! -e {backup_root}/{identifier}; mkdir -p {backup_root}/{identifier}; tar -czf {backup} -C {webroot} -- '+shlex.join(existing)+f'; gzip -t {backup}; sha256sum {backup}')
    backup_hash=backup_out.split()[0];print('Backup verified: '+backup,flush=True)
    listfile=a.report.with_suffix('.files.txt');listfile.write_text('\n'.join(paths)+'\n')
    subprocess.run(['rsync','-rtz','--checksum','--delay-updates','--itemize-changes','--files-from='+str(listfile),'-e',shlex.join(ssh),str(release)+'/',a.host+':'+webroot+'/'],check=True)
    if hashes(paths)!={p:changes[p]['new_sha256'] for p in paths}:raise ValueError('Remote hashes do not match release')
    report={'schema':'flypow-mining-deploy-v1','release':str(release),'backup':backup,'backup_sha256':backup_hash,'backup_gzip_verified':True,'new_paths_for_rollback':added,'existing_paths_backed_up':existing,'remote_before_matches_retained':True,'remote_after_matches_release':True,'changed_files':len(paths),'method':'scoped checksum rsync delay-updates; existing files archived; no atlas replacement or deletion'}
    a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'verified':True,'changed_files':len(paths),'backup':backup}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build-report',type=Path,required=True);p.add_argument('--validation',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--ssh-config',type=Path,default=Path('/workspace/.ssh/config'));p.add_argument('--host',default='flybrain-work');deploy(p.parse_args())
