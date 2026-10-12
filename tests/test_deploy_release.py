import gzip
import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_static_release", PROJECT / "tools/validate_static_release.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ReleaseFixture:
    def setUp(self):
        # CI /tmp may be mounted noexec; this fixture launches fake ssh binaries.
        self.temp = tempfile.TemporaryDirectory(prefix="flypow-release-validation-", dir=PROJECT.parent)
        self.root = Path(self.temp.name) / "release"
        self.root.mkdir()
        for name in validator.TOP_LEVEL:
            if name == "release.json":
                continue
            path = self.root / name
            if "." in name:
                path.write_text("static fixture")
            else:
                path.mkdir()
        identity = "0123456789abcdef"
        entry = {"id": identity}
        for field, folder, extension in (("geometry", "geometry", "json"), ("detail", "details", "json"), ("thumbnail", "thumbs", "svg")):
            relative = "/assets/data/atlas/{}/{}.{}".format(folder, identity, extension)
            entry[field] = relative
            path = self.root / relative.lstrip("/")
            path.parent.mkdir(parents=True, exist_ok=True)
            data = b"<svg/>" if extension == "svg" else b"{}"
            path.write_bytes(data)
            path.with_name(path.name + ".gz").write_bytes(gzip.compress(data))
        self.catalogue = {"schema": "flypow-neuron-atlas-v1", "count": 1, "entries": [entry]}
        self.catalogue_path = self.root / "assets/data/atlas.json"
        self.catalogue_path.write_text(json.dumps(self.catalogue))
        self.refresh_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def refresh_manifest(self):
        files = [p for p in self.root.rglob("*") if p.is_file() and p.name != "release.json"]
        self.report = {"deployment": "static", "api_enabled": False, "atlas_included": True, "compression": {"lossless_verified": True}, "file_count": len(files), "bytes": sum(p.stat().st_size for p in files)}
        (self.root / "release.json").write_text(json.dumps(self.report))


class DeploymentValidationTests(ReleaseFixture, unittest.TestCase):
    def test_valid_release(self):
        self.assertEqual(validator.validate_release(self.root)["types"], 1)

    def test_research_release_binds_wasm_and_disables_rewards(self):
        wasm = self.root / "assets/wasm/flypow_sim_core.wasm"
        wasm.parent.mkdir()
        wasm.write_bytes(b"\x00asm\x01\x00\x00\x00")
        for module in ("research-app.mjs", "research-worker.mjs", "computation.mjs", "receipt-v1.mjs", "catalog-task.mjs", "response-record.mjs", "response-store.mjs", "archive-upload.mjs", "chunk-store.mjs", "official-source.mjs", "miner-state.mjs", "model-storage.mjs", "preparation-controller.mjs", "task-runner.mjs", "submission-store.mjs", "submission-controller.mjs", "response-view.mjs", "contribution-view.mjs", "research-tools.mjs", "vendor/generated/official-builder.mjs", "vendor/generated/solana-client.mjs", "vendor/generated/archive-zip.mjs"):
            path=self.root / "assets" / module
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text("// test fixture")
        # Keep this policy fixture current with the existing 3D/V2 public modules.
        # Actual exported source bytes are checked by test_static_export.
        for source in (PROJECT/'web').glob('*.mjs'):
            (self.root/'assets'/source.name).write_text('// test fixture')
        catalog = self.root / "assets/data/task-catalog-dev.json"
        original_catalog=(PROJECT/'web/data/task-catalog-dev.json').read_text()
        catalog.write_text(original_catalog)
        cells=json.loads((PROJECT/'web/data/pilot-cells.json').read_text())
        (self.root / "assets/data/research-config.json").write_text(json.dumps({
            "state": "UNCALIBRATED_DEV_ONLY", "allow_wallet": False,
            "allow_payment": False, "allow_rewards": False,
            "task_catalog_sha256": hashlib.sha256(catalog.read_bytes()).hexdigest(),
            "registry_sha256": cells['registry_sha256'],
            "graph_sha256": '0'*64,
        }))
        anatomy={'schema':'flypow-mining-anatomy-v2','registryRoot':cells['registry_sha256'],'graphRoot':'0'*64,'cells':[]}
        anatomy_bytes=json.dumps(anatomy).encode()
        (self.root/'assets/data/mining-anatomy.json').write_bytes(anatomy_bytes)
        (self.root/'assets/mining-anatomy-index.mjs').write_text("export const MINING_ANATOMY_INDEX_SHA256 = '"+hashlib.sha256(anatomy_bytes).hexdigest()+"';")
        (self.root / "mining/index.html").write_text('/assets/research-app.mjs')
        (self.root / 'assets/data/chain-config.json').write_text(json.dumps({'schema':'flypow-solana-client-v1','enabled':False,'network':'localnet'}))
        (self.root / 'assets/data/pilot-cells.json').write_text(json.dumps(cells))
        shutil.copytree(PROJECT/'web/data/pilot-cells',self.root/'assets/data/pilot-cells')
        (self.root / ".htaccess").write_text("application/wasm worker-src 'self' 'wasm-unsafe-eval' https://storage.googleapis.com")
        self.refresh_manifest()
        self.report["mode"] = "research-app"
        self.report["wasm_sha256"] = hashlib.sha256(wasm.read_bytes()).hexdigest()
        (self.root / "release.json").write_text(json.dumps(self.report))
        self.assertEqual(validator.validate_release(self.root)["types"], 1)
        catalog.write_text('{"state":"TAMPERED"}')
        self.refresh_manifest()
        self.report["mode"] = "research-app"
        self.report["wasm_sha256"] = hashlib.sha256(wasm.read_bytes()).hexdigest()
        (self.root / "release.json").write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError, "catalog digest"):
            validator.validate_release(self.root)
        catalog.write_text(original_catalog)
        wasm.write_bytes(b"\x00asm\x01\x00\x00\x01")
        self.refresh_manifest()
        self.report["mode"] = "research-app"
        self.report["wasm_sha256"] = hashlib.sha256(b"\x00asm\x01\x00\x00\x00").hexdigest()
        (self.root / "release.json").write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError, "digest"):
            validator.validate_release(self.root)

    def test_reject_repository_or_extra_credentials(self):
        (self.root / "id_ed25519").write_text("not a real key")
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "top-level"):
            validator.validate_release(self.root)

    def test_reject_symlinks(self):
        (self.root / "assets/sensitive.json").symlink_to(self.root / "index.html")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            validator.validate_release(self.root)

    def test_reject_changed_bytes(self):
        (self.root / "index.html").write_text("modified after build")
        with self.assertRaisesRegex(ValueError, "sizes differ"):
            validator.validate_release(self.root)

    def test_reject_incomplete_atlas(self):
        self.report["atlas_included"] = False
        (self.root / "release.json").write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError, "complete atlas"):
            validator.validate_release(self.root)

    def test_reject_traversal_in_catalogue(self):
        self.catalogue["entries"][0]["geometry"] = "/../../id_ed25519"
        self.catalogue_path.write_text(json.dumps(self.catalogue))
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "resource path"):
            validator.validate_release(self.root)

    def test_reject_missing_gzip(self):
        next((self.root / "assets/data/atlas/geometry").glob("*.gz")).unlink()
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "gzip fallback"):
            validator.validate_release(self.root)


class DeploymentScriptTests(ReleaseFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.bin = Path(self.temp.name) / "fake-bin"
        self.bin.mkdir()
        self.log = Path(self.temp.name) / "calls.jsonl"
        self.config = Path(self.temp.name) / "ssh-config"
        self.config.write_text("Host flybrain-work\n")
        program = "#!" + sys.executable + "\n" + '''
import json, os, pathlib, subprocess, sys
name=pathlib.Path(sys.argv[0]).name
with open(os.environ['FLYPOW_TEST_CALL_LOG'],'a') as handle:
    handle.write(json.dumps({'command':name,'args':sys.argv[1:]})+'\\n')
if name=='ssh':
    if '-G' in sys.argv:
        print('hostname '+os.environ.get('FLYPOW_TEST_HOST','server241.web-hosting.com'))
        print('user flybwhiv\\nport 21098')
    elif 'tar --use-compress-program' in ' '.join(sys.argv) and os.environ.get('FLYPOW_TEST_BACKUP_FAIL'):
        sys.exit(9)
    else:
        print('flybwhiv')
elif name=='python3':
    if len(sys.argv)>1 and sys.argv[1].endswith('check_public_site.py'):
        print('Mock public check passed; no network used.')
    else:
        sys.exit(subprocess.call([sys.executable]+sys.argv[1:]))
'''
        for name in ("ssh", "rsync", "python3"):
            path = self.bin / name
            path.write_text(program)
            path.chmod(0o700)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"], FLYPOW_TEST_CALL_LOG=str(self.log))

    def run_script(self, *arguments):
        result = subprocess.run(["bash", str(PROJECT / "deploy/deploy-static.sh"), "--release", str(self.root), "--ssh-config", str(self.config), *arguments], env=self.env, text=True, capture_output=True)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
        return result, calls

    def test_default_mode_never_writes(self):
        result, calls = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        transfers = [c for c in calls if c["command"] == "rsync"]
        self.assertEqual(len(transfers), 1)
        self.assertIn("--dry-run", transfers[0]["args"])
        self.assertFalse(any("tar --use-compress-program" in " ".join(c["args"]) for c in calls))

    def test_check_does_not_transfer(self):
        result, calls = self.run_script("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(c["command"] == "rsync" for c in calls))

    def test_apply_requires_backup_first_and_never_deletes(self):
        result, calls = self.run_script("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        backup = next(i for i,c in enumerate(calls) if "tar --use-compress-program" in " ".join(c["args"]))
        transfer = next(i for i,c in enumerate(calls) if c["command"] == "rsync")
        self.assertLess(backup, transfer)
        self.assertNotIn("--dry-run", calls[transfer]["args"])
        self.assertFalse(any(a.startswith("--delete") or a == "--inplace" for a in calls[transfer]["args"]))
        self.assertIn("--delay-updates", calls[transfer]["args"])
        self.assertTrue(any(c["command"] == "python3" and c["args"][0].endswith("check_public_site.py") for c in calls[transfer + 1:]))

    def test_failed_backup_prevents_upload(self):
        self.env["FLYPOW_TEST_BACKUP_FAIL"] = "1"
        result, calls = self.run_script("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c["command"] == "rsync" for c in calls))

    def test_wrong_host_is_rejected(self):
        self.env["FLYPOW_TEST_HOST"] = "other.invalid"
        result, calls = self.run_script("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c["command"] == "rsync" or "tar --use-compress-program" in " ".join(c["args"]) for c in calls))


if __name__ == "__main__":
    unittest.main()
