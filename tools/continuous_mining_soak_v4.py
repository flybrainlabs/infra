#!/usr/bin/env python3
"""Bounded health/resource observer; never starts mining or signs transactions."""
import argparse,json,signal,time,urllib.parse,urllib.request
from pathlib import Path

def main(a):
    u=urllib.parse.urlsplit(a.health)
    if u.scheme not in ('http','https') or not u.netloc or u.username or u.password or u.query or u.fragment or not u.path.endswith('/health'):raise ValueError('Use a health endpoint without credentials or query parameters')
    if not 24<=a.hours<=72 or not 5<=a.interval<=60:raise ValueError('Use 24–72 hours and a 5–60 second interval')
    if a.smoke_seconds is not None and not 1<=a.smoke_seconds<=300:raise ValueError('Smoke duration is 1–300 seconds')
    a.output.mkdir(parents=True,exist_ok=True);log=a.output/'samples.jsonl';summary=a.output/'summary.json'
    if log.exists() or summary.exists():raise ValueError('Use a fresh report directory; previous evidence is retained')
    stopped=False
    def stop(*_):
        nonlocal stopped
        stopped=True
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,stop)
    start=time.monotonic();duration=a.smoke_seconds if a.smoke_seconds is not None else a.hours*3600;count=failures=0;status='running'
    try:
        with log.open('x') as file:
            while not stopped and time.monotonic()-start<duration:
                if a.stop_file and a.stop_file.exists():status='stop-file';break
                row={'at':time.time(),'elapsedSeconds':time.monotonic()-start}
                try:
                    request=urllib.request.Request(a.health,headers={'Cache-Control':'no-cache'})
                    with urllib.request.urlopen(request,timeout=15) as response:data=json.load(response)
                    row['health']={k:data.get(k) for k in ('schema','businessReady','lastDiscoveryAt','discoveryAgeMs','lastDiscoveryError','lastWorkerError','lastMaintenanceError','inventory','queues','replayLatency','storage','verifier')};row['httpReady']=True
                    if not data.get('businessReady'):failures+=1
                except Exception as error:row['httpReady']=False;row['errorClass']=type(error).__name__;failures+=1
                if a.node_pid:
                    try:
                        values={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in Path('/proc',str(a.node_pid),'status').read_text().splitlines() if ':' in line};row['process']={k:values.get(k) for k in ('VmRSS','VmHWM','VmSize','Threads')}
                    except OSError:row['process']={'available':False}
                file.write(json.dumps(row,separators=(',',':'))+'\n');file.flush();count+=1
                deadline=min(start+duration,time.monotonic()+a.interval)
                while not stopped and time.monotonic()<deadline:time.sleep(min(1,deadline-time.monotonic()))
        if status=='running':status='stopped' if stopped else 'duration-observed'
    finally:
        result={'schema':'flybrainlabs-continuous-mining-observation-v4','readOnly':True,'plannedSeconds':duration,'observedSeconds':time.monotonic()-start,'samples':count,'unreadyOrFailedSamples':failures,'status':status,'smokeOnly':a.smoke_seconds is not None,'miningOrFinancialActions':0,'limitation':'Health and process observations alone do not prove complete-model candidates, browser continuity or rewards.'};summary.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--health',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--hours',type=float,default=24);p.add_argument('--interval',type=int,default=30);p.add_argument('--stop-file',type=Path);p.add_argument('--node-pid',type=int);p.add_argument('--smoke-seconds',type=int);main(p.parse_args())
