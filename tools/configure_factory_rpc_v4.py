#!/usr/bin/env python3
"""Verify Devnet identities before switching the original node's private RPCs."""
import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time
import urllib.request
from urllib.parse import urlsplit

V4 = Path('/etc/flypow/task-factory-v4-runtime.json')
WALLET = Path('/etc/flypow/wallet-mining-v3-runtime.json')
SERVICES = ['flybrainlabs-wallet-mining-v3', 'flybrainlabs-task-factory-v4']
PUBLIC_PROVIDERS = {'onfinality': 'https://solana-devnet.api.onfinality.io/public'}
PROGRAM = '5yxjnH1PSk8iQKfK3ejG4jfSkewkTKfcpJygojdb6sam'


def replace(path, value):
    previous = path.stat()
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name + '.rpc-')
    try:
        with os.fdopen(fd, 'w') as target:
            json.dump(value, target, indent=2)
            target.write('\n')
            target.flush()
            os.fsync(target.fileno())
        os.chmod(name, stat.S_IMODE(previous.st_mode))
        os.chown(name, previous.st_uid, previous.st_gid)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def get_json(url, origin):
    request = urllib.request.Request(url, headers={'Origin': origin})
    with urllib.request.urlopen(request, timeout=3) as response:
        return json.load(response)


def probe(provider, deployment):
    # The URL enters the child environment, never command arguments or reports.
    source = """
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {readerForDeployment} from '/opt/flypow/task-factory-v4/current/web/task-factory-client-v4.mjs';
const {Connection,PublicKey}=createRequire('/opt/flypow/task-factory-v4/current/check.cjs')('@solana/web3.js');
const c=JSON.parse(process.env.FACTORY_RPC_PROBE);
const connection=new Connection(c.url,{commitment:'finalized',disableRetryOnRateLimit:true,
  fetch:(url,options)=>fetch(url,{...options,signal:AbortSignal.timeout(12000)})});
const reader=readerForDeployment(c.deployment,connection),f=await reader.factory();
const program=await connection.getAccountInfo(reader.program,'finalized');
const data=await connection.getAccountInfo(new PublicKey('GmTNV9aBMjWeEEsZxBhRAFhahFu2ivUssy1MdHVXam64'),'finalized');
if(!program?.executable||f.budget!==160000000000n||f.count!==8||data?.data.readUInt32LE(0)!==3||
 createHash('sha256').update(data.data.subarray(45,45+404944)).digest('hex')!==
 '606eac05dda6210fc6cfa68f677060f3545b44aa8118983a1334c44e261a33e8')
 throw new Error('Finalized provider scope mismatch');
console.log(JSON.stringify({devnetGenesisVerified:true,actualFactoryAndBudgetVerified:true,
 deployedExecutableHashVerified:true,activeIndex:f.activeIndex,chainTransactions:0}));
"""
    result = subprocess.run(
        ['/opt/flypow/runtime/node/bin/node', '--input-type=module', '-e', source],
        env={**os.environ, 'FACTORY_RPC_PROBE': json.dumps({'url': provider, 'deployment': deployment})},
        capture_output=True, text=True, timeout=90,
    )
    if result.returncode:
        raise RuntimeError('Provider identity probe failed; private upstream was not logged')
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--public-provider', choices=sorted(PUBLIC_PROVIDERS))
    group.add_argument('--provider-config', type=Path, help='Private mode 0600 JSON with rpcUpstream')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.provider_config:
        info = args.provider_config.stat()
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('Provider configuration must be a private regular file')
        provider = json.loads(args.provider_config.read_text())['rpcUpstream']
    else:
        provider = PUBLIC_PROVIDERS[args.public_provider]
    parsed = urlsplit(provider)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or any(c.isspace() for c in provider):
        raise ValueError('An HTTPS RPC upstream without user information is required')
    v4 = json.loads(V4.read_text())
    wallet = json.loads(WALLET.read_text())
    assert v4['deployment']['cluster'] == wallet['cluster'] == 'devnet'
    assert v4['deployment']['programId'] == wallet['programId'] == PROGRAM
    origin = 'https://flybrain.work'
    assert origin in wallet['origins'] and origin in v4['origins']
    checked = probe(provider, v4['deployment'])
    report = {
        'schema': 'flybrainlabs-v4-rpc-switch', 'providerHost': parsed.hostname,
        'probe': checked, 'mainnet': False, 'newPaidSubscription': False,
        'privateProviderInput': bool(args.provider_config), 'credentialsLogged': False,
    }
    if not args.apply:
        print(json.dumps({**report, 'applied': False}))
        return
    assert os.geteuid() == 0
    health = get_json('http://127.0.0.1:8792/api/task-factory/v4/health', origin)
    if health.get('verifier', {}).get('status') == 'replaying':
        raise RuntimeError('Wait for the current native replay before changing RPC')
    backup = Path('/var/backups/flypow') / ('rpc-v4-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    backup.mkdir(mode=0o700)
    for path in [V4, WALLET]:
        shutil.copy2(path, backup / path.name)
    updated_v4 = {**v4, 'rpcUpstream': provider}
    updated_wallet = {**wallet, 'rpc': wallet['apiBase'] + '/api/mining/v3/rpc', 'rpcUpstream': provider}
    try:
        replace(V4, updated_v4)
        replace(WALLET, updated_wallet)
        subprocess.run(['systemctl', 'restart', *SERVICES], check=True, capture_output=True, timeout=120)
        for attempt in range(45):
            try:
                configured = get_json('http://127.0.0.1:8789/api/mining/v3/configuration', origin)
                health = get_json('http://127.0.0.1:8792/api/task-factory/v4/health', origin)
                assert configured['programId'] == PROGRAM and configured['rpc'] == updated_wallet['rpc']
                assert health['taskAuthority'] == 'contract' and health['transportReady']
                break
            except Exception:
                if attempt == 44:
                    raise
                time.sleep(1)
    except BaseException:
        for path in [V4, WALLET]:
            replace(path, json.loads((backup / path.name).read_text()))
        subprocess.run(['systemctl', 'restart', *SERVICES], check=True, capture_output=True, timeout=120)
        raise RuntimeError('Provider switch failed; original private transports restored') from None
    print(json.dumps({**report, 'applied': True, 'existingDatabaseAndGrantsRetained': True,
                      'publicGatewayUrlsUnchanged': True, 'taskAndFinancialIdentitiesUnchanged': True,
                      'backendRestarts': len(SERVICES)}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Provider failures can include an API key in their underlying exception.
        print(json.dumps({'applied': False, 'errorClass': type(error).__name__, 'credentialsLogged': False}))
        raise SystemExit(1)
