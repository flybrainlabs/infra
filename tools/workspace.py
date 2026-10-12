#!/usr/bin/env python3
"""Assemble a reproducible Flybrain workspace from uniquely owned components."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
NAMES=('web','node','miner','explorer','protocol','contracts','sdk','infra','research','docs')

def run(args,cwd=None):
    return subprocess.check_output(args,cwd=cwd,text=True).strip()
def safe_path(s):
    p=PurePosixPath(s)
    if not s or p.is_absolute() or any(x in ('..','.git','private','node_modules','target') for x in p.parts):raise ValueError('Unsafe source path: '+s)
    return p
def load_components(repos):
    entries={}
    for name in NAMES:
        spec=json.loads((repos/name/'component.json').read_text())
        if spec['schema']!='flybrain-component-v1' or spec['repository']!=name or spec['owner']!='flybrainwork':raise ValueError('Unexpected component identity: '+name)
        for dst,src in spec['workspaceFiles'].items():
            safe_path(dst);safe_path(src)
            if dst in entries:raise ValueError('Duplicate source ownership: '+dst)
            source=repos/name/src
            if not source.is_file() or source.is_symlink():raise ValueError('Missing or indirect source: '+str(source))
            entries[dst]=(name,src,source)
    return entries
def verify_pins(repos,manifest):
    data=json.loads(manifest.read_text())
    if data['schema']!='flybrain-release-manifest-v1' or data['owner']!='flybrainwork':raise ValueError('Invalid release manifest')
    for name in NAMES:
        if name=='infra':continue # The commit containing this manifest pins infra.
        pin=data['repositories'][name]
        if pin['url']!=f'https://github.com/flybrainwork/{name}.git' or len(pin['commit'])!=40:raise ValueError('Invalid dependency pin: '+name)
        if run(['git','rev-parse','HEAD'],repos/name)!=pin['commit']:raise ValueError('Revision mismatch: '+name)
        if run(['git','status','--porcelain'],repos/name):raise ValueError('Dirty pinned dependency: '+name)
    return data
def assemble(repos,output,working_tree=False,manifest=None):
    repos=repos.resolve();output=output.resolve()
    if output==repos or repos in output.parents or output in repos.parents:raise ValueError('Workspace must be outside source repositories')
    if not working_tree:verify_pins(repos,manifest or ROOT/'release-manifest.json')
    entries=load_components(repos);output.mkdir(parents=True,exist_ok=True)
    marker=output/'.flybrain-workspace.json';old=json.loads(marker.read_text()) if marker.exists() else {'files':{}}
    report={}
    for dst,(name,src,source) in sorted(entries.items()):
        target=output/dst;blob=source.read_bytes();digest=hashlib.sha256(blob).hexdigest()
        if target.exists():
            previous=old['files'].get(dst)
            current=hashlib.sha256(target.read_bytes()).hexdigest()
            if current!=digest and (not previous or current!=previous['sha256']):raise ValueError('Workspace edits require explicit sync before refresh: '+dst)
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
            temporary=target.with_name(target.name+'.flybrain-tmp');shutil.copy2(source,temporary);os.replace(temporary,target)
        report[dst]={'repository':name,'repositoryPath':src,'sha256':digest}
    for dst in set(old['files'])-set(report):
        target=output/dst
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest()!=old['files'][dst]['sha256']:raise ValueError('Removed source contains unsynchronized edits: '+dst)
            target.unlink()
    state={'schema':'flybrain-workspace-v1','repositories':str(repos),'mode':'working-tree' if working_tree else 'pinned-release','files':report}
    marker.write_text(json.dumps(state,indent=2)+'\n')
    return {'files':len(report),'output':str(output),'mode':state['mode']}
def checkout(repos,manifest):
    data=json.loads(manifest.read_text())
    if data.get('publication',{}).get('complete') is not True:raise ValueError('Release publication is incomplete; restore repository access and finish the pending pushes first')
    repos.mkdir(parents=True,exist_ok=True)
    for name,pin in data['repositories'].items():
        if name not in NAMES or name=='infra':raise ValueError('Unexpected dependency')
        if pin['url']!=f'https://github.com/flybrainwork/{name}.git':raise ValueError('Unexpected repository URL')
        target=repos/name
        created=not target.exists()
        if created:subprocess.run(['git','clone','--no-checkout',pin['url'],str(target)],check=True)
        if not created and run(['git','status','--porcelain'],target):raise ValueError('Refusing to replace source edits: '+name)
        subprocess.run(['git','fetch','origin',pin['commit']],cwd=target,check=True)
        subprocess.run(['git','checkout','--detach',pin['commit']],cwd=target,check=True)
def sync(repos,output):
    state=json.loads((output/'.flybrain-workspace.json').read_text());changed=[]
    if state['repositories']!=str(repos.resolve()):raise ValueError('Different source repositories')
    # Check the whole set before applying any change; detect independent edits.
    for dst,info in state['files'].items():
        target=output/dst;source=repos/info['repository']/info['repositoryPath']
        if not target.is_file():raise ValueError('Workspace deletions must be made in their owning repository: '+dst)
        digest=hashlib.sha256(target.read_bytes()).hexdigest()
        if digest!=info['sha256']:
            if hashlib.sha256(source.read_bytes()).hexdigest()!=info['sha256']:raise ValueError('Concurrent component edit: '+dst)
            changed.append((target,source))
    for target,source in changed:shutil.copy2(target,source)
    return {'synchronizedFiles':len(changed),'repositories':sorted({str(s.relative_to(repos).parts[0]) for _,s in changed})}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['assemble','checkout','sync','verify']);p.add_argument('--repos',type=Path,default=ROOT.parent);p.add_argument('--output',type=Path,default=ROOT.parent.parent/'flybrain-workspace');p.add_argument('--manifest',type=Path,default=ROOT/'release-manifest.json');p.add_argument('--working-tree',action='store_true');a=p.parse_args()
    if a.action=='assemble':result=assemble(a.repos,a.output,a.working_tree,a.manifest)
    elif a.action=='checkout':checkout(a.repos,a.manifest);result={'checkedOut':True}
    elif a.action=='sync':result=sync(a.repos,a.output)
    else:verify_pins(a.repos,a.manifest);result={'pinsVerified':True,'files':len(load_components(a.repos))}
    print(json.dumps(result))
if __name__=='__main__':main()
