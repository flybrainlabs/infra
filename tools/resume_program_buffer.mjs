// Resume one existing authorized Devnet buffer. No account creation or deployment.
// Signed transport journals remain private, outside the source checkout.
import {Connection,Keypair,PublicKey,Transaction,TransactionInstruction} from '@solana/web3.js';
import {readFile,writeFile,rename,mkdir,open,unlink} from 'node:fs/promises';
import {dirname,resolve} from 'node:path';
import {createHash} from 'node:crypto';

const LOADER=new PublicKey('BPFLoaderUpgradeab1e11111111111111111111111');
const GENESIS='EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG';
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const digest=b=>createHash('sha256').update(b).digest('hex');
async function save(path,value){const temp=path+'.tmp';await writeFile(temp,JSON.stringify(value,null,2)+'\n',{mode:0o600});await rename(temp,path);}
function base58(bytes){const alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';let n=BigInt('0x'+Buffer.from(bytes).toString('hex')),s='';while(n){s=alphabet[Number(n%58n)]+s;n/=58n;}for(const b of bytes){if(b)break;s='1'+s;}return s;}
export function writeInstruction(buffer,authority,offset,bytes){
  // bincode UpgradeableLoaderInstruction::Write: u32 tag, u32 offset, u64 length.
  const data=Buffer.alloc(16+bytes.length);data.writeUInt32LE(1,0);data.writeUInt32LE(offset,4);data.writeBigUInt64LE(BigInt(bytes.length),8);Buffer.from(bytes).copy(data,16);
  return new TransactionInstruction({programId:LOADER,keys:[{pubkey:buffer,isWritable:true,isSigner:false},{pubkey:authority,isWritable:false,isSigner:true}],data});
}
export async function resume({elfPath,bufferKeyPath,authorityKeyPath,journalPath,maxFeeLamports=5_000_000,batchSize=16}){
  if(resolve(journalPath).startsWith(resolve(process.cwd())+'/'))throw new Error('Journal must be outside the checkout');
  await mkdir(dirname(journalPath),{recursive:true,mode:0o700});const lockPath=journalPath+'.lock',lock=await open(lockPath,'wx',0o600);
  try{
    const key=async p=>Keypair.fromSecretKey(Uint8Array.from(JSON.parse(await readFile(p,'utf8'))));
    const [elf,buffer,authority]=await Promise.all([readFile(elfPath),key(bufferKeyPath),key(authorityKeyPath)]);
    const c=new Connection('https://api.devnet.solana.com','finalized');if(await c.getGenesisHash()!==GENESIS)throw new Error('Genesis mismatch');
    const scope={elfSha256:digest(elf),buffer:buffer.publicKey.toBase58(),authority:authority.publicKey.toBase58(),genesisHash:GENESIS};
    let journal;try{journal=JSON.parse(await readFile(journalPath,'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;journal={schema:'flybrainlabs-buffer-transport-v1',scope,records:[]};}
    if(JSON.stringify(journal.scope)!==JSON.stringify(scope))throw new Error('Journal scope mismatch');
    const ranges=Array.from({length:Math.ceil(elf.length/900)},(_,n)=>({offset:n*900,bytes:elf.subarray(n*900,Math.min((n+1)*900,elf.length))}));
    async function inspect(){
      const a=await c.getAccountInfo(buffer.publicKey,'finalized');
      if(!a?.owner.equals(LOADER)||a.data.length!==37+elf.length||a.data.readUInt32LE(0)!==1||a.data[4]!==1||!new PublicKey(a.data.subarray(5,37)).equals(authority.publicKey))throw new Error('Existing buffer identity mismatch');
      return {a,missing:ranges.filter(r=>Buffer.compare(a.data.subarray(37+r.offset,37+r.offset+r.bytes.length),r.bytes)!==0)};
    }
    const started=await inspect();console.log(JSON.stringify({scope,missing:started.missing.length,balanceLamports:await c.getBalance(authority.publicKey,'finalized'),maxFeeLamports}));
    // Reconcile retained signatures before creating any replacement transactions.
    for(;;){
      const {a,missing}=await inspect();if(!missing.length){console.log(JSON.stringify({complete:true,buffer:scope.buffer,elfSha256:scope.elfSha256,bufferSha256:digest(a.data.subarray(37)),records:journal.records.length}));return;}
      const offsets=new Set(missing.map(r=>r.offset)),height=await c.getBlockHeight('finalized');
      const retained=journal.records.filter(r=>offsets.has(r.offset)&&r.lastValidBlockHeight>=height&&!['finalized','failed'].includes(r.state));
      const latest=await c.getLatestBlockhash('finalized'),batch=[];
      for(const r of missing.slice(0,batchSize)){
        let record=retained.find(x=>x.offset===r.offset);
        if(!record){
          const attempts=journal.records.filter(x=>x.offset===r.offset).length;if(attempts>=3)throw new Error('Range retry budget exhausted');
          const tx=new Transaction({feePayer:authority.publicKey,recentBlockhash:latest.blockhash}).add(writeInstruction(buffer.publicKey,authority.publicKey,r.offset,r.bytes));tx.sign(authority);
          const fee=(await c.getFeeForMessage(tx.compileMessage(),'finalized')).value;if(fee===null||fee>10_000||journal.records.reduce((n,x)=>n+x.feeLamports,0)+fee>maxFeeLamports)throw new Error('Finite fee ceiling exceeded');
          record={offset:r.offset,length:r.bytes.length,sha256:digest(r.bytes),signedBytes:tx.serialize().toString('base64'),signature:base58(tx.signature),lastValidBlockHeight:latest.lastValidBlockHeight,feeLamports:fee,sends:0,state:'prepared'};journal.records.push(record);await save(journalPath,journal);
        }
        batch.push(record);
        if(record.sends<4){record.sends++;await save(journalPath,journal);try{const sig=await c.sendRawTransaction(Buffer.from(record.signedBytes,'base64'),{maxRetries:0,skipPreflight:false});if(sig!==record.signature)throw new Error('Signature mismatch');record.state='sent';}catch{record.state='send-unknown';}await save(journalPath,journal);}
        await pause(300);
      }
      for(let poll=0;poll<22;poll++){
        await pause(2000);const observed=await c.getSignatureStatuses(batch.map(r=>r.signature),{searchTransactionHistory:true});let finished=true;
        observed.value.forEach((status,i)=>{if(status?.confirmationStatus==='finalized'){batch[i].state=status.err?'failed':'finalized';if(status.err)batch[i].error='CHAIN_REJECTED';}else finished=false;});await save(journalPath,journal);
        if(batch.some(r=>r.state==='failed'))throw new Error('Loader rejected a write; private journal retained');
        if(finished||await c.getBlockHeight('finalized')>Math.min(...batch.map(r=>r.lastValidBlockHeight)))break;
      }
      const next=await inspect();console.log(JSON.stringify({matching:ranges.length-next.missing.length,total:ranges.length,remaining:next.missing.length,records:journal.records.length}));
    }
  }finally{await lock.close();await unlink(lockPath);}
}
if(process.argv[1]===new URL(import.meta.url).pathname){
  const [elfPath,bufferKeyPath,authorityKeyPath,journalPath]=process.argv.slice(2);
  if(!journalPath)throw new Error('Usage: resume_program_buffer.mjs ELF EXISTING_BUFFER_KEY AUTHORITY_KEY PRIVATE_JOURNAL');
  resume({elfPath,bufferKeyPath,authorityKeyPath,journalPath}).catch(e=>{console.error('Buffer resume stopped: '+(e.message||'RPC unavailable'));process.exitCode=1;});
}
