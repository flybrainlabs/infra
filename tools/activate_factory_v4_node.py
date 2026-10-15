#!/usr/bin/env python3
"""Switch the authorized original Devnet node to a sealed, paused V4 catalog."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import time
import urllib.request

ROOT=Path('/opt/flypow/task-factory-v4')
STATE=Path('/var/lib/flypow/task-factory-v4')
WALLET=Path('/opt/flypow/tools/wallet_mining_v3.mjs')
RUNTIME=Path('/etc/flypow/wallet-mining-v3-runtime.json')
V4_RUNTIME=Path('/etc/flypow/task-factory-v4-runtime.json')
NGINX=Path('/etc/nginx/conf.d/flypow-node.conf')
SERVICE='flybrainlabs-task-factory-v4'
LEGACY='flypow-target-verifier-serial'
WALLET_SERVICE='flybrainlabs-wallet-mining-v3'
NODE='/opt/flypow/runtime/node/bin/node'

def require(ok,message):
    if not ok:raise RuntimeError(message)

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def call(*args):return subprocess.check_output(args,text=True,stderr=subprocess.PIPE).strip()

def run(*args):subprocess.run(args,check=True,capture_output=True,text=True)

def atomic(blob,path,mode=0o644,uid=0,gid=0):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.v4-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as out:out.write(blob);out.flush();os.fsync(out.fileno())
        os.chmod(tmp,mode);os.chown(tmp,uid,gid);os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def json_get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'Origin':'https://flybrain.work'}),timeout=10) as response:return json.load(response)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('upload',type=Path);actions=parser.add_mutually_exclusive_group();actions.add_argument('--apply',action='store_true');actions.add_argument('--refresh-service',action='store_true');args=parser.parse_args();os.umask(0o077)
    manifest=json.loads((args.upload/'manifest.json').read_text());deployment=json.loads((args.upload/'deployment.json').read_text());files=manifest['files']
    require(manifest['schema']=='flybrainlabs-factory-v4-node-activation' and deployment['cluster']=='devnet' and deployment['enabled'] is True and deployment['catalogRoot']==manifest['catalogRoot'] and deployment['budgetAtoms']=='160000000000' and deployment['rewardAtoms']=='20000000000' and deployment['taskCount']==8,'Unexpected approved activation scope')
    release=ROOT/'releases'/('active-'+manifest['sourceBundleSha256'][:16]);require(hashlib.sha256((args.upload/'bundle.tar.gz').read_bytes()).hexdigest()==manifest['sourceBundleSha256'],'Source bundle changed')
    with tarfile.open(args.upload/'bundle.tar.gz') as archive:
        members=archive.getmembers();require(len(members)==len(files) and len({m.name for m in members})==len(files),'Source manifest mismatch')
        for member in members:
            path=PurePosixPath(member.name);require(member.isfile() and not path.is_absolute() and '..' not in path.parts and path.parts[0] in ('tools','web','deploy') and member.name in files,'Unsafe source path');require(hashlib.sha256(archive.extractfile(member).read()).hexdigest()==files[member.name],'Source hash mismatch')
    require(digest(args.upload/'wallet_mining_v3.mjs')==manifest['newWalletSourceSha256'] and digest(WALLET) in (manifest['oldWalletSourceSha256'],manifest['newWalletSourceSha256']),'Shared wallet source changed')
    old=json.loads(RUNTIME.read_text());verify=json.loads(Path('/etc/flypow/verifier-serial-runtime.json').read_text());require(old['cluster']=='devnet' and old['testOnly'] is True and old['programId']==deployment['programId'] and old['policyHash']==deployment['policyHash'],'Existing node identity mismatch')
    supply=json_get('http://127.0.0.1:8790/api/target-mining/v2/rounds/current')['supply'];require(supply['pendingGoals']==0 and supply['solvedGoals']==31,'Retain and inspect any changed legacy work before switching')
    untouched=['flypow-target-authority','flybrainlabs-community'];pids=call('systemctl','show',*untouched,'-p','Id','-p','MainPID')
    require(call('systemctl','is-active',WALLET_SERVICE,*untouched).splitlines()==['active']*3,'Existing user services must be healthy')
    ROOT.joinpath('releases').mkdir(parents=True,exist_ok=True)
    ROOT.chmod(0o755);(ROOT/'releases').chmod(0o755)
    if not release.exists():
        with tempfile.TemporaryDirectory(prefix='v4-source-',dir=ROOT/'releases') as temporary:
            stage=Path(temporary)/'source';stage.mkdir(mode=0o755)
            with tarfile.open(args.upload/'bundle.tar.gz') as archive:
                for member in archive.getmembers():
                    target=stage/member.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.extractfile(member).read());target.chmod(0o644)
            stage.chmod(0o755)
            for directory in stage.rglob('*'):
                if directory.is_dir():directory.chmod(0o755)
            (stage/'node_modules').symlink_to('/opt/flypow/node_modules',target_is_directory=True)
            for name in files:
                if name.endswith('.mjs'):run(NODE,'--check',str(stage/name))
            run(NODE,'--input-type=module','-e','await import('+json.dumps((stage/'tools/factory_service_v4.mjs').as_uri())+')')
            stage.rename(release)
    for name,expected in files.items():require(digest(release/name)==expected,'Installed source differs')
    run('runuser','-u','flypow','--',NODE,'--input-type=module','-e','await import('+json.dumps((release/'tools/factory_service_v4.mjs').as_uri())+')')
    origins=[x for x in old['origins'] if x.startswith('https://')];require('https://flybrain.work' in origins,'Existing official origin required')
    config={'schema':'flybrainlabs-factory-node-runtime-v4','deployment':deployment,'origins':origins,'rpcUpstream':old.get('rpcUpstream') or old['rpc'],'database':str(STATE/'gateway.sqlite'),'contentDir':str(STATE/'content'),'partialDir':str(STATE/'partial'),'journalDir':str(STATE/'journals'),'modelDir':verify['modelDir'],'binary':verify['binary'],'outputDir':str(STATE/'replays'),'verifierKeyFiles':old['settlerKeypairs'][:2],'maxStorageBytes':1073741824,'diskReserveBytes':4294967296,'submitVotes':True,'maxTransactionsPerVerifier':64,'port':8792}
    # Private paths and URLs are consumed locally; only public identity and
    # readiness booleans are printed by this probe.
    probe="""import {readFile} from 'node:fs/promises';import {Keypair,PublicKey,Connection} from '@solana/web3.js';import {readerForDeployment} from './web/task-factory-client-v4.mjs';import {getModelReadiness} from './tools/candidate_verifier_v2.mjs';const c=JSON.parse(process.env.FLYBRAIN_V4_PROBE),reader=readerForDeployment(c.deployment,new Connection(c.rpcUpstream,'finalized')),f=await reader.factory();if((!f.paused&&!process.env.FLYBRAIN_V4_ACTIVE_REFRESH)||f.uploaded!==f.count||f.count!==8)throw new Error('Catalog must remain sealed and paused during node switch');if(!f.paused){const task=await reader.task(f.activeIndex);for(const entry of task.queue){const submission=await reader.submission(new PublicKey(entry.submission),reader.a.task(reader.expected.factoryAddress,task.index));if(submission.state===2)throw new Error('Revealed submissions require a separate drain before maintenance');}}const publicKeys=[];for(const path of c.verifierKeyFiles){const bytes=await readFile(path),k=bytes.length===32?Keypair.fromSeed(bytes):Keypair.fromSecretKey(Uint8Array.from(JSON.parse(bytes)));if(!f.verifiers.some(p=>new PublicKey(p).equals(k.publicKey)))throw new Error('Verifier scope');publicKeys.push({address:k.publicKey.toBase58(),balanceLamports:await reader.connection.getBalance(k.publicKey,'finalized')});}const ready=await getModelReadiness(c.binary,c.modelDir);console.log(JSON.stringify({sealedPausedCatalog:f.paused,keys:publicKeys,model:ready}));"""
    probe_result=subprocess.run([NODE,'--input-type=module','-e',probe],cwd=release,env={**os.environ,'FLYBRAIN_V4_PROBE':json.dumps(config),'FLYBRAIN_V4_ACTIVE_REFRESH':'1' if args.refresh_service else ''},check=True,capture_output=True,text=True);ready=json.loads(probe_result.stdout)
    require(ready['model']['nativeBinaryReady'] is True and ready['model']['graphRoot']==manifest['graphRoot'] and ready['model']['modelDataRoot']==manifest['modelDataRoot'],'Complete native model mismatch')
    require(all(k['balanceLamports']>=20000000 for k in ready['keys']),'Existing admitted verifier fee balances need bounded replenishment before activation')
    if not args.apply and not args.refresh_service:print(json.dumps({'preflightPassed':True,'sourceFiles':len(files),'sealedPausedCatalog':True,'completeModelChecked':True,'existingVerifierFeeBalancesSufficient':True,'servicesChanged':False}));return
    require(os.geteuid()==0,'The existing authorized node administrator is required')
    if args.refresh_service:
        require(call('systemctl','is-active',SERVICE)=='active' and json.loads(V4_RUNTIME.read_text())==config and (ROOT/'current').is_symlink(),'Refresh requires the identical configured paused V4 service')
        previous=os.readlink(ROOT/'current');backup=Path('/var/backups/flypow')/('factory-v4-refresh-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+str(os.getpid()));backup.mkdir(mode=0o700)
        (backup/'previous-source-link.txt').write_text(previous+'\n')
        try:
            link=ROOT/'current.next';link.symlink_to(release,target_is_directory=True);os.replace(link,ROOT/'current');run('systemctl','restart',SERVICE)
            for attempt in range(40):
                try:
                    require(json_get('http://127.0.0.1:8792/api/task-factory/v4/health')['verifier']['status']==('paused' if ready['sealedPausedCatalog'] else 'waiting-for-revealed-submission'),'Verifier not ready');break
                except Exception:
                    if attempt==39:raise
                    time.sleep(1)
            require(call('systemctl','show',*untouched,'-p','Id','-p','MainPID')==pids,'An unrelated service restarted')
            print(json.dumps({'refreshed':True,'sourceBundleSha256':manifest['sourceBundleSha256'],'catalogPaused':ready['sealedPausedCatalog'],'walletRestarted':False,'databasesRetained':True,'communityAndHistoricalAuthorityUnchanged':True}));return
        except BaseException:
            link=ROOT/'current.rollback';link.symlink_to(previous,target_is_directory=True);os.replace(link,ROOT/'current');run('systemctl','restart',SERVICE);raise RuntimeError('Paused V4 service refresh failed; previous source restored') from None
    backup=Path('/var/backups/flypow')/('factory-v4-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+str(os.getpid()));backup.mkdir(mode=0o700)
    shutil.copy2(WALLET,backup/'wallet-source.before.mjs');shutil.copy2(RUNTIME,backup/'wallet-runtime.before.json');shutil.copy2(NGINX,backup/'nginx.before.conf');old_link=os.readlink(ROOT/'current') if (ROOT/'current').is_symlink() else None
    legacy_active=subprocess.run(['systemctl','is-active',LEGACY],capture_output=True).returncode==0;legacy_enabled=subprocess.run(['systemctl','is-enabled',LEGACY],capture_output=True,text=True).stdout.strip()=='enabled'
    for label,path in [('authority',old['database'])]:
        with closing(sqlite3.connect('file:'+path+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(backup/(label+'.sqlite'))) as target:source.backup(target);require(target.execute('PRAGMA integrity_check').fetchone()[0]=='ok','Coherent database backup failed')
    user=pwd.getpwnam('flypow');STATE.mkdir(mode=0o700,parents=True,exist_ok=True);os.chown(STATE,user.pw_uid,user.pw_gid)
    for name in ('content','partial','journals','replays'):
        path=STATE/name;path.mkdir(mode=0o700,exist_ok=True);os.chown(path,user.pw_uid,user.pw_gid)
    for name,expected in manifest['content'].items():
        require(name==expected+'.bin' and digest(args.upload/'content'/name)==expected,'Compiled content mismatch');target=STATE/'content'/name
        if target.exists():require(digest(target)==expected,'Retained V4 content differs')
        else:atomic((args.upload/'content'/name).read_bytes(),target,0o600,user.pw_uid,user.pw_gid)
    try:
        run('systemctl','stop',WALLET_SERVICE)
        if legacy_active:run('systemctl','stop',LEGACY)
        run('systemctl','disable',LEGACY)
        st=WALLET.stat();atomic((args.upload/'wallet_mining_v3.mjs').read_bytes(),WALLET,st.st_mode&0o777,st.st_uid,st.st_gid)
        current=ROOT/'current.new';current.symlink_to(release,target_is_directory=True);os.replace(current,ROOT/'current')
        updated={**old,'continuousSupplyConfig':None};atomic((json.dumps(updated,indent=2)+'\n').encode(),RUNTIME,0o600,user.pw_uid,user.pw_gid)
        atomic((json.dumps(config,indent=2)+'\n').encode(),V4_RUNTIME,0o600,user.pw_uid,user.pw_gid)
        atomic((release/'deploy/target-v2/flybrainlabs-task-factory-v4.service').read_bytes(),Path('/etc/systemd/system')/(SERVICE+'.service'))
        marker='include /opt/flypow/deploy/target-v2/nginx-wallet-mining-v3.conf;';text=NGINX.read_text();include='include /opt/flypow/task-factory-v4/current/deploy/target-v2/nginx-task-factory-v4.conf;'
        if include not in text:require(text.count(marker)==1,'Unexpected original nginx layout');text=text.replace(marker,marker+'\n    '+include)
        atomic(text.encode(),NGINX);run('nginx','-t');run('systemctl','daemon-reload');run('systemctl','start',WALLET_SERVICE);run('systemctl','enable','--now',SERVICE);run('systemctl','reload','nginx')
        health=None
        for attempt in range(40):
            try:
                require(call('systemctl','is-active',SERVICE)=='active','V4 service inactive');health=json_get('http://127.0.0.1:8792/api/task-factory/v4/health');require(health['taskAuthority']=='contract' and health['verifier']['status']=='paused','Paused factory verifier has not become ready');break
            except Exception:
                if attempt==39:raise
                time.sleep(1)
        require(call('systemctl','show',*untouched,'-p','Id','-p','MainPID')==pids,'An unrelated service restarted')
        require(call('systemctl','is-active',WALLET_SERVICE,*untouched).splitlines()==['active']*3,'Retained user service unavailable')
        report={'schema':'flybrainlabs-factory-v4-node-switch-acceptance','recordedAtUtc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'V4-node-online-catalog-paused-awaiting-website-switch','sourceBundleSha256':manifest['sourceBundleSha256'],'sourceFiles':len(files),'allSourceHashesVerified':True,'nativeCompleteModelHashesVerified':True,'trustedVerifierKeys':2,'independentOperators':1,'serialReplay':True,'walletServiceRestarts':1,'legacyVerifierStopped':legacy_active,'legacyVerifierDisabled':True,'legacyNodeTaskSupplyDisabled':True,'communityAndHistoricalAuthorityUnchanged':True,'databaseMigration':False,'coherentDatabaseBackupVerified':True,'privateCredentialsCopiedToPublicSource':False,'catalogRoot':deployment['catalogRoot'],'taskCount':8,'rewardFbwPerWinner':200,'totalBudgetFbw':1600,'factoryStillPaused':True,'publicSiteChanged':False,'mainnet':False}
        (backup/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    except BaseException:
        subprocess.run(['systemctl','stop',SERVICE],capture_output=True)
        for source,destination in [('wallet-source.before.mjs',WALLET),('wallet-runtime.before.json',RUNTIME),('nginx.before.conf',NGINX)]:
            st=destination.stat();atomic((backup/source).read_bytes(),destination,st.st_mode&0o777,st.st_uid,st.st_gid)
        if old_link:
            rollback=ROOT/'current.rollback';rollback.symlink_to(old_link,target_is_directory=True);os.replace(rollback,ROOT/'current')
        run('nginx','-t');run('systemctl','reload','nginx');run('systemctl','start',WALLET_SERVICE)
        if legacy_enabled:run('systemctl','enable',LEGACY)
        if legacy_active:run('systemctl','start',LEGACY)
        raise RuntimeError('V4 node switch failed; original source/configuration restored, databases and model retained') from None

if __name__=='__main__':main()
