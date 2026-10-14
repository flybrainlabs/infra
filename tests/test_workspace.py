import importlib.util,json,tempfile,unittest,sys
from unittest.mock import patch
from pathlib import Path
spec=importlib.util.spec_from_file_location('workspace',Path(__file__).resolve().parents[1]/'tools/workspace.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
class WorkspaceSafety(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.repos=self.base/'repos';self.output=self.base/'assembled'
  for name in w.NAMES:
   p=self.repos/name;p.mkdir(parents=True);(p/'component.json').write_text(json.dumps({'schema':'flybrain-component-v1','repository':name,'owner':'flybrainlabs','workspaceFiles':{}}))
  self.spec=self.repos/'node/component.json';self.doc=json.loads(self.spec.read_text());self.doc['workspaceFiles']={'src/a.rs':'src/a.rs'};self.spec.write_text(json.dumps(self.doc));(self.repos/'node/src').mkdir();(self.repos/'node/src/a.rs').write_text('original')
 def tearDown(self):self.tmp.cleanup()
 def test_unique_ownership_and_path_traversal(self):
  d=json.loads((self.repos/'miner/component.json').read_text());d['workspaceFiles']={'src/a.rs':'src/a.rs'};(self.repos/'miner/component.json').write_text(json.dumps(d))
  with self.assertRaises(ValueError):w.load_components(self.repos)
  for p in ['../private.key','/absolute','src/.git/config','private/key']:self.assertRaises(ValueError,w.safe_path,p)
 def test_preserves_build_cache_and_rejects_unsynchronized_edits(self):
  w.assemble(self.repos,self.output,True);cache=self.output/'target/cache';cache.parent.mkdir();cache.write_text('keep')
  (self.output/'src/a.rs').write_text('workspace change')
  with self.assertRaises(ValueError):w.assemble(self.repos,self.output,True)
  self.assertEqual(cache.read_text(),'keep');w.sync(self.repos,self.output);self.assertEqual((self.repos/'node/src/a.rs').read_text(),'workspace change');w.assemble(self.repos,self.output,True)
 def test_concurrent_source_change_is_not_overwritten(self):
  w.assemble(self.repos,self.output,True);(self.output/'src/a.rs').write_text('workspace change');(self.repos/'node/src/a.rs').write_text('source change')
  with self.assertRaises(ValueError):w.sync(self.repos,self.output)
  self.assertEqual((self.repos/'node/src/a.rs').read_text(),'source change')
 def test_private_repository_checkout_uses_requested_identity(self):
  manifest=self.base/'release.json';manifest.write_text(json.dumps({'publication':{'complete':True},'repositories':{'web':{'url':'https://github.com/flybrainlabs/web.git','commit':'a'*40}}}))
  destination=self.base/'checkout'
  with patch.object(w.subprocess,'run') as run:
   w.checkout(destination,manifest,'ssh','github-flybrainlabs')
   self.assertEqual(run.call_args_list[0].args[0],['git','clone','--no-checkout','git@github-flybrainlabs:flybrainlabs/web.git',str(destination/'web')])
   self.assertEqual(run.call_args_list[1].args[0],['git','fetch','origin','a'*40])
  with self.assertRaises(ValueError):w.checkout(destination,manifest,'ssh','github.com;echo secret')
 def test_localized_handbook_does_not_relax_technical_documentation(self):
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
  from check_sources import check
  translated=self.repos/'docs/docs/handbook/zh/model.md';translated.parent.mkdir(parents=True);translated.write_text('# 科学模型\n')
  self.assertTrue(check(self.repos)['englishDocumentation'])
  technical=self.repos/'docs/docs/OPERATIONS.md';technical.write_text('# 中文维护文件\n')
  with self.assertRaisesRegex(ValueError,'non-English maintained documentation'):check(self.repos)
if __name__=='__main__':unittest.main()
