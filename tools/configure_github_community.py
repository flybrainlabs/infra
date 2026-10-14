#!/usr/bin/env python3
"""Install private GitHub OAuth configuration without printing credentials."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess


REMOTE = r'''
import grp,json,os,pathlib,sys
p=pathlib.Path('/etc/flypow/github-community.json');config=json.load(sys.stdin)
assert config['callbackUrl']=='https://flybrain.work/api/auth/github/callback'
assert config['engagementRewardsEnabled'] is False
if p.exists():
 old=json.loads(p.read_text())
 if old.get('encryptionKey')!=config['encryptionKey']:raise SystemExit('Existing token encryption key differs; explicit reconciliation required')
 if old==config:
  print(json.dumps({'configured':True,'changed':False,'path':str(p),'engagementRewardsEnabled':False}));sys.exit(0)
t=p.with_name(p.name+'.new');fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o640)
with os.fdopen(fd,'w') as f:json.dump(config,f,indent=2);f.write(chr(10));f.flush();os.fsync(f.fileno())
os.chown(t,0,grp.getgrnam('flypow').gr_gid);os.chmod(t,0o640);os.replace(t,p)
print(json.dumps({'configured':True,'changed':True,'path':str(p),'fileMode':'0640','owner':'root:flypow','engagementRewardsEnabled':False}))
'''


def configure(a):
    if a.host != 'flypow-node':
        raise ValueError('Use the original authorized node alias')
    for parent in [a.input.parent, *a.input.parent.parents]:
        if (parent / '.git').exists():
            raise ValueError('OAuth input must be outside repositories')
    if a.input.stat().st_mode & 0o077:
        raise ValueError('Private OAuth input permissions are too broad')
    value = json.loads(a.input.read_text())
    client_id, client_secret = value.get('client_id'), value.get('client_secret')
    if not isinstance(client_id, str) or not isinstance(client_secret, str) or not client_id or not client_secret:
        raise ValueError('Private OAuth input is incomplete')
    a.key.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not a.key.exists():
        fd = os.open(a.key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as file:
            file.write(secrets.token_hex(32) + '\n')
    if a.key.stat().st_mode & 0o077:
        raise ValueError('Private token key permissions are too broad')
    key = a.key.read_text().strip()
    if len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
        raise ValueError('Invalid private token key')
    ssh = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes']
    actual = dict(line.split(None, 1) for line in subprocess.check_output(ssh + ['-G', a.host], text=True).splitlines() if ' ' in line)
    if (actual['hostname'], actual['user']) != ('43.161.219.89', 'ubuntu'):
        raise ValueError('Unexpected original node destination')
    config = dict(clientId=client_id, clientSecret=client_secret, encryptionKey=key, callbackUrl='https://flybrain.work/api/auth/github/callback', bindingEnabled=True, engagementRewardsEnabled=False)
    import shlex
    result = subprocess.run(ssh + [a.host, 'sudo python3 -c ' + shlex.quote(REMOTE)], input=json.dumps(config), text=True, check=True, capture_output=True)
    return json.loads(result.stdout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--key', type=Path, required=True)
    parser.add_argument('--host', default='flypow-node')
    args = parser.parse_args()
    try:
        print(json.dumps(configure(args)))
    except Exception as error:
        raise SystemExit('Private GitHub configuration failed: ' + type(error).__name__ + '; no credentials are printed') from None
