#!/usr/bin/env python3
"""Validate a private Devnet RPC and atomically configure the existing gateway."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import tempfile
import urllib.request

GENESIS = 'EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG'


def configure(runtime, private_rpc, *, dry_run=False, request=None):
    from urllib.parse import urlsplit
    if runtime.is_symlink() or private_rpc.is_symlink():
        raise ValueError('Use direct private configuration files')
    source_stat = private_rpc.stat()
    if stat.S_IMODE(source_stat.st_mode) & 0o077:
        raise ValueError('RPC input must have private file permissions')
    original = runtime.read_bytes()
    config = json.loads(original)
    private = json.loads(private_rpc.read_text())
    endpoint = private.get('rpcUpstream')
    parsed = urlsplit(endpoint or '')
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('Private RPC must use HTTPS without URL user credentials or fragments')
    api = urlsplit(config.get('apiBase', ''))
    if config.get('schema') != 'flybrainlabs-wallet-mining-config-v3' or config.get('cluster') != 'devnet' or config.get('genesisHash') != GENESIS or api.scheme != 'https' or config['apiBase'] != api.scheme + '://' + api.netloc or api.username or api.password:
        raise ValueError('Keep the existing pinned Devnet gateway identity')

    def call(method, params):
        body = dict(jsonrpc='2.0', id=1, method=method, params=params)
        try:
            if request:
                response = request(endpoint, body)
            else:
                req = urllib.request.Request(endpoint, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'}, method='POST')
                class NoRedirect(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self, req, fp, code, msg, headers, newurl):
                        return None
                with urllib.request.build_opener(NoRedirect).open(req, timeout=15) as result:
                    response = json.loads(result.read(262145))
            if response.get('jsonrpc') != '2.0' or response.get('id') != 1 or 'error' in response:
                raise ValueError()
            return response['result']
        except Exception:
            raise ValueError('Private RPC probe failed; the runtime was not changed') from None

    if call('getGenesisHash', []) != GENESIS:
        raise ValueError('Private RPC is not Solana Devnet; the runtime was not changed')
    quote = call('getMinimumBalanceForRentExemption', [1024, {'commitment': 'finalized'}])
    if isinstance(quote, bool) or not isinstance(quote, int) or quote <= 0:
        raise ValueError('Private RPC did not supply a valid current rent quote')
    updated = {**config, 'rpc': config['apiBase'] + '/api/mining/v3/rpc', 'rpcUpstream': endpoint}
    unchanged = {k: v for k, v in config.items() if k not in {'rpc', 'rpcUpstream'}}
    if unchanged != {k: v for k, v in updated.items() if k not in {'rpc', 'rpcUpstream'}}:
        raise ValueError('A nontransport runtime field changed')
    report = dict(schema='flybrainlabs-wallet-rpc-configuration-v1', genesisVerified=True,
                  rentQuoteVerified=True, gateway=updated['rpc'], changed=updated != config, dryRun=dry_run,
                  frozenPlanPreserved=True, chainTransactions=0)
    if dry_run or updated == config:
        return report
    # Detect an intervening operator edit before preserving the exact baseline.
    if runtime.read_bytes() != original:
        raise ValueError('Private runtime changed during validation')
    before = runtime.stat()
    suffix = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + str(os.getpid())
    backup = runtime.with_name(runtime.name + '.before-rpc-' + suffix)
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as saved:
        saved.write(original)
        saved.flush()
        os.fsync(saved.fileno())
    fd, temporary = tempfile.mkstemp(prefix='.wallet-rpc-', dir=runtime.parent)
    try:
        os.fchmod(fd, 0o600)
        os.fchown(fd, before.st_uid, before.st_gid)
        with os.fdopen(fd, 'w') as target:
            json.dump(updated, target, indent=2)
            target.write('\n')
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, runtime)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    report['backup'] = str(backup)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=Path('/etc/flypow/wallet-mining-v3-runtime.json'))
    parser.add_argument('--private-rpc-file', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(configure(args.runtime, args.private_rpc_file, dry_run=args.dry_run)))
    except (ValueError, OSError):
        # URL-bearing exception strings never enter stdout or the service journal.
        print(json.dumps(dict(passed=False, code='RPC_CONFIGURATION_NOT_APPLIED')))
        raise SystemExit(1)
