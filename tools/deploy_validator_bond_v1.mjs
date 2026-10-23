// Deploy only a separate, bounded Devnet validator collateral program.
// This tool neither funds validator wallets nor changes historical programs.
import {Connection,Keypair,PublicKey,TransactionInstruction,SystemProgram,SYSVAR_CLOCK_PUBKEY,SYSVAR_RENT_PUBKEY} from '@solana/web3.js';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {DevnetJournal} from './devnet_journal.mjs';
import {resume} from './resume_program_buffer.mjs';
import {bondAddresses,bondInstruction,decodeBondPolicy,DEVNET_GENESIS} from '../web/validator-bond-v1.mjs';
const LOADER=new PublicKey('BPFLoaderUpgradeab1e11111111111111111111111');
const check=(v,code)=>{if(!v)throw new Error(code);};
const digest=v=>createHash('sha256').update(v).digest('hex');
const meta=(pubkey,isWritable=false,isSigner=false)=>({pubkey,isWritable,isSigner});
const loader=(keys,data)=>new TransactionInstruction({programId:LOADER,keys,data});
const u32=n=>{const b=Buffer.alloc(4);b.writeUInt32LE(n);return b;};
const key=async p=>Keypair.fromSecretKey(Uint8Array.from(JSON.parse(await readFile(p,'utf8'))));
export async function deployValidatorBond({planPath,elfPath,authorityKeyPath,programKeyPath,bufferKeyPath,privateDirectory,apply=false}){
 const p=JSON.parse(await readFile(planPath,'utf8')),elf=await readFile(elfPath),authority=await key(authorityKeyPath),program=await key(programKeyPath),buffer=await key(bufferKeyPath);
 check(p.schema==='flybrain-validator-bond-deployment-plan-v1'&&p.cluster==='devnet'&&p.genesisHash===DEVNET_GENESIS&&p.ownerRequested===true,'Explicit Devnet plan required');
 check(p.programId===program.publicKey.toBase58()&&p.authority===authority.publicKey.toBase58()&&p.elfSha256===digest(elf)&&p.elfBytes===elf.length,'Reviewed identity and ELF required');
 check(elf.subarray(0,4).equals(Buffer.from([127,69,76,70]))&&elf.readUInt32LE(48)===3,'SBPF v3 ELF required');
 check(p.maxTemporaryDebitLamports>0&&p.maxTemporaryDebitLamports<=2500000000&&p.maxWriteFeesLamports>0&&p.maxWriteFeesLamports<=2000000,'Finite deployment limits required');
 const dir=resolve(privateDirectory);check(!dir.startsWith(resolve(process.cwd())+'/'),'Private transport outside checkout required');
 const c=new Connection('https://api.devnet.solana.com','finalized');check(await c.getGenesisHash()===DEVNET_GENESIS,'Wrong chain');
 const a=bondAddresses(program.publicKey),rentBuffer=await c.getMinimumBalanceForRentExemption(37+elf.length),rentData=await c.getMinimumBalanceForRentExemption(45+elf.length),rentProgram=await c.getMinimumBalanceForRentExemption(36),initialSol=await c.getBalance(authority.publicKey,'finalized');
 const temporary=rentBuffer+rentData+rentProgram+p.maxWriteFeesLamports+1000000;
 check(temporary<=p.maxTemporaryDebitLamports&&initialSol>=temporary,'Bounded rent and fees exceed available balance');
 const feature=await c.getAccountInfo(new PublicKey('5cC3foj77CWun58pC51ebHFUWavHWKarWyR5UUik7dnC'),'finalized');
 check(feature?.data[0]===1&&feature.data.readBigUInt64LE(1)<=BigInt(await c.getSlot('finalized')),'SBPF v3 feature required');
 const already=await c.getAccountInfo(program.publicKey,'finalized');
 const codeMatches=async()=>{const [pi,pd]=await c.getMultipleAccountsInfo([program.publicKey,a.programData],'finalized');return !!(pi?.executable&&pi.owner.equals(LOADER)&&pi.data.length===36&&pi.data.readUInt32LE(0)===2&&new PublicKey(pi.data.subarray(4,36)).equals(a.programData)&&pd?.owner.equals(LOADER)&&pd.data.length===45+elf.length&&pd.data.readUInt32LE(0)===3&&pd.data[12]===1&&new PublicKey(pd.data.subarray(13,45)).equals(authority.publicKey)&&pd.data.subarray(45).equals(elf));};
 check(!already||await codeMatches(),'Existing program differs from reviewed new program');
 const preflight={atUtc:new Date().toISOString(),programId:p.programId,elfSha256:digest(elf),elfBytes:elf.length,rentBuffer,rentData,rentProgram,maximumTemporaryDebitLamports:temporary,initialSol,applyRequested:apply};
 console.log(JSON.stringify(preflight));if(!apply)return preflight;
 await mkdir(dir,{recursive:true,mode:0o700});
 const journal=await new DevnetJournal(join(dir,'loader-journal.json'),authority,{maxTransactions:8,maxFees:100000}).initialize({operation:'separate-validator-bond-v1',programId:p.programId,elfSha256:p.elfSha256,mint:p.mint});
 if(!await codeMatches()){
  await journal.run('create-reviewed-buffer',[SystemProgram.createAccount({fromPubkey:authority.publicKey,newAccountPubkey:buffer.publicKey,lamports:rentBuffer,space:37+elf.length,programId:LOADER}),loader([meta(buffer.publicKey,true),meta(authority.publicKey)],u32(0))],[buffer],async()=>{const b=await c.getAccountInfo(buffer.publicKey,'finalized');return !!(b&&b.owner.equals(LOADER)&&b.data.length===37+elf.length&&b.data.readUInt32LE(0)===1&&b.data[4]===1&&new PublicKey(b.data.subarray(5,37)).equals(authority.publicKey));});
  await resume({elfPath,bufferKeyPath,authorityKeyPath,journalPath:join(dir,'buffer-journal.json'),maxFeeLamports:p.maxWriteFeesLamports,batchSize:24});
  const b=await c.getAccountInfo(buffer.publicKey,'finalized');check(b&&digest(b.data.subarray(37))===p.elfSha256,'Written ELF mismatch');
  const data=Buffer.alloc(12);data.writeUInt32LE(2);data.writeBigUInt64LE(BigInt(elf.length),4);
  await journal.run('deploy-separate-validator-bond',[SystemProgram.createAccount({fromPubkey:authority.publicKey,newAccountPubkey:program.publicKey,lamports:rentProgram,space:36,programId:LOADER}),loader([meta(authority.publicKey,true,true),meta(a.programData,true),meta(program.publicKey,true),meta(buffer.publicKey,true),meta(SYSVAR_RENT_PUBKEY),meta(SYSVAR_CLOCK_PUBKEY),meta(SystemProgram.programId),meta(authority.publicKey,false,true)],data)],[program],codeMatches);
 }
 check(await codeMatches(),'Deployed code mismatch');
 await journal.run('initialize-fixed-bond-policy',bondInstruction(program.publicKey,0,{mint:p.mint,payer:authority.publicKey}),[],async()=>{const i=await c.getAccountInfo(a.policy,'finalized');return !!i&&i.owner.equals(program.publicKey);});
 const policy=decodeBondPolicy((await c.getAccountInfo(a.policy,'finalized')).data);
 check(new PublicKey(policy.mint).toBase58()===p.mint&&new PublicKey(policy.clearanceAuthority).equals(authority.publicKey)&&new PublicKey(policy.network).toBase58()===DEVNET_GENESIS,'Initialized policy mismatch');
 const report={schema:'flybrain-validator-bond-deployment-v1',cluster:'devnet',genesisHash:DEVNET_GENESIS,programId:p.programId,mint:p.mint,clearanceAuthority:p.authority,policy:a.policy.toBase58(),programData:a.programData.toBase58(),elfSha256:p.elfSha256,elfBytes:elf.length,minimumFbw:100000,minimumAtoms:String(policy.minimum),lockDays:30,exitWaitDays:7,exitClearanceRequired:true,slashingEnabled:false,finalized:true,upgradeAuthorityRetained:true,initialSol,finalSol:await c.getBalance(authority.publicKey,'finalized'),receipts:journal.publicReceipts(),atUtc:new Date().toISOString()};
 await writeFile(join(dir,'deployment.json'),JSON.stringify(report,null,2)+'\n',{mode:0o600});console.log(JSON.stringify(report));return report;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){const [planPath,elfPath,authorityKeyPath,programKeyPath,bufferKeyPath,privateDirectory,flag]=process.argv.slice(2);if(!privateDirectory||(flag&&flag!=='--apply'))throw new Error('PLAN ELF AUTHORITY_KEY PROGRAM_KEY BUFFER_KEY PRIVATE_DIR [--apply] required');deployValidatorBond({planPath,elfPath,authorityKeyPath,programKeyPath,bufferKeyPath,privateDirectory,apply:flag==='--apply'}).catch(()=>{console.error('Validator bond deployment stopped; private journals retained.');process.exitCode=1;});}
