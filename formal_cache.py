"""Formal six-day M1 cache pipeline.

Layers are independent and atomically committed:
  A orbit/elevation visibility, B station astronomical night, C their intersection.
Each layer carries an input/config fingerprint so priority changes only rebuild C.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, tempfile, time, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from dataclasses import asdict
import numpy as np
from skyfield.api import load, EarthSatellite, wgs84
from m1 import load_tle, load_stations
from visibility import Geometry, OrbitEvaluator, NumericPolicy, refine_windows_optimized

VERSION = "formal-m1-cache-2.1"

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()

def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.tmp-', dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f: json.dump(value,f,ensure_ascii=False,indent=2)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def atomic_csv(path: Path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True);fd,tmp=tempfile.mkstemp(prefix='.tmp-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def parse_priority(path: Path):
    if path.suffix.lower()=='.zip':
        z=zipfile.ZipFile(path);names=z.namelist();data=[(n,z.read(n).decode('utf-8')) for n in names]
    else:data=[(path.name,path.read_text(encoding='utf-8'))]
    out={};mapping={'高':'high','中':'medium','低':'low'}
    for name,text in data:
        level=next((v for k,v in mapping.items() if k in name),None)
        if not level:continue
        for token in text.replace('\n',',').split(','):
            token=token.strip()
            if token:out[token]=level
    return out

def manifest(layer, args, inputs, extra=None):
    d={'schema_version':VERSION,'layer':layer,'inputs':{str(p):sha256(Path(p)) for p in inputs},'time':{'start_utc':args.start,'end_utc':args.end,'time_scale':args.time_scale},'algorithm':{'coarse_step_s':args.step,'min_elevation_deg':10,'max_elevation_deg':85,'night_sun_altitude_deg':-6,'root_time_tol_s':1e-6,'minimum_observation_s':120,'maximum_observation_s':240},'source_version':VERSION}
    if extra:d.update(extra)
    d['fingerprint']=hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False).encode()).hexdigest();return d

def cache_ok(directory: Path, expected):
    p=directory/'manifest.json'
    if not p.exists():return False
    try:
        actual=json.loads(p.read_text(encoding='utf-8'))
        return actual.get('fingerprint')==expected['fingerprint'] and (directory/'windows.csv').is_file() and all((directory/name).is_file() for name in actual.get('required_artifacts',[]))
    except Exception:return False

def times(args):
    if args.time_scale != 'UTC': raise ValueError('Only UTC is implemented; do not relabel other scales')
    if args.step<=0: raise ValueError('step must be positive')
    start=datetime.fromisoformat(args.start.replace('Z','+00:00')).astimezone(timezone.utc);end=datetime.fromisoformat(args.end.replace('Z','+00:00')).astimezone(timezone.utc)
    if end<=start:raise ValueError('end must be after start')
    return start,end,np.r_[np.arange(0,(end-start).total_seconds(),args.step),(end-start).total_seconds()]

def layer_a(args, root, rec, stations, ts, start, seconds, force=False):
    policy=NumericPolicy(coarse_step_s=args.step,discovery_step_s=min(15,args.step))
    d=root/'A_orbit';m=manifest('A_orbit',args,[args.tle,args.stations],{'target_count':args.targets,'station_count':len(stations),'numeric_policy':asdict(policy),'visibility_source_sha256':sha256(Path(__file__).with_name('visibility.py')),'required_artifacts':['target_status.json']})
    if cache_ok(d,m) and not force:return 'hit',m
    rows=[];statuses=[];geometry=Geometry(ts,start,stations);grid=seconds;prepared=geometry.prepare(grid);p=NumericPolicy(coarse_step_s=args.step,discovery_step_s=min(15,args.step))
    for idx,r in enumerate(rec[:args.targets]):
        ev=None
        try:
            ev=OrbitEvaluator(r,geometry);e=ev.grid(grid,prepared)
            windows,anomalies=refine_windows_optimized(ev,grid,e,p)
            status=('full_propagation_failure' if ev.error_samples and ev.error_samples==ev.evaluations else
                    'partial_propagation_failure' if ev.error_samples else
                    'refinement_failure' if anomalies else 'has_windows' if windows else 'normal_no_window_sampled')
        except (ValueError,RuntimeError,FloatingPointError) as exc:
            windows=[];anomalies=[dict(reason='target_computation_exception',exception_type=type(exc).__name__,message=str(exc))]
            status='computation_exception'
        statuses.append(dict(target_id=r[1][2:7],target_index=idx,status=status,window_count=len(windows),
            propagation_samples=ev.evaluations if ev else 0,propagation_error_samples=ev.error_samples if ev else 0,
            error_codes=ev.error_codes if ev else {},error_intervals=ev.error_intervals if ev else [],anomalies=anomalies))
        for w in windows:
            rows.append({'target_id':r[1][2:7],'target_index':idx,'station_id':stations[w['site']]['id'],'start_s':w['start_s'],'end_s':w['end_s'],'duration_s':w['end_s']-w['start_s'],'refinement_status':w['refinement_status'],'start_kind':w['start_kind'],'end_kind':w['end_kind'],'discovery_status':w['discovery_status']})
    atomic_json(d/'target_status.json',statuses)
    atomic_csv(d/'windows.csv',rows,list(rows[0]) if rows else ['target_id','target_index','station_id','start_s','end_s','duration_s','refinement_status']);atomic_json(d/'manifest.json',m);return 'miss',m

def layer_b(args, root, stations, ts, start, seconds, force=False):
    d=root/'B_night';m=manifest('B_night',args,[args.stations,args.ephemeris])
    if cache_ok(d,m) and not force:return 'hit',m
    planets=load(args.ephemeris);sun=planets['sun'];earth=planets['earth'];rows=[];t=ts.from_datetimes([start+timedelta(seconds=float(x)) for x in seconds])
    for st,site in zip(stations,[wgs84.latlon(s['lat'],s['lon'],elevation_m=s['elevation_m']) for s in stations]):
        alt=(earth+site).at(t).observe(sun).apparent().altaz()[0].degrees;mask=alt<-6
        for i in np.flatnonzero(mask & ~np.r_[False,mask[:-1]]):
            j=i
            while j+1<len(mask) and mask[j+1]:j+=1
            rows.append({'station_id':st['id'],'start_s':float(seconds[i]),'end_s':float(seconds[min(j+1,len(seconds)-1)]),'duration_s':float(seconds[min(j+1,len(seconds)-1)]-seconds[i])})
    atomic_csv(d/'windows.csv',rows,['station_id','start_s','end_s','duration_s']);atomic_json(d/'manifest.json',m);return 'miss',m

def layer_c(args, root, inputs, priority, force=False):
    dependencies={}
    for name in ['A_orbit','B_night']:
        folder=root/name; meta=json.loads((folder/'manifest.json').read_text())
        dependencies[name]=dict(manifest_sha256=sha256(folder/'manifest.json'),windows_sha256=sha256(folder/'windows.csv'),source_version=meta.get('source_version'),algorithm=meta.get('algorithm'))
    d=root/'C_optical';m=manifest('C_optical',args,inputs+[args.priority],{'dependencies':dependencies,'priority_sha256':hashlib.sha256(json.dumps(priority,sort_keys=True).encode()).hexdigest()})
    if cache_ok(d,m) and not force:return 'hit',m
    with (root/'A_orbit/windows.csv').open(encoding='utf-8') as f: a=list(csv.DictReader(f))
    with (root/'B_night/windows.csv').open(encoding='utf-8') as f: n=list(csv.DictReader(f))
    by={int(x['station_id']):[] for x in n}
    for x in n:by.setdefault(int(x['station_id']),[]).append(x)
    rows=[]
    for x in a:
        for y in by.get(int(x['station_id']),[]):
            lo=max(float(x['start_s']),float(y['start_s']));hi=min(float(x['end_s']),float(y['end_s']))
            if hi>lo:
                dur=hi-lo;tid=x['target_id'];rows.append({'target_id':tid,'station_id':x['station_id'],'start_s':lo,'end_s':hi,'duration_s':dur,'priority':priority.get(tid,'unassigned'),'meets_120s':dur>=120,'validation_status':'generated_intersection'})
    atomic_csv(d/'windows.csv',rows,list(rows[0]) if rows else ['target_id','station_id','start_s','end_s','duration_s','priority','meets_120s','validation_status']);atomic_json(d/'manifest.json',m);return 'miss',m

def main():
    p=argparse.ArgumentParser();p.add_argument('--tle',default='data/轨道.txt');p.add_argument('--stations',default='data/站址.txt');p.add_argument('--priority',required=True);p.add_argument('--ephemeris',default='data/ephemeris/de421.bsp');p.add_argument('--out',required=True);p.add_argument('--targets',type=int,default=100);p.add_argument('--start',default='2026-10-01T00:00:00Z');p.add_argument('--end',default='2026-10-07T00:00:00Z');p.add_argument('--time-scale',default='UTC');p.add_argument('--step',type=int,default=60);p.add_argument('--force',action='store_true');a=p.parse_args()
    root=Path(a.out);start,end,seconds=times(a);ts=load.timescale(builtin=True);rec,parse_errors=load_tle(a.tle);stations=load_stations(a.stations);priority=parse_priority(Path(a.priority));root.mkdir(parents=True,exist_ok=True)
    if parse_errors: raise ValueError(f'TLE format errors at groups {parse_errors}')
    if a.targets>len(rec) or a.targets<=0: raise ValueError('invalid target count')
    result={'cache_version':VERSION,'layers':{},'priority_counts':{k:list(priority.values()).count(k) for k in ['high','medium','low','unassigned']},'started_utc':datetime.now(timezone.utc).isoformat()}
    for name,fn in [('A',lambda:layer_a(a,root,rec,stations,ts,start,seconds,a.force)),('B',lambda:layer_b(a,root,stations,ts,start,seconds,a.force))]:
        status,m=fn();result['layers'][name]={'status':status,'fingerprint':m['fingerprint']}
    status,m=layer_c(a,root,[a.tle,a.stations],priority,a.force);result['layers']['C']={'status':status,'fingerprint':m['fingerprint']};atomic_json(root/'run_summary.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
