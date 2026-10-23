"""Fail closed before SSH when a mining asset overlay exceeds its review scope."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('mining_deploy',Path(__file__).resolve().parents[1]/'tools/deploy_mining_release.py')
deploy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


class NetworkBoundary(Exception):
    pass


class AssetOverlayTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='flybrainlabs-overlay-')
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.baseline=root/'baseline';self.release=root/'release'
        for p in [self.baseline,self.release]:
            (p/'assets').mkdir(parents=True)
            (p/'release.json').write_text('{}')
        (self.baseline/'assets/research-app.mjs').write_text('old')
        (self.release/'assets/research-app.mjs').write_text('new')
        self.build={'schema':'flybrainlabs-mining-asset-overlay-v1','release':str(self.release),'baseline':str(self.baseline),'baselineMetadataSha256':sha(self.baseline/'release.json'),'atlas_unchanged':True,'independent_copy':True,'changed_files':{'assets/research-app.mjs':{'old_sha256':sha(self.baseline/'assets/research-app.mjs'),'new_sha256':sha(self.release/'assets/research-app.mjs')}}}
        self.args=SimpleNamespace(build_report=root/'build.json',validation=root/'validation.json',ssh_config=root/'ssh',host='flybrain-work',report=root/'report.json')

    def save(self):
        self.args.build_report.write_text(json.dumps(self.build))
        self.args.validation.write_text(json.dumps({'schema':'flybrainlabs-mining-asset-overlay-validation-v1','passed':True,'buildSha256':sha(self.args.build_report)}))

    def rejected(self,pattern):
        with patch.object(deploy.subprocess,'check_output') as network:
            with self.assertRaisesRegex(ValueError,pattern):deploy.deploy(self.args)
            network.assert_not_called()

    def test_valid_overlay_reaches_existing_ssh_identity_checks(self):
        self.save()
        with patch.object(deploy.subprocess,'check_output',side_effect=NetworkBoundary):
            with self.assertRaises(NetworkBoundary):deploy.deploy(self.args)

    def test_unsafe_paths_are_rejected(self):
        for name in ['../../private.json','/etc/passwd','assets/data/task-factory-deployment-v4.json','github-oauth.php','.htaccess']:
            with self.subTest(name=name):
                self.build['changed_files']={name:{}}
                self.save();self.rejected('scope')

    def test_changed_baseline_is_rejected(self):
        self.save();(self.baseline/'release.json').write_text('{"changed":true}')
        self.rejected('baseline changed')

    def test_stale_validation_is_rejected(self):
        self.save();self.args.build_report.write_text(self.args.build_report.read_text()+' ')
        self.rejected('exact asset overlay')

    def test_shared_source_is_rejected(self):
        self.save();target=self.release/'assets/research-app.mjs';target.unlink();target.symlink_to(self.baseline/'assets/research-app.mjs')
        self.rejected('independent file')

    def test_changed_bytes_are_rejected(self):
        self.save();(self.release/'assets/research-app.mjs').write_text('unreviewed')
        self.rejected('Release changed')

    def test_new_reviewed_module_reaches_destination_checks(self):
        target=self.release/'assets/task-supply-status-v4.mjs';target.write_text('export const informational=true;')
        self.build['changed_files'][str(target.relative_to(self.release))]={'old_sha256':None,'new_sha256':sha(target)}
        self.save()
        with patch.object(deploy.subprocess,'check_output',side_effect=NetworkBoundary):
            with self.assertRaises(NetworkBoundary):deploy.deploy(self.args)

    def test_existing_path_cannot_be_declared_new(self):
        self.build['changed_files']['assets/research-app.mjs']['old_sha256']=None
        self.save();self.rejected('already exists')


if __name__=='__main__':unittest.main()
