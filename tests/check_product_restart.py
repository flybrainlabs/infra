#!/usr/bin/env python3
"""Check the deployed product across a real service restart, without exporting receipts.

Run only on an authorized node, after mining has stopped. The ticket proof remains
in memory; the report contains public identities and boolean persistence checks.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener


def main(args):
    proof = json.loads(Path(args.ticket).read_text())
    opener = build_opener(ProxyHandler({}))
    base = args.api.rstrip('/')
    report = {
        'schema': 'flybrain-product-restart-acceptance-v2',
        'api': base,
        'checks': [],
        'formalFunds': False,
        'privateFieldsExported': False,
    }
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)

    def fetch(path, body=None):
        request = Request(base + path,
                          data=None if body is None else json.dumps(body).encode(),
                          headers={'Content-Type': 'application/json'})
        with opener.open(request, timeout=30) as response:
            return json.load(response)

    def capture():
        ready = fetch('/api/target-mining/v2/readiness')
        assert ready['authorityId'] == args.authority, 'Unexpected authority identity'
        assert ready['payment'] is False and ready['rewards'] is False
        assert ready['database']['journalMode'].lower() == 'wal'
        winners, before = {}, 0
        while True:
            history = fetch('/api/target-mining/v2/rounds/history?limit=100&before=' + str(before))
            assert history['authorityId'] == args.authority
            for row in history['rounds']:
                if row['winner'] is not None:
                    winners[row['roundId']] = row['winner']
            cursor = history['nextBefore']
            if cursor is None:
                break
            assert cursor > 0 and (before == 0 or cursor < before)
            before = cursor
        manifest = fetch('/api/product/manifest')
        assert manifest['economicPolicy']['paymentEnabled'] is False
        assert manifest['economicPolicy']['rewardEnabled'] is False
        result = fetch('/api/results/' + args.result)
        files = [(f['name'], f['sha256'], f['bytes']) for f in result['files']]
        ticket = fetch('/api/service-requests/lookup', proof)
        assert ticket['status'] == 'budget-required', 'Expected an unfunded confirmed engineering quote'
        assert ticket['quotes'] and ticket['quotes'][0]['confirmed'] is True
        return {
            'authority': ready['authorityId'],
            'model': ready['modelIdentity'],
            'archiveBytes': ready['archiveSpace']['reservedBytes'],
            'winners': winners,
            'result': result['id'],
            'files': files,
            'ticket': ticket,
        }

    try:
        prior = capture()
        subprocess.run([
            'ssh', '-T', '-F', args.ssh_config, '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=yes', args.ssh_alias,
            'sudo systemctl restart flypow-target-authority flypow-target-verifier-serial',
        ], check=True, capture_output=True, timeout=90)
        deadline = time.monotonic() + 90
        while True:
            try:
                after = capture()
                break
            except (OSError, ValueError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(2)
        assert prior['authority'] == after['authority']
        assert prior['model'] == after['model']
        assert prior['winners'] == after['winners'], 'Winner history changed'
        assert prior['archiveBytes'] == after['archiveBytes'], 'Private archive declarations changed'
        assert prior['result'] == after['result'] and prior['files'] == after['files']
        assert prior['ticket'] == after['ticket'], 'Private request or quote changed'
        report.update(authorityId=after['authority'], winnerCount=len(after['winners']),
                      publicResultId=after['result'], publicFiles=len(after['files']),
                      privateArchiveBytesPreserved=True, privateTicketAndQuotePreserved=True)
        report['checks'] = [
            'Real cloud service restart preserves the pinned authority and frozen model identity',
            'All existing winner receipts and private archive declarations remain unchanged',
            'Published result and all twelve file roots remain unchanged',
            'Private engineering request, confirmed quote and budget-required state remain unchanged',
            'Formal payments and rewards remain disabled before and after restart',
        ]
        print(json.dumps({'passed': len(report['checks']), 'winnerCount': report['winnerCount']}))
    except Exception as error:
        # Avoid copying private server responses or the receipt proof to a report.
        report['errorType'] = type(error).__name__
        raise
    finally:
        output.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api', default='https://43.161.219.89.sslip.io')
    parser.add_argument('--ssh-alias', default='flypow-node')
    parser.add_argument('--ssh-config', default='/workspace/.ssh/config')
    parser.add_argument('--ticket', required=True)
    parser.add_argument('--authority', required=True)
    parser.add_argument('--result', required=True)
    parser.add_argument('--report', required=True)
    main(parser.parse_args())
