#!/usr/bin/env python3
"""One-time import of reviewed sources into repositories with unique ownership.

Does not copy Git history, ignored runtime data, credentials, model caches or
generated bundles. The output is source code, not a production deployment.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path

REPOSITORIES = ('web','node','miner','explorer','protocol','contracts','sdk','infra','research','docs')
MINER_MODULES = set('anatomy-assets anatomy-renderer anatomy-scene archive-upload archive-zip artifact-export artifact-export-worker browser-abort browser-shims candidate-store-v2 chunk-store computation compute-pool contribution-view difficulty-family fly-scene goal-mining-view goal-search-runner goal-status-text goal-ui-state input-order live-observation live-observation-view metric-format miner-state mining-anatomy mining-anatomy-index mining-deployment mining-workflow mining model-storage neural-ribbon observation-focus official-builder official-source pending-output preparation-controller preparation-progress propagation-routes propagation-trace propagation-view replay-controller research-app research-profiles research-tools research-worker response-store response-view ribbon-path session-plan submission-controller submission-store task-eligibility task-runner work-meter'.split())
SDK_MODULES = set('campaign-codec candidate-submission-v2 catalog-task evidence-manifest receipt-v1 response-record service-outbox solana-client target-protocol-v2 target-response-record target-round-client wallet-core'.split())
PROTOCOL_SRC = set('block compact_index dataset economics evidence_manifest flyhash hash network pow useful'.split())
RESEARCH_TOOLS = set('activate_research_profiles build_comparable_family_v3 build_product_goals build_public_result calibrate_live_goals_v3 calibrate_product_goals calibrate_target_v2 evaluate_model fetch_official_ranges generate_research_profiles inspect_connectome_weights model_evaluation_schema prepare_atlas prepare_atlas_context prepare_brain_view prepare_dataset prepare_graph prepare_mining_anatomy prepare_model_v0 prepare_official prepare_propagation_routes prepare_registry publish_model_evaluation reference_sim reference_target_v2 requirements-research'.split())
WEB_TOOLS = set('build_browser build_mining_release build_product_pages build_product_release build_live_current_release check_public_site csp_policy english_templates export_static optimize_images requirements-images validate_static_release'.split())
SDK_TOOLS = set('campaign_tools economy_v2_client target_dev_identity'.split())
CONTRACT_TOOLS = set('agave-localnet-sync-io deploy_localnet migrate_economic_stage_v3 setup_campaign start_localnet'.split())

def owner(name:str)->str:
    p=Path(name);parts=p.parts;stem=p.stem
    if parts[0]=='docs':return 'docs'
    if name in ('Cargo.toml','Cargo.lock') or parts[0]=='config' and not stem.startswith('explorer'):return 'node'
    if parts[0]=='config':return 'explorer'
    if name in ('package.json','package-lock.json'):return 'web'
    if parts[0]=='crates':return 'miner' if parts[1]=='sim-core' else 'protocol'
    if parts[0]=='programs':return 'contracts'
    if parts[0]=='src':
        if stem.startswith('explorer') or stem.startswith('flypow_explorer'):return 'explorer'
        if stem in PROTOCOL_SRC:return 'protocol'
        if name=='src/main.rs':return 'miner'
        if stem in ('site','flypow-web'):return 'web'
        return 'node'
    if parts[0]=='web':
        if len(parts)>1 and parts[1]=='data':
            if stem=='market-catalog-v1':return 'node'
            if stem in ('chain-config','economic-policy-v2'):return 'protocol'
            if stem in ('mining-deployment-v1','target-network-v2','product-manifest-v1'):return 'web'
            return 'research'
        if stem.startswith('explorer') or stem=='block':return 'explorer'
        if stem in ('mining','legacy-mining') or stem in MINER_MODULES or parts[1]=='vendor':return 'miner'
        if stem in SDK_MODULES:return 'sdk'
        return 'web'
    if parts[0]=='deploy':return 'web' if parts[1]=='public' else 'infra'
    if parts[0]=='tools':
        if stem in RESEARCH_TOOLS:return 'research'
        if stem in WEB_TOOLS:return 'web'
        if stem in SDK_TOOLS:return 'sdk'
        if stem in CONTRACT_TOOLS:return 'contracts'
        if 'explorer' in stem or stem=='rebuild_index':return 'explorer'
        if stem.startswith(('deploy','upgrade','check_product_node')):return 'infra'
        if stem in ('build_research_app','build_portable_validator'):return 'miner'
        if stem=='target_protocol_v2':return 'protocol'
        return 'node'
    if parts[0]=='tests':
        if stem in ('browser_cache','test_deploy_release','check_product_restart'):return 'infra'
        if 'explorer' in stem:return 'explorer'
        if stem in ('target_protocol_v2','receipt_v1','catalog_task','comparable_family_v3','evidence_manifest') or parts[1]=='vectors' or stem=='submission-v1':return 'protocol'
        if stem in ('campaign_localnet','economy_v2_localnet'):return 'contracts'
        if stem in ('settlement_transport.test','service_outbox','economic_ingest_transport','wallet_crypto'):return 'sdk'
        if any(t in stem for t in ('model_evaluation','connectome_coverage','prepare_dataset','optimization_reference','equivalence')):return 'research'
        if any(t in stem for t in ('atlas','static_export','brand','image_optimization','site_upgrade','e2e_product')):return 'web'
        if stem in ('product_api','target_authority','target_api_v2','target_competition_v2','public_product_api','public_target_competition_v2','product_cloud_pipeline'):return 'node'
        return 'miner'
    raise ValueError('Unclassified source: '+name)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--repos',type=Path,required=True);a=p.parse_args()
    source=a.source.resolve();repos=a.repos.resolve();names=subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0')
    names=set(filter(None,names))
    for rel in ['config/market-v1.sql','src/market','crates/service-core','tests/market_catalog.rs','web/data/market-catalog-v1.json','docs/PROTOCOL_EN.md','docs/history/v1/PROTOCOL_EN.md']:
        q=source/rel
        names.update(str(f.relative_to(source)) for f in q.rglob('*') if f.is_file()) if q.is_dir() else names.add(rel)
    skipped=[];mapped={};files=[]
    for name in sorted(names):
        q=source/name
        if not q.is_file():continue
        # New maintained documentation is English. Original historical text and
        # screenshots remain untouched in the retained source directory.
        if name in ('AGENTS.md','README.md','.gitignore') or name.startswith('deploy/keys/') or ('docs/' in name and (q.suffix!='.md' or q.name.endswith('_ZH.md') or '_ZH' in q.name or q.name=='GOAL_MINING_V2_WORK_LOG.md')):
            skipped.append(name);continue
        if q.suffix=='.md' and any('\u3400'<=c<='\u9fff' for c in q.read_text()):skipped.append(name);continue
        o=owner(name);dest=repos/o/name
        if dest.exists():raise ValueError('Refusing to overwrite '+str(dest))
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(q,dest)
        mapped.setdefault(o,{})[name]=name
        files.append({'workspacePath':name,'repository':o,'repositoryPath':name,'sha256':hashlib.sha256(q.read_bytes()).hexdigest()})
    for repo in REPOSITORIES:
        r=repos/repo;r.mkdir(parents=True,exist_ok=True)
        (r/'component.json').write_text(json.dumps({'schema':'flybrain-component-v1','repository':repo,'owner':'flybrainlabs','workspaceFiles':mapped.get(repo,{})},indent=2)+'\n')
    report={'schema':'flybrain-source-import-v1','baselineCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=source).decode().strip(),'baselineTree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=source).decode().strip(),'files':files,'retainedOutsideNewRepositories':skipped,'productionDeploymentChanged':False}
    (repos/'infra'/'import-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'mappedFiles':len(files),'repositories':{r:len(mapped.get(r,{})) for r in REPOSITORIES},'retainedHistoricalFiles':len(skipped)}))
if __name__=='__main__':main()
