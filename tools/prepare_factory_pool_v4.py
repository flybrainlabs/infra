#!/usr/bin/env python3
"""Prepare a hash-verified inactive source bundle; never install or activate it."""
import argparse,ast,gzip,hashlib,io,json,re,tarfile
from pathlib import Path

def digest(data):return hashlib.sha256(data).hexdigest()
def prepare(a):
    root=a.workspace.resolve();out=a.output.resolve()
    if out.exists() or out==root or out.is_relative_to(root):raise ValueError('Choose a fresh private output outside the workspace')
    files={};pending=['tools/factory_pool_service_v4.mjs','tools/calibrate_factory_reserve_v4.py','web/data/target-mining-v2/brief/goal.json','config/factory-pool-v4.sql','package.json','package-lock.json','deploy/target-v2/factory-pool-v4.example.json','docs/FACTORY_POOL_V4_OPERATIONS.md']
    while pending:
        name=pending.pop();source=root/name;path=source.resolve()
        if not path.is_relative_to(root) or source.is_symlink() or not path.is_file():raise ValueError('Missing or unsafe source dependency: '+name)
        name=str(path.relative_to(root))
        if name in files:continue
        data=path.read_bytes()
        if len(data)>2*1024*1024 or (b'-----BEGIN '+b'PRIVATE KEY-----') in data:raise ValueError('Unexpected source material')
        files[name]=data
        if path.suffix=='.mjs':
            for reference in re.findall(r'''(?:from\s*|import\s*\()\s*['"]([^'"]+)['"]''',data.decode()):
                if reference.startswith('.'):pending.append(str((path.parent/reference).resolve().relative_to(root)))
        if path.suffix=='.py':
            tree=ast.parse(data)
            modules=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and n.module]
            modules += [alias.name for n in ast.walk(tree) if isinstance(n,ast.Import) for alias in n.names]
            for module in modules:
                candidate=path.parent/(module.split('.')[0]+'.py')
                if candidate.is_file():pending.append(str(candidate.relative_to(root)))
    out.mkdir(parents=True,mode=0o700)
    tar=io.BytesIO()
    with tarfile.open(fileobj=tar,mode='w') as archive:
        for name,data in sorted(files.items()):
            item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o644;item.mtime=0;archive.addfile(item,io.BytesIO(data))
    bundle=gzip.compress(tar.getvalue(),mtime=0);(out/'bundle.tar.gz').write_bytes(bundle)
    manifest={'schema':'flybrainlabs-factory-pool-source-v4','files':{n:digest(b) for n,b in sorted(files.items())},'bundleSha256':digest(bundle),'fileCount':len(files),'programUpgrade':False,'activation':False,'publicChainWrites':0,'newRewardBudgetAtoms':'0','modelsIncluded':False,'privateRuntimeIncluded':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items() if k!='files'}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--output',type=Path,required=True);prepare(p.parse_args())
