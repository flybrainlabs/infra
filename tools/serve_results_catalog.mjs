// Local development uses persistent isolated data and actual wallet signatures.
import {createServer} from 'node:http';
import {readFile,mkdir,writeFile,chmod,realpath,stat} from 'node:fs/promises';
import {resolve,join,extname,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {once} from 'node:events';
import {DatabaseSync} from 'node:sqlite';
import {PublicKey} from '@solana/web3.js';
import {WalletMiningService} from './wallet_mining_v3.mjs';
import {SocialCommunityService} from './social_community.mjs';
import {serveSocial} from './social_server.mjs';

export async function serveResultsCatalog({release,data,port=8099,adminWallets=[]}) {
  if (!Number.isInteger(port)||port<1024||port>65535) throw new Error('Choose an unprivileged loopback port');
  const root=await realpath(release),directory=resolve(data),origin='http://127.0.0.1:'+port;
  if (directory===root||directory.startsWith(root+sep)) throw new Error('Private data must be outside the website export');
  if (!(await stat(join(root,'results/index.html'))).isFile()) throw new Error('Build the website export first');
  for (const wallet of adminWallets) if (new PublicKey(wallet).toBase58()!==wallet) throw new Error('Invalid administrator public key');
  await mkdir(directory,{recursive:true,mode:0o700});await chmod(directory,0o700);
  const marker=join(directory,'.fbw-results-local.json'),database=join(directory,'auth.db');
  let marked=false;try{marked=JSON.parse(await readFile(marker,'utf8')).schema==='fbw-results-local-v1';}catch(error){if(error.code!=='ENOENT')throw new Error('Invalid local data marker');}
  if (!marked) {
    for (const suffix of ['', '-wal','-shm']) {
      try {await stat(database+suffix);throw new Error('Refusing an existing unmarked database');} catch(error) {if(error.code!=='ENOENT')throw error;}
    }
    await writeFile(marker,JSON.stringify({schema:'fbw-results-local-v1',purpose:'local recruitment development'})+'\n',{flag:'wx',mode:0o600});
  }
  // This is public, checked-in identity data, never a private runtime config.
  const source=JSON.parse(await readFile(new URL('../web/data/wallet-mining-v3.json',import.meta.url),'utf8'));
  const config={};
  for (const key of ['schema','cluster','genesisHash','programId','mint','policyHash','stage','deadline','budgetAtoms','units','project','relayer','settlers','retentionSeconds','authorityId','symbol','decimals','defaultGrant','planState','paidAtoms']) config[key]=source[key];
  Object.assign(config,{apiBase:origin,rpc:'https://api.devnet.solana.com',origins:[origin],enabled:false,testOnly:true});
  const db=new DatabaseSync(database);await chmod(database,0o600);
  const auth=await new WalletMiningService(config,db,null).initialize();
  const community=await new SocialCommunityService(auth,JSON.parse(await readFile(new URL('../config/community-allocation-v1.json',import.meta.url),'utf8')),{adminWallets}).initialize();
  const social=serveSocial(community,{port:0});await once(social,'listening');
  const body=async req=>{const chunks=[];let size=0;for await(const chunk of req){size+=chunk.length;if(size>32768)throw Object.assign(new Error(),{status:413,code:'body_limit'});chunks.push(chunk);}return Buffer.concat(chunks);};
  const web=createServer(async(req,res)=>{
    try {
      res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
      const url=new URL(req.url,origin);
      if(req.headers.host!==new URL(origin).host)throw Object.assign(new Error(),{status:403,code:'local_host_required'});
      if(req.method==='OPTIONS')throw Object.assign(new Error(),{status:405,code:'same_origin_only'});
      if(url.pathname==='/assets/data/wallet-mining-v3.json') {
        if(req.method!=='GET')throw Object.assign(new Error(),{status:405});
        res.setHeader('Content-Type','application/json');res.end(JSON.stringify(config));return;
      }
      if(url.pathname.startsWith('/api/community/')||url.pathname.startsWith('/api/social/')) {
        if(!['GET','POST'].includes(req.method))throw Object.assign(new Error(),{status:405});
        if(req.method==='POST')auth.checkOrigin(req.headers.origin);
        const bytes=await body(req),headers=Object.fromEntries(Object.entries(req.headers).filter(([key])=>!['host','connection','content-length','origin'].includes(key)));
        headers.origin=req.headers.origin||origin;
        const response=await fetch('http://127.0.0.1:'+social.address().port+url.pathname+url.search,{method:req.method,headers,body:req.method==='POST'?bytes:undefined,redirect:'manual',signal:AbortSignal.timeout(20000)});
        res.writeHead(response.status,{'Content-Type':response.headers.get('content-type')||'application/json'});res.end(Buffer.from(await response.arrayBuffer()));return;
      }
      if(url.pathname.startsWith('/api/mining/v3/')) {
        const action=url.pathname.slice('/api/mining/v3/'.length);
        if(!['challenge','login','logout'].includes(action)||req.method!=='POST')throw Object.assign(new Error(),{status:503,code:'LOCAL_RECRUITMENT_IDENTITY_ONLY'});
        auth.checkOrigin(req.headers.origin);
        if(req.headers['content-type']?.split(';')[0]!=='application/json')throw Object.assign(new Error(),{status:415,code:'content_type_required'});
        const value=JSON.parse((await body(req)).toString());
        const result=action==='challenge'?auth.challenge(req.headers.origin,value):action==='login'?auth.login(req.headers.origin,value):auth.logout(auth.authenticate(req.headers.origin,req.headers,true));
        res.setHeader('Content-Type','application/json');res.end(JSON.stringify(result));return;
      }
      if(url.pathname.startsWith('/api/'))throw Object.assign(new Error(),{status:503,code:'local_api_not_configured'});
      if(!['GET','HEAD'].includes(req.method))throw Object.assign(new Error(),{status:405});
      if(['/results','/results/'].includes(url.pathname)) {
        const result=/^[a-f0-9]{64}$/.test(url.searchParams.get('id')||'');
        if(result||['input','task','model','type','evidence','since','related'].some(key=>url.searchParams.has(key))) {res.writeHead(302,{Location:(result?'/results/detail/':'/results/publications/')+url.search});res.end();return;}
      }
      let pathname=decodeURIComponent(url.pathname);
      if(/^\/results\/[a-f0-9]{64}\/?$/.test(pathname)){res.writeHead(302,{Location:'/results/detail/?id='+pathname.split('/')[2]});res.end();return;}
      if(!extname(pathname)&&!pathname.endsWith('/')){res.writeHead(302,{Location:pathname+'/'+url.search});res.end();return;}
      const file=resolve(root,'.'+pathname+(pathname.endsWith('/')?'index.html':'')),target=await realpath(file).catch(()=>null);
      if(!target||!target.startsWith(root+sep)){res.writeHead(404,{'Content-Type':'text/html; charset=utf-8'});res.end(req.method==='HEAD'?undefined:await readFile(join(root,'404.html')));return;}
      const bytes=await readFile(target);
      res.setHeader('Content-Type',({'.html':'text/html; charset=utf-8','.mjs':'text/javascript','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.webp':'image/webp','.wasm':'application/wasm'}[extname(target)]||'application/octet-stream'));
      res.end(req.method==='HEAD'?undefined:bytes);
    } catch(error) {res.writeHead(error.status||503,{'Content-Type':'application/json'});res.end(JSON.stringify({code:error.code||'local_service_unavailable'}));}
  });
  web.headersTimeout=10000;web.requestTimeout=20000;
  try{web.listen(port,'127.0.0.1');await once(web,'listening');}catch(error){social.close();db.close();throw error;}
  return {origin,close:async()=>{await new Promise(done=>web.close(done));await new Promise(done=>social.close(done));db.close();}};
}
if(process.argv[1]===fileURLToPath(import.meta.url)) {
  const [release,data,port,...adminWallets]=process.argv.slice(2);
  if(!release||!data)throw new Error('Usage: node tools/serve_results_catalog.mjs RELEASE PRIVATE_DATA_DIR [PORT] [ADMIN_PUBLIC_KEYS...]');
  const service=await serveResultsCatalog({release,data,port:port?Number(port):8099,adminWallets});
  console.log(JSON.stringify({origin:service.origin,localDevelopment:true,persistentApplications:true,administratorCount:adminWallets.length,financialHandlers:false}));
  for(const signal of ['SIGINT','SIGTERM'])process.once(signal,()=>service.close().then(()=>process.exit()));
}
