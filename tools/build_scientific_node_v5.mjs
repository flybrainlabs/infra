// Create a self-contained review/maintenance package. No private configuration,
// keys, database, model, installation or service activation is included.
import {build} from 'esbuild';
import {parseArgs} from 'node:util';
import {mkdir,readFile,writeFile,copyFile,chmod,stat} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const {values}=parseArgs({options:{workspace:{type:'string'},output:{type:'string'},native:{type:'string'},sbf:{type:'string'}}});
for(const field of ['workspace','output','native','sbf'])if(!values[field])throw new Error('Missing --'+field);
const workspace=resolve(values.workspace),output=resolve(values.output),assembly=JSON.parse(await readFile(join(workspace,'.flybrain-workspace.json'),'utf8')),owner=join(assembly.repositories,'node');await mkdir(output,{recursive:false});for(const dir of ['tools','config','bin','sbf'])await mkdir(join(output,dir));
await build({entryPoints:[join(workspace,'tools/scientific_service_v5.mjs')],outfile:join(output,'tools/scientific_service_v5.mjs'),bundle:true,platform:'node',target:'node22',format:'esm',legalComments:'eof',banner:{js:"import { createRequire as scientificCreateRequire } from 'node:module'; import { fileURLToPath as scientificFilePath } from 'node:url'; import { dirname as scientificDirectory } from 'node:path'; const __filename = scientificFilePath(import.meta.url); const __dirname = scientificDirectory(__filename); const require = scientificCreateRequire(import.meta.url);"}});
const files=[['config/factory-pool-v4.sql',join(workspace,'config/factory-pool-v4.sql')],['bin/exact_trial',resolve(values.native)],['sbf/flypow_economy_v2_program.so',resolve(values.sbf)],['LICENSE-MIT',join(owner,'LICENSE-MIT')],['LICENSE-APACHE',join(owner,'LICENSE-APACHE')],['NOTICE',join(owner,'NOTICE')],['OPERATIONS.md',join(workspace,'docs/SCIENTIFIC_MINING_V5_OPERATIONS.md')]];
for(const [dest,source]of files)await copyFile(source,join(output,dest));await chmod(join(output,'bin/exact_trial'),0o755);
const capabilities=JSON.parse(execFileSync(join(output,'bin/exact_trial'),['--capabilities'],{encoding:'utf8'}));if(capabilities.completeModel!==true||!capabilities.methods.includes('exact-events-v1'))throw new Error('Native capabilities');
await writeFile(join(output,'package.json'),JSON.stringify({private:true,type:'module'})+'\n');
const hashes={};for(const name of ['tools/scientific_service_v5.mjs',...files.map(([name])=>name),'package.json']){const bytes=await readFile(join(output,name));hashes[name]={sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length};}
const sourceRevisions={};for(const name of ['contracts','infra','miner','node','protocol','sdk'])sourceRevisions[name]=execFileSync('git',['rev-parse','HEAD'],{cwd:join(assembly.repositories,name),encoding:'utf8'}).trim();
const manifest={schema:'flybrain-scientific-node-package-v5',createdAt:new Date().toISOString(),activation:false,privateConfigurationIncluded:false,privateKeysIncluded:false,modelIncluded:false,databaseIncluded:false,mainnet:false,sourceRevisions,files:hashes,capabilities};await writeFile(join(output,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');console.log(JSON.stringify({output,files:Object.keys(hashes).length,activation:false,privateMaterialIncluded:false}));
