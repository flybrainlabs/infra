#!/usr/bin/env python3
"""Publish validated component changes with normal SSH fast forwards only."""
import argparse,json,re,subprocess
from pathlib import Path
from check_sources import check
from workspace import NAMES

def run(args,cwd):return subprocess.check_output(args,cwd=cwd,text=True).strip()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repos',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--message',required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--only',nargs='+',choices=NAMES);a=p.parse_args()
    if not a.message.strip() or re.search('[\u3400-\u9fff]',a.message):raise ValueError('Commit messages must be English')
    checked=check(a.repos);results=[]
    a.report.parent.mkdir(parents=True,exist_ok=True)
    for name in a.only or NAMES:
        root=a.repos/name;expected=f'git@github-flybrainwork:flybrainwork/{name}.git'
        if run(['git','remote','get-url','--push','origin'],root)!=expected:raise ValueError('Unexpected publication target: '+name)
        subprocess.run(['git','fetch','origin'],cwd=root,check=True)
        branch=run(['git','branch','--show-current'],root)
        if not branch:raise ValueError('Check out a development branch before publishing: '+name)
        remote=subprocess.run(['git','rev-parse','--verify','refs/remotes/origin/'+branch],cwd=root,capture_output=True,text=True)
        if remote.returncode==0 and subprocess.run(['git','merge-base','--is-ancestor',remote.stdout.strip(),'HEAD'],cwd=root).returncode!=0:raise ValueError('Remote changes must be preserved before publishing: '+name)
        dirty=run(['git','status','--porcelain'],root)
        if dirty:
            subprocess.run(['git','add','--all'],cwd=root,check=True)
            subprocess.run(['git','commit','-m',a.message],cwd=root,check=True)
        head=run(['git','rev-parse','HEAD'],root)
        if remote.returncode!=0 or remote.stdout.strip()!=head:subprocess.run(['git','push','--set-upstream','origin',branch],cwd=root,check=True)
        actual=run(['git','ls-remote','origin','refs/heads/'+branch],root).split()[0]
        if actual!=head:raise ValueError('Remote publication verification failed: '+name)
        results.append({'repository':name,'branch':branch,'commit':head,'updated':bool(dirty),'remoteVerified':True})
        a.report.write_text(json.dumps({'owner':'flybrainwork','checks':checked,'repositories':results,'complete':False},indent=2)+'\n')
    a.report.write_text(json.dumps({'owner':'flybrainwork','checks':checked,'repositories':results,'complete':True},indent=2)+'\n');print(json.dumps(results))
if __name__=='__main__':main()
