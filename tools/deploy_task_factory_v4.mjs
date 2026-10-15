#!/usr/bin/env node
// Upgrade only the existing Devnet program. This never creates/funds a factory.
// Backups and signed transport journals stay in an operator-only directory.
import {Connection,Keypair,PublicKey,Transaction,TransactionInstruction,SystemProgram,SYSVAR_CLOCK_PUBKEY,SYSVAR_RENT_PUBKEY} from '@solana/web3.js';
import {readFile,writeFile,mkdir,open,unlink} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {DevnetJournal} from './devnet_journal.mjs';
import {resume} from './resume_program_buffer.mjs';

const GENESIS='EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG';
const LOADER=new PublicKey('BPFLoaderUpgradeab1e11111111111111111111111');
const V3_FEATURE=new PublicKey('5cC3foj77CWun58pC51ebHFUWavHWKarWyR5UUik7dnC');
const digest=b=>createHash('sha256').update(b).digest('hex');
const require=(ok,message)=>{if(!ok)throw new Error(message);};
const meta=(pubkey,isWritable=false,isSigner=false)=>({pubkey:new PublicKey(pubkey),isWritable,isSigner});
const u32=(...v)=>{const b=Buffer.alloc(4*v.length);v.forEach((x,i)=>b.writeUInt32LE(x,i*4));return b;};
const loader=(keys,data)=>new TransactionInstruction({programId:LOADER,keys,data});
async function saveNew(path,value){await writeFile(path,JSON.stringify(value,null,2)+'\n',{mode:0o600,flag:'wx'});}
async function stored(path,make){try{return JSON.parse(await readFile(path,'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;const v=await make();await saveNew(path,v);return v;}}

export function validatePlan(p){
  require(p.schema==='flybrainlabs-task-factory-program-upgrade-v4'&&p.cluster==='devnet'&&p.genesisHash===GENESIS,'Only an explicit Devnet upgrade is supported');
  for(const k of ['programId','programData','authority'])new PublicKey(p[k]);
  for(const k of ['oldProgramSha256','newProgramSha256'])require(/^[a-f0-9]{64}$/.test(p[k]),'Exact ELF hashes required');
  require(Number.isSafeInteger(p.oldProgramBytes)&&p.oldProgramBytes>0&&Number.isSafeInteger(p.newProgramBytes)&&p.newProgramBytes>0,'Exact ELF sizes required');
  for(const k of ['maxTemporaryDebitLamports','maxAdditionalRentLamports','maxWriteFeesLamports'])require(Number.isSafeInteger(p[k])&&p[k]>0,'Finite integer Devnet cost limits required');
  require(p.maxTemporaryDebitLamports<=5_000_000_000&&p.maxAdditionalRentLamports<=1_000_000_000&&p.maxWriteFeesLamports<=5_000_000,'Finite Devnet rent and fee limits required');
  require(p.publicFbwBudgetAtoms==='0'&&p.activateFactory===false&&p.ownerDeploymentRequested===true,'This upgrade cannot activate or fund tasks');
  return p;
}

export async function deploy({planPath,elfPath,authorityKeyPath,privateDirectory,reportPath,apply=false}){
  const p=validatePlan(JSON.parse(await readFile(planPath,'utf8'))),elf=await readFile(elfPath);
  require(elf.length===p.newProgramBytes&&digest(elf)===p.newProgramSha256,'Reviewed ELF mismatch');
  require(elf.subarray(0,4).equals(Buffer.from([127,69,76,70]))&&elf.readUInt32LE(48)===3,'Reviewed SBPF v3 ELF required');
  const dir=resolve(privateDirectory),cwd=resolve(process.cwd());
  require(dir!==cwd&&!dir.startsWith(cwd+'/'),'Private transport must be outside the source checkout');
  const authority=Keypair.fromSecretKey(Uint8Array.from(JSON.parse(await readFile(authorityKeyPath,'utf8'))));
  require(authority.publicKey.toBase58()===p.authority,'Existing upgrade identity mismatch');
  const c=new Connection('https://api.devnet.solana.com','finalized'),program=new PublicKey(p.programId),pdAddress=new PublicKey(p.programData);
  require(await c.getGenesisHash()===GENESIS,'Wrong cluster');
  const feature=await c.getAccountInfo(V3_FEATURE),featureSlot=feature?.data[0]===1?feature.data.readBigUInt64LE(1):null;
  require(feature?.owner.toBase58()==='Feature111111111111111111111111111111111111'&&featureSlot!==null&&featureSlot<=BigInt(await c.getSlot('finalized')),'SBPF v3 is not active on the intended cluster');
  async function programData(){
    const [a,b]=await c.getMultipleAccountsInfo([program,pdAddress],'finalized');
    require(a?.executable&&a.owner.equals(LOADER)&&a.data.length===36&&a.data.readUInt32LE(0)===2&&new PublicKey(a.data.subarray(4,36)).equals(pdAddress),'Existing program identity mismatch');
    require(b?.owner.equals(LOADER)&&b.data.readUInt32LE(0)===3&&b.data[12]===1&&new PublicKey(b.data.subarray(13,45)).equals(authority.publicKey),'Existing upgrade authority mismatch');
    return b;
  }
  const initial=await programData(),targetLength=45+elf.length;
  const newCode=a=>a.data.length>=targetLength&&a.data.subarray(45,targetLength).equals(elf)&&a.data.subarray(targetLength).every(b=>b===0);
  const oldCode=a=>digest(a.data.subarray(45,45+p.oldProgramBytes))===p.oldProgramSha256&&a.data.subarray(45+p.oldProgramBytes).every(b=>b===0);
  require(newCode(initial)||oldCode(initial),'On-chain executable changed; review before deployment');
  const extension=Math.max(0,targetLength-initial.data.length),bufferRent=await c.getMinimumBalanceForRentExemption(37+elf.length,'finalized');
  const newRent=await c.getMinimumBalanceForRentExemption(Math.max(initial.data.length,targetLength),'finalized'),additionalRent=Math.max(0,newRent-initial.lamports);
  const balance=await c.getBalance(authority.publicKey,'finalized');
  require(additionalRent<=p.maxAdditionalRentLamports&&bufferRent+additionalRent+p.maxWriteFeesLamports+100_000<=p.maxTemporaryDebitLamports,'Rent/fee preflight exceeds frozen limits');
  require(newCode(initial)||balance>=bufferRent+additionalRent+p.maxWriteFeesLamports+100_000,'Insufficient existing Devnet SOL for bounded deployment');
  const preflight={schema:'flybrainlabs-task-factory-upgrade-preflight-v4',cluster:'devnet',genesisHash:GENESIS,programId:p.programId,programData:p.programData,authority:p.authority,oldProgramSha256:p.oldProgramSha256,newProgramSha256:p.newProgramSha256,newProgramBytes:elf.length,sbpfArchitecture:'v3',featureActivationSlot:String(featureSlot),onChainVersion:(await c.getVersion())['solana-core'],initialProgramDataBytes:initial.data.length,extensionBytes:extension,bufferRentLamports:bufferRent,additionalRentLamports:additionalRent,initialBalanceLamports:balance,alreadyUpgraded:newCode(initial),applyRequested:apply,publicFbwBudgetAtoms:'0',activateFactory:false};
  console.log(JSON.stringify(preflight));if(!apply)return preflight;
  await mkdir(dir,{recursive:true,mode:0o700});const lockPath=join(dir,'upgrade.lock'),lock=await open(lockPath,'wx',0o600);
  try{
    const scope=await stored(join(dir,'scope.json'),async()=>({plan:p,initialProgramDataBytes:initial.data.length,initialBalanceLamports:balance,initialLamports:initial.lamports}));
    require(JSON.stringify(scope.plan)===JSON.stringify(p),'Retained deployment plan differs');
    const journal=await new DevnetJournal(join(dir,'loader-journal.json'),authority,{maxTransactions:9,maxFees:100_000}).initialize({operation:'task-factory-v4-program-only',programId:p.programId,elfSha256:p.newProgramSha256});
    if(!newCode(await programData())){
      require(oldCode(await programData()),'Old program changed after preflight');
      const old=initial.data.subarray(45,45+p.oldProgramBytes),backup=join(dir,'previous-program.so');
      try{require(digest(await readFile(backup))===p.oldProgramSha256,'Retained rollback ELF mismatch');}catch(e){if(e.code!=='ENOENT')throw e;require(digest(old)===p.oldProgramSha256,'Rollback source mismatch');await writeFile(backup,old,{mode:0o600,flag:'wx'});}
      await stored(join(dir,'owned-accounts-before.json'),async()=>({accounts:(await c.getProgramAccounts(program,'finalized')).map(({pubkey,account:a})=>({address:pubkey.toBase58(),lamports:a.lamports,data:a.data.toString('base64'),sha256:digest(a.data)}))}));
      const bufferKeyPath=join(dir,'buffer.json');let buffer;
      try{buffer=Keypair.fromSecretKey(Uint8Array.from(JSON.parse(await readFile(bufferKeyPath,'utf8'))));}catch(e){if(e.code!=='ENOENT')throw e;buffer=Keypair.generate();await saveNew(bufferKeyPath,Array.from(buffer.secretKey));}
      const existing=await c.getAccountInfo(buffer.publicKey,'finalized');
      require(!existing||(existing.owner.equals(LOADER)&&existing.data.length===37+elf.length&&existing.data.readUInt32LE(0)===1&&existing.data[4]===1&&new PublicKey(existing.data.subarray(5,37)).equals(authority.publicKey)),'Retained buffer identity mismatch');
      await journal.run('create-buffer',[SystemProgram.createAccount({fromPubkey:authority.publicKey,newAccountPubkey:buffer.publicKey,lamports:bufferRent,space:37+elf.length,programId:LOADER}),loader([meta(buffer.publicKey,true),meta(authority.publicKey)],u32(0))],[buffer],async()=>!!await c.getAccountInfo(buffer.publicKey,'finalized'));
      await resume({elfPath,bufferKeyPath,authorityKeyPath,journalPath:join(dir,'write-journal.json'),maxFeeLamports:p.maxWriteFeesLamports,batchSize:24});
      const complete=await c.getAccountInfo(buffer.publicKey,'finalized');require(complete?.data.subarray(37).equals(elf),'Transported buffer ELF mismatch');
      const beforeExtend=await programData();require(oldCode(beforeExtend),'Program changed during buffer upload');
      const frozenExtension=Math.max(0,targetLength-scope.initialProgramDataBytes);
      if(frozenExtension){
        require(beforeExtend.data.length===scope.initialProgramDataBytes||beforeExtend.data.length===targetLength,'Unexpected program allocation');
        await journal.run('extend-existing-program',loader([meta(pdAddress,true),meta(program,true),meta(SystemProgram.programId),meta(authority.publicKey,true,true)],u32(6,frozenExtension)),[],async()=>(await programData()).data.length===targetLength);
      }
      require((await programData()).data.length>=targetLength,'Program allocation incomplete');
      const upgrade=loader([meta(pdAddress,true),meta(program,true),meta(buffer.publicKey,true),meta(authority.publicKey,true),meta(SYSVAR_RENT_PUBKEY),meta(SYSVAR_CLOCK_PUBKEY),meta(authority.publicKey,false,true)],u32(3));
      const latest=await c.getLatestBlockhash('finalized'),tx=new Transaction({feePayer:authority.publicKey,recentBlockhash:latest.blockhash}).add(upgrade);tx.sign(authority);
      const simulation=await c.simulateTransaction(tx);require(!simulation.value.err,'Intended-cluster upgrade simulation rejected: '+JSON.stringify(simulation.value.err));
      console.log(JSON.stringify({upgradeSimulationPassed:true,computeUnits:simulation.value.unitsConsumed}));
      await journal.run('upgrade-reviewed-program',upgrade,[],async()=>newCode(await programData()),{replacementSafe:false});
    }
    const final=await programData();require(newCode(final),'Finalized deployed ELF mismatch');
    const before=JSON.parse(await readFile(join(dir,'owned-accounts-before.json'),'utf8'));
    const after=await c.getProgramAccounts(program,'finalized'),afterMap=new Map(after.map(({pubkey,account:a})=>[pubkey.toBase58(),digest(a.data)]));
    const changed=before.accounts.filter(a=>afterMap.get(a.address)!==a.sha256).map(a=>a.address);
    const bkey=Keypair.fromSecretKey(Uint8Array.from(JSON.parse(await readFile(join(dir,'buffer.json'),'utf8'))));
    const bufferAfter=await c.getAccountInfo(bkey.publicKey,'finalized');require(!bufferAfter||bufferAfter.lamports===0,'Deployment buffer rent was not returned');
    const report={schema:'flybrainlabs-task-factory-program-deployment-v4',recordedAtUtc:new Date().toISOString(),status:'devnet-program-upgraded-factory-activation-pending',cluster:'devnet',genesisHash:GENESIS,programId:p.programId,programData:p.programData,upgradeAuthority:p.authority,programSha256:p.newProgramSha256,previousProgramSha256:p.oldProgramSha256,programBytes:elf.length,programDataBytes:final.data.length,deployedSlot:String(final.data.readBigUInt64LE(4)),commitment:'finalized',sbpfArchitecture:'v3',intendedClusterV3FeatureVerified:true,reviewedBufferHashVerified:true,rollbackBinaryRetained:true,bufferRentReturned:true,ownedAccountsBefore:before.accounts.length,ownedAccountsAfter:after.length,existingAccountDataUnchanged:changed.length===0,concurrentlyChangedAccounts:changed.length,projectBalanceBeforeLamports:String(scope.initialBalanceLamports),projectBalanceAfterLamports:String(await c.getBalance(authority.publicKey,'finalized')),loaderReceipts:journal.publicReceipts(),publicFactoryEnabled:false,newPublicTasks:0,newPublicFbwBudgetAtoms:'0',mainnet:false,formalIssuance:false};
    await writeFile(reportPath,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));return report;
  }finally{await lock.close();await unlink(lockPath);}
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  const [planPath,elfPath,authorityKeyPath,privateDirectory,reportPath,flag]=process.argv.slice(2);
  if(!reportPath||(flag&&flag!=='--apply'))throw new Error('Usage: deploy_task_factory_v4.mjs PLAN ELF EXISTING_AUTHORITY_KEY PRIVATE_DIRECTORY PUBLIC_REPORT [--apply]');
  deploy({planPath,elfPath,authorityKeyPath,privateDirectory,reportPath,apply:flag==='--apply'}).catch(e=>{console.error('Devnet program upgrade stopped: '+e.message);process.exitCode=1;});
}
