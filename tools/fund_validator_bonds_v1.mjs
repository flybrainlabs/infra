// Owner-approved collateral sponsorship from a separate finite validator stage.
// The evidence is an endowment authorization, never fabricated scientific work.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Connection,Keypair,PublicKey,SystemProgram,SYSVAR_INSTRUCTIONS_PUBKEY} from '@solana/web3.js';
import {TOKEN_PROGRAM_ID,getAssociatedTokenAddressSync,createAssociatedTokenAccountIdempotentInstruction,unpackAccount} from '@solana/spl-token';
import {addresses,decodeGlobal,decodeStage,decodeSlot,instruction,acceptanceInstructions,Writer,meta} from './economy_v2_client.mjs';
import {DevnetJournal} from './devnet_journal.mjs';
import {DEVNET_GENESIS,MINIMUM_BOND_ATOMS} from '../web/validator-bond-v1.mjs';
const check=(ok,code)=>{if(!ok)throw new Error(code);};
const hash=v=>new Uint8Array(createHash('sha256').update(v).digest());
const bytes=v=>Buffer.from(v,'hex');
const loadKey=async path=>{const b=await readFile(path);return b.length===32?Keypair.fromSeed(b):Keypair.fromSecretKey(Uint8Array.from(JSON.parse(b.toString())));};
// Keep administrative traffic below the public provider's rate and honor its
// cooldown. Existing signed packets are reconciled by the retained journal.
function operatorFetch(){
 let tail=Promise.resolve(),next=0;
 return (url,options)=>{
  const run=async()=>{
   for(let attempt=0;attempt<5;attempt++){
    await new Promise(ok=>setTimeout(ok,Math.max(0,next-Date.now())));
    const response=await fetch(url,{...options,signal:AbortSignal.timeout(30000)});next=Date.now()+3000;
    if(response.status!==429)return response;
    const value=response.headers.get('retry-after'),seconds=Number(value),date=Date.parse(value||'');
    const requested=Number.isFinite(seconds)&&seconds>0?seconds*1000:Number.isFinite(date)?Math.max(0,date-Date.now()):0;
    next=Date.now()+Math.max(requested,30000*(attempt+1));
    if(attempt===4)return response;
    await response.arrayBuffer();
   }
  };
  const current=tail.then(run,run);tail=current.catch(()=>{});return current;
 };
}
export async function fundValidatorBonds({runtimePath,fleetPath,planPath,privateDirectory,apply=false}){
 const c=JSON.parse(await readFile(runtimePath,'utf8')),fleet=JSON.parse(await readFile(fleetPath,'utf8')),plan=JSON.parse(await readFile(planPath,'utf8'));
 check(plan.cluster==='devnet'&&plan.genesisHash===DEVNET_GENESIS&&plan.ownerRequested===true&&plan.validatorCount===4&&plan.perValidatorAtoms===String(MINIMUM_BOND_ATOMS)&&plan.totalAtoms===String(MINIMUM_BOND_ATOMS*4n),'Exact approved collateral scope required');
 check(fleet.members.length===4&&new Set(fleet.members.map(m=>m.publicKey)).size===4,'Four distinct scientific owners required');
 const authority=await loadKey(c.authorityKeyFile),signers=await Promise.all(c.verifierKeyFiles.map(loadKey)),conn=new Connection(c.rpcUpstream,{commitment:'finalized',disableRetryOnRateLimit:true,fetch:operatorFetch()});
 check(authority.publicKey.toBase58()===plan.authority&&await conn.getGenesisHash()===DEVNET_GENESIS,'Project and Devnet identity required');
 const program=new PublicKey(c.deployment.programId),a=addresses(program),global=async()=>decodeGlobal((await conn.getAccountInfo(a.global,'finalized')).data),g=await global();
 check(new PublicKey(g.mint).toBase58()===plan.mint&&new PublicKey(g.authority).equals(authority.publicKey)&&signers.length>=2&&signers.slice(0,2).every(s=>g.settlers.some(k=>new PublicKey(k).equals(s.publicKey))),'Existing authority, mint and settlement signers required');
 const dir=resolve(privateDirectory);check(!dir.startsWith(resolve(process.cwd())+'/'),'Private journal outside source required');await mkdir(dir,{recursive:true,mode:0o700});
 const scope={operation:'owner-approved-validator-collateral-sponsorship-v1',bondProgramId:plan.programId,totalAtoms:plan.totalAtoms,owners:fleet.members.map(m=>({id:m.id,publicKey:m.publicKey}))};
 const stageId=hash('flybrain/validator-collateral-sponsorship/devnet/20261023/v1'),stage=a.stage(stageId),existing=await conn.getAccountInfo(stage,'finalized');
 if(existing){const s=decodeStage(existing.data);check(s.budget===MINIMUM_BOND_ATOMS*4n&&s.pool===1,'Retained finite sponsorship differs');}
 else check(g.available[1]>=MINIMUM_BOND_ATOMS*4n,'Insufficient unallocated validator-pool balance');
 const owners=fleet.members.map(m=>({...m,address:new PublicKey(bytes(m.publicKey)),source:getAssociatedTokenAddressSync(new PublicKey(plan.mint),new PublicKey(bytes(m.publicKey)))}));
 const preflight={atUtc:new Date().toISOString(),cluster:'devnet',mint:plan.mint,source:'existing-validator-pool',sourcePool:a.pool(1).toBase58(),stage:stage.toBase58(),totalAtoms:plan.totalAtoms,validatorPoolAvailableAtoms:String(g.available[1]),owners:owners.map(o=>({id:o.id,address:o.address.toBase58(),tokenAccount:o.source.toBase58(),atoms:plan.perValidatorAtoms})),applyRequested:apply};
 await writeFile(join(dir,'preflight.json'),JSON.stringify(preflight,null,2)+'\n',{mode:0o600});console.log(JSON.stringify(preflight));if(!apply)return preflight;
 const journal=await new DevnetJournal(join(dir,'funding-journal.json'),authority,{maxTransactions:32,maxFees:400000});journal.connection=conn;await journal.initialize(scope);
 // Freeze the on-chain stage deadline in the first private plan, for safe retries.
 let frozen;try{frozen=JSON.parse(await readFile(join(dir,'stage-plan.json'),'utf8'));}catch(error){if(error.code!=='ENOENT')throw error;const slot=await conn.getSlot('finalized');frozen={deadline:(await conn.getBlockTime(slot))+7*86400,stageId:Buffer.from(stageId).toString('hex'),scope};await writeFile(join(dir,'stage-plan.json'),JSON.stringify(frozen,null,2)+'\n',{mode:0o600,flag:'wx'});}
 check(JSON.stringify(frozen.scope)===JSON.stringify(scope),'Retained sponsorship owner scope changed');
 await journal.run('open-finite-validator-collateral-stage',instruction(program,[meta(a.global,true),meta(stage,true),meta(authority.publicKey,true,true),meta(SystemProgram.programId)],2,new Writer().key(stageId).u8(1).u64(MINIMUM_BOND_ATOMS*4n).i64(frozen.deadline).result()),[],async()=>!!await conn.getAccountInfo(stage,'finalized'));
 for(const o of owners){
  await journal.run('create-owner-token-account-'+o.id,createAssociatedTokenAccountIdempotentInstruction(authority.publicKey,o.source,o.address,new PublicKey(plan.mint)),[],async()=>!!await conn.getAccountInfo(o.source,'finalized'));
  const task=hash('flybrain/validator-collateral-sponsorship/task/'+plan.programId+'/'+o.id),unit=bytes(o.publicKey),slot=a.slot(task,2,unit),paymentId=hash('flybrain/validator-collateral-sponsorship/payment/'+plan.programId+'/'+o.id),payment=a.payment(slot,paymentId);
  const evidenceObject={schema:'flybrain-validator-collateral-sponsorship-v1',ownerApproved:true,scope:'Devnet collateral endowment, not earned scientific work or mining reward',validatorId:o.id,validator:o.address.toBase58(),bondProgramId:plan.programId,mint:plan.mint,atoms:plan.perValidatorAtoms,minimumDays:30,exitWaitDays:7},evidence=hash(JSON.stringify(evidenceObject));
  await writeFile(join(dir,o.id+'-authorization.json'),JSON.stringify(evidenceObject,null,2)+'\n',{mode:0o600});
  await journal.run('reserve-collateral-'+o.id,instruction(program,[meta(a.global),meta(stage,true),meta(slot,true),meta(authority.publicKey,true,true),meta(SystemProgram.programId)],3,new Writer().key(task).key(unit).u8(2).key(o.address).key(o.address).u64(MINIMUM_BOND_ATOMS).result()),[],async()=>{const i=await conn.getAccountInfo(slot,'finalized');if(!i)return false;const s=decodeSlot(i.data);check(s.amount===MINIMUM_BOND_ATOMS&&new PublicKey(s.beneficiary).equals(o.address),'Retained sponsorship reservation mismatch');return true;});
  const s=decodeSlot((await conn.getAccountInfo(slot,'finalized')).data),accept=acceptanceInstructions(program,g,s,evidence,signers.slice(0,2),[meta(a.global),meta(stage,true),meta(slot,true),meta(SYSVAR_INSTRUCTIONS_PUBKEY)]),claim=instruction(program,[meta(a.global),meta(stage),meta(slot,true),meta(a.pool(1),true),meta(o.source,true),meta(payment,true),meta(authority.publicKey,true,true),meta(SystemProgram.programId),meta(TOKEN_PROGRAM_ID)],5,new Writer().key(paymentId).u64(MINIMUM_BOND_ATOMS).result());
  await journal.run('pay-collateral-'+o.id,[...accept,claim],[],async()=>{const i=await conn.getAccountInfo(slot,'finalized');return !!i&&decodeSlot(i.data).paid===MINIMUM_BOND_ATOMS;});
  const balance=unpackAccount(o.source,await conn.getAccountInfo(o.source,'finalized')).amount;
  check(balance>=MINIMUM_BOND_ATOMS,'Finalized collateral did not reach validator owner');
 }
 await journal.run('close-fully-distributed-collateral-stage',instruction(program,[meta(a.global,true),meta(stage,true),meta(authority.publicKey,false,true)],7),[],async()=>decodeStage((await conn.getAccountInfo(stage,'finalized')).data).closed);
 const after=await global(),report={...preflight,finalized:true,atUtc:new Date().toISOString(),validatorPoolAvailableAfterAtoms:String(after.available[1]),sourceBudgetAtoms:plan.totalAtoms,additionalMiningRewardAuthorization:false,newMinting:false,receipts:journal.publicReceipts()};
 await writeFile(join(dir,'funding-final.json'),JSON.stringify(report,null,2)+'\n',{mode:0o600});console.log(JSON.stringify(report));return report;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){const [runtimePath,fleetPath,planPath,privateDirectory,flag]=process.argv.slice(2);if(!privateDirectory||(flag&&flag!=='--apply'))throw new Error('RUNTIME FLEET PLAN PRIVATE_DIR [--apply] required');fundValidatorBonds({runtimePath,fleetPath,planPath,privateDirectory,apply:flag==='--apply'}).catch(error=>{console.error(JSON.stringify({code:'VALIDATOR_COLLATERAL_FUNDING_STOPPED',errorType:error.constructor.name}));process.exitCode=1;});}
