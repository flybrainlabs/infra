import importlib.util,json,tempfile,unittest
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
if __name__=='__main__':unittest.main()
