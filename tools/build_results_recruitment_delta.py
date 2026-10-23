#!/usr/bin/env python3
"""Package the additive community change without runtime data or deployment."""
import argparse,hashlib,json,tarfile
from pathlib import Path

FILES=('tools/social_community.mjs','tools/social_server.mjs','tools/project_recruitment.mjs','config/social-community-v4.sql','config/research-projects-v1.json')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def build(workspace,output):
    workspace=workspace.resolve();output=output.resolve()
    if output.exists():raise ValueError('Choose a fresh output directory')
    state=json.loads((workspace/'.flybrain-workspace.json').read_text())
    records={}
    for name in FILES:
        file=workspace/name;info=state['files'][name]
        if info['repository']!='node' or file.is_symlink() or sha(file)!=info['sha256']:raise ValueError('Unassembled node source: '+name)
        records[name]={'sha256':sha(file),'bytes':file.stat().st_size}
    output.mkdir(parents=True,mode=0o700)
    archive=output/'community-recruitment-v4.tar.gz'
    with tarfile.open(archive,'w:gz',format=tarfile.PAX_FORMAT) as tar:
        for name in FILES:
            file=workspace/name;info=tar.gettarinfo(str(file),arcname=name)
            info.uid=info.gid=0;info.uname=info.gname='';info.mode=0o644;info.mtime=0
            with file.open('rb') as stream:tar.addfile(info,stream)
    manifest={'schema':'fbw-community-recruitment-delta-v1','nodeMinimumVersion':'22.13.0','archive':archive.name,'archiveSha256':sha(archive),'files':records,'retainedMigrationSha256':{str(i):sha(workspace/f'config/social-community-v{i}.sql') for i in (1,2,3)},'existingInstallRequired':True,'automaticDeployment':False,'productionMigrated':False,'databaseResetRequired':False}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'archive':str(archive),'sha256':manifest['archiveSha256'],'files':len(records),'productionChanged':False}))
    return manifest
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();build(args.workspace,args.output)
