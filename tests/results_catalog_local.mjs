// Verify the non-fixture local launcher with actual message signatures and data.
import assert from 'node:assert/strict';
import {mkdtemp,rm,readFile,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createServer} from 'node:net';
import {once} from 'node:events';
import {Keypair} from '@solana/web3.js';
import {sign,createPrivateKey} from 'node:crypto';
import {serveResultsCatalog} from '../tools/serve_results_catalog.mjs';
const release=process.argv[2];if(!release)throw new Error('Pass a prepared static review export');
const temporary=await mkdtemp(join(tmpdir(),'fbw-local-launcher-')),user=Keypair.generate();let server;
const listener=createServer();listener.listen(0,'127.0.0.1');await once(listener,'listening');const port=listener.address().port;await new Promise(done=>listener.close(done));
async function request(path,body=null,login=null,origin=server.origin){const headers={Origin:origin};if(body!==null)headers['Content-Type']='application/json';if(login){headers.Authorization='Bearer '+login.token;if(body!==null)headers['X-Mining-CSRF']=login.csrfToken;}const r=await fetch(server.origin+path,{method:body===null?'GET':'POST',headers,body:body===null?undefined:JSON.stringify(body)});return {status:r.status,value:await r.json()};}
async function signIn(){const {value:q}=await request('/api/mining/v3/challenge',{address:user.publicKey.toBase58()});const signature=sign(null,Buffer.from(q.message),createPrivateKey({key:Buffer.concat([Buffer.from('302e020100300506032b657004220420','hex'),Buffer.from(user.secretKey.subarray(0,32))]),format:'der',type:'pkcs8'})).toString('base64');const r=await request('/api/mining/v3/login',{address:user.publicKey.toBase58(),nonce:q.input.nonce,signedMessage:q.message,signature});assert.equal(r.status,200);return r.value;}
try{
 server=await serveResultsCatalog({release,data:join(temporary,'local'),port,adminWallets:[]});
 assert.equal((await fetch(server.origin+'/results/')).status,200);
 const config=await(await fetch(server.origin+'/assets/data/wallet-mining-v3.json')).json();assert.equal(config.apiBase,server.origin);assert.equal(config.enabled,false);assert.ok(!('rpcUpstream'in config));assert.ok(!('database'in config));
 const login=await signIn();
 assert.equal((await request('/api/community/projects/admin/applications',null,login)).status,403);
 assert.equal((await request('/api/mining/v3/challenge',{address:user.publicKey.toBase58()},null,'https://untrusted.example')).status,403);
 assert.equal((await request('/api/mining/v3/grants/create',{},login)).status,503);
 assert.equal((await fetch(server.origin+'/auth.db')).status,404);
 const body={projectId:'FBW-P01',requestId:crypto.randomUUID(),application:{roles:['develop'],contact:{type:'email',value:'local-launcher@example.invalid'},consent:true,consentVersion:'project-coordination-v1'}};
 const submitted=await request('/api/community/projects/applications/submit',body,login);assert.equal(submitted.status,200);const id=submitted.value.application.id;
 assert.equal((await request('/api/community/projects/stats')).value.totalUniqueApplicants,1);
 await server.close();server=null;
 server=await serveResultsCatalog({release,data:join(temporary,'local'),port,adminWallets:[user.publicKey.toBase58()]});
 const retained=await request('/api/community/projects/me',null,login);assert.equal(retained.value.applications[0].id,id);
 assert.equal((await request('/api/community/projects/admin/applications',null,login)).value.total,1);
 assert.deepEqual((await request('/api/community/projects/applications/submit',body,login)).value,submitted.value);
 await server.close();server=null;
 // A mistakenly selected production-like database is never opened or migrated.
 const other=join(temporary,'auth.db');await writeFile(other,'must remain untouched');
 await assert.rejects(serveResultsCatalog({release,data:temporary,port}),/unmarked/);assert.equal(await readFile(other,'utf8'),'must remain untouched');
 console.log(JSON.stringify({passed:true,checks:14,actualSignature:true,localPersistence:true,financialRequestsAllowed:false,productionChanged:false}));
}finally{if(server)await server.close();await rm(temporary,{recursive:true,force:true});}
