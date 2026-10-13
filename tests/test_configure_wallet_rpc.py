"""RPC configuration preserves the frozen plan and never exposes provider keys."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('configure_rpc', Path(__file__).resolve().parents[1] / 'tools/configure_wallet_rpc_v3.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.runtime = self.root / 'runtime.json'
        self.private = self.root / 'private.json'
        self.original = dict(schema='flybrainlabs-wallet-mining-config-v3', cluster='devnet',
                             genesisHash=module.GENESIS, apiBase='https://node.example', rpc='https://api.devnet.solana.com',
                             programId='existing-program', mint='existing-mint', budgetAtoms='200000000',
                             units=[{'economicTaskId': 'existing-unit'}], relayerKeypair='/private/existing-signer',
                             database='/private/existing.sqlite', defaultGrant={'maxResults': '2'})
        self.runtime.write_text(json.dumps(self.original))
        self.endpoint = 'https://provider.invalid/?api-key=fixture-private-key'
        self.private.write_text(json.dumps(dict(rpcUpstream=self.endpoint)))
        self.private.chmod(0o600)
        self.calls = []

    def tearDown(self):
        self.directory.cleanup()

    def request(self, endpoint, body):
        self.assertEqual(endpoint, self.endpoint)
        self.calls.append(body['method'])
        return dict(jsonrpc='2.0', id=1, result=module.GENESIS if body['method'] == 'getGenesisHash' else 1000)

    def test_atomic_apply_and_idempotency(self):
        baseline = self.runtime.read_bytes()
        report = module.configure(self.runtime, self.private, request=self.request)
        updated = json.loads(self.runtime.read_text())
        for key, value in self.original.items():
            if key != 'rpc':
                self.assertEqual(updated[key], value)
        self.assertEqual(updated['rpc'], self.original['apiBase'] + '/api/mining/v3/rpc')
        self.assertEqual(updated['rpcUpstream'], self.endpoint)
        self.assertEqual(Path(report['backup']).read_bytes(), baseline)
        self.assertEqual(self.runtime.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(self.endpoint, json.dumps(report))
        self.assertEqual(self.calls, ['getGenesisHash', 'getMinimumBalanceForRentExemption'])
        before = self.runtime.read_bytes()
        self.assertFalse(module.configure(self.runtime, self.private, request=self.request)['changed'])
        self.assertEqual(before, self.runtime.read_bytes())
        self.assertEqual(len(list(self.root.glob('runtime.json.before-rpc-*'))), 1)

    def test_dry_run_does_not_write(self):
        baseline = self.runtime.read_bytes()
        self.assertTrue(module.configure(self.runtime, self.private, request=self.request, dry_run=True)['dryRun'])
        self.assertEqual(self.runtime.read_bytes(), baseline)
        self.assertFalse(list(self.root.glob('runtime.json.before-rpc-*')))

    def test_wrong_chain_and_provider_error_do_not_write(self):
        baseline = self.runtime.read_bytes()
        for response in [dict(jsonrpc='2.0', id=1, result='mainnet'), dict(jsonrpc='2.0', id=1, error={'message': self.endpoint})]:
            with self.assertRaises(ValueError) as caught:
                module.configure(self.runtime, self.private, request=lambda *_: response)
            self.assertNotIn(self.endpoint, str(caught.exception))
            self.assertEqual(self.runtime.read_bytes(), baseline)
            self.assertFalse(list(self.root.glob('runtime.json.before-rpc-*')))

    def test_input_permissions_and_https(self):
        self.private.chmod(0o644)
        with self.assertRaises(ValueError):
            module.configure(self.runtime, self.private, request=self.request)
        self.private.chmod(0o600)
        self.private.write_text(json.dumps(dict(rpcUpstream='http://provider.invalid')))
        with self.assertRaises(ValueError):
            module.configure(self.runtime, self.private, request=self.request)
        self.assertFalse(self.calls)


if __name__ == '__main__':
    unittest.main()
