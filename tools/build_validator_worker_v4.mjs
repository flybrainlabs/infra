#!/usr/bin/env node
// Package the worker and read-only relay without runtime secrets or model data.
import {parseArgs} from 'node:util';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir,stat} from 'node:fs/promises';
import {dirname,join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
const {values}=parseArgs({options:{workspace:{type:'string'},output:{type:'string'}}});
if(!values.workspace||!values.output)throw new Error('Usage: --workspace ASSEMBLY --output NEW_WORKER.mjs');
const workspace=resolve(values.workspace),output=resolve(values.output);
for(const path of [output,output+'.manifest.json']){try{await stat(path);throw new Error('Retained package already exists');}catch(error){if(error.code!=='ENOENT')throw error;}}
const require=createRequire(join(workspace,'package.json')),{build}=require('esbuild');
await mkdir(dirname(output),{recursive:true});
// Imported CLI guards must stay inactive after modules share one bundle URL.
await build({absWorkingDir:workspace,preserveSymlinks:true,stdin:{contents:"import {runValidatorWorkerV4} from './tools/factory_validator_worker_v4.mjs'; runValidatorWorkerV4().catch(()=>{console.error(JSON.stringify({code:'VALIDATOR_STARTUP_FAILED'}));process.exitCode=1;});",resolveDir:workspace,sourcefile:'validator-entry.mjs'},outfile:output,bundle:true,platform:'node',target:'node22',format:'esm',define:{'import.meta.url':JSON.stringify('file:///__flybrain_bundled_library__.mjs')},banner:{js:"import {createRequire as _createRequire} from 'node:module';const require=_createRequire(import.meta.url);"}});
const bytes=await readFile(output),manifest={schema:'flybrain-validator-worker-package-v1',nodeTarget:'node22',sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,entrypoint:'tools/factory_validator_worker_v4.mjs',privateConfigurationIncluded:false,privateKeysIncluded:false,modelFilesIncluded:false,activation:false};
await writeFile(output+'.manifest.json',JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(manifest));
