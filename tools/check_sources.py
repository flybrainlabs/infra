#!/usr/bin/env python3
"""Check source ownership, English documentation and secret-free Git inputs."""
import argparse, json, re, subprocess
from pathlib import Path
from workspace import NAMES,load_components

def check(repos):
    entries=load_components(repos);errors=[];count=0
    for name in NAMES:
        root=repos/name
        files=[p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts]
        for p in files:
            count+=1;relative=str(p.relative_to(root));b=p.read_bytes()
            # The owner requested Chinese public handbook content. Technical
            # maintenance documentation continues to use English elsewhere.
            localized_handbook=name=='docs' and p.relative_to(root).parts[:3]==('docs','handbook','zh')
            if p.suffix=='.md' and not localized_handbook and re.search('[\u3400-\u9fff]',b.decode('utf-8')):errors.append(name+'/'+relative+': non-English maintained documentation')
            if re.search(rb'-----BEGIN (?:OPENSSH |RSA |EC |DSA |ENCRYPTED )?PRIVATE KEY-----',b) or re.search(rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b',b):errors.append(name+'/'+relative+': secret material detected')
            if p.stat().st_size>=100_000_000:errors.append(name+'/'+relative+': exceeds source publication limit')
            if any(part in ('private','.ssh','.flypow-secrets','node_modules','test-ledger') for part in p.relative_to(root).parts) or p.suffix in ('.sqlite','.sqlite-wal','.pem','.key'):errors.append(name+'/'+relative+': forbidden publication path')
    if errors:raise ValueError('\n'.join(errors))
    return {'checkedFiles':count,'uniqueWorkspaceFiles':len(entries),'englishDocumentation':True,'secretPatternScan':True}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repos',type=Path,default=Path(__file__).resolve().parents[2]);a=p.parse_args();print(json.dumps(check(a.repos)))
