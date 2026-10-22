"""Repair sub-10-second sunlit fragments omitted by conservative D ambiguity handling.

Reads the completed August D cache and C source, scans only C-minus-D gaps up to
10 seconds, then uses a 1 ms grid to detect sunlight and Brent roots (1 us
`tolerance`) to locate boundaries. Writes a separate refined cache; never
modifies the source D cache. This is a bounded local repair, not a continuous-
time proof; the 1 ms discovery grid is recorded in the manifest.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,tempfile,sys,time
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
import numpy as np
from skyfield.api import load,EarthSatellite
import illumination_filter_aug2026 as dgen
csv.field_size_limit(sys.maxsize)
ROOT=Path(__file__).resolve().parent
START=datetime(2026,8,1,tzinfo=timezone.utc)

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def atomic_json(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def atomic_csv(p,fields,write):
 p.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w',encoding='utf-8',newline='') as f:
   w=csv.DictWriter(f,fieldnames=fields);w.writeheader();write(w);f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def positive_grid_runs(values):
    """Return inclusive index runs where sampled clearance is nonnegative."""
    ix=np.flatnonzero(np.asarray(values,dtype=float)>=0.0)
    if not len(ix):return []
    runs=[];first=previous=int(ix[0])
    for value in ix[1:]:
        value=int(value)
        if value!=previous+1:runs.append((first,previous));first=value
        previous=value
    runs.append((first,previous))
    return runs

def dt(sec):return START+timedelta(seconds=float(sec))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--c',default='m1_validation/formal_20260801_candidate/C_optical/windows.csv');ap.add_argument('--d',default='m1_validation/formal_20260801_candidate/D_illumination/windows.csv');ap.add_argument('--out',default='m1_validation/formal_20260801_candidate/D_illumination_refined');ap.add_argument('--tle',default='data/轨道.txt');ap.add_argument('--ephemeris',default='data/ephemeris/de421.bsp');ap.add_argument('--max-gap-seconds',type=float,default=10.0);ap.add_argument('--coarse-gap-samples',type=int,default=5);ap.add_argument('--fine-grid-step-seconds',type=float,default=.001);ap.add_argument('--root-tolerance-seconds',type=float,default=1e-6);args=ap.parse_args()
 cpath,dpath,tlepath,ephpath=[ROOT/x for x in (args.c,args.d,args.tle,args.ephemeris)];out=ROOT/args.out
 if (out/'manifest.json').exists() or out.exists():raise SystemExit(f'refusing to overwrite existing refined D output: {out}')
 ts=load.timescale(builtin=True);planets=load(str(ephpath));earth,sun=planets['earth'],planets['sun'];tles=dgen.load_tles(tlepath);satcache={}
 def sat_for(tid):
  if tid not in satcache:
   n,l1,l2=tles[tid];satcache[tid]=EarthSatellite(l1,l2,n,ts)
  return satcache[tid]
 def clearance_many(tid,secs):
  times=ts.from_datetimes([dt(x) for x in secs]);sat=sat_for(tid)
  r=np.asarray(sat.at(times).position.km,dtype=float).T;s=np.asarray(earth.at(times).observe(sun).position.km,dtype=float).T
  dist=np.linalg.norm(s,axis=1);u=s/dist[:,None];ax=np.einsum('ij,ij->i',r,u);perp=np.linalg.norm(r-ax[:,None]*u,axis=1);radius=np.linalg.norm(r,axis=1)
  return np.where(ax>=0,radius-dgen.EARTH_RADIUS_KM,perp-(dgen.EARTH_RADIUS_KM+ax*(dgen.SUN_RADIUS_KM-dgen.EARTH_RADIUS_KM)/dist))
 run_started=time.perf_counter()
 # Stream C and D and collect only short uncovered gaps.
 gaps=defaultdict(list);dfile=dpath.open(encoding='utf-8',newline='');dit=iter(csv.DictReader(dfile));dr=next(dit,None);source_rows=0;drows=0
 with cpath.open(encoding='utf-8',newline='') as cf:
  for line,c in enumerate(csv.DictReader(cf),2):
   source_rows+=1;tid=c['target_id'];cur=float(c['start_s']);end=float(c['end_s']);parts=[]
   while dr is not None and int(dr['source_C_line'])==line:
    a=float(dr['start_s']);b=float(dr['end_s']);parts.append((a,b));drows+=1
    if a-cur>1e-9 and a-cur<=args.max_gap_seconds:gaps[tid].append({'line':line,'target_id':tid,'station_id':c['station_id'],'a':cur,'b':a})
    cur=max(cur,b);dr=next(dit,None)
   if end-cur>1e-9 and end-cur<=args.max_gap_seconds:gaps[tid].append({'line':line,'target_id':tid,'station_id':c['station_id'],'a':cur,'b':end})
 if dr is not None:raise RuntimeError('D rows are not ordered by source C line')
 dfile.close()
 dgen.ROOT_TOL_S=args.root_tolerance_seconds
 repaired=defaultdict(list);log=[];coarse_evals=fine_evals=0;checked_gaps=0
 for tid,gs in gaps.items():
  sample_secs=[];offsets=[]
  for g in gs:
   qs=np.linspace(g['a'],g['b'],args.coarse_gap_samples);offsets.append((g,len(sample_secs),len(qs)));sample_secs.extend(qs.tolist())
  coarse=clearance_many(tid,sample_secs);coarse_evals+=len(coarse);candidate=[]
  for g,i,n in offsets:
   checked_gaps+=1;candidate.append(g)
  for g in candidate:
   n=max(2,int(np.ceil((g['b']-g['a'])/args.fine_grid_step_seconds))+1);q=np.linspace(g['a'],g['b'],n);v=clearance_many(tid,q.tolist());fine_evals+=n
   # Positive runs on the fine grid; crossings are independently refined by Brent.
   runs=positive_grid_runs(v)
   if not runs:continue
   roots=[]
   for i,j in runs:
    a=float(q[i]) if i==0 else dgen._root(sat_for(tid),earth,sun,ts,float(q[i-1]),float(q[i]))
    b=float(q[j]) if j==n-1 else dgen._root(sat_for(tid),earth,sun,ts,float(q[j]),float(q[j+1]))
    if b>a:repaired[g['line']].append((a,b));roots.append((a,b))
   if roots:log.append({'source_C_line':g['line'],'target_id':tid,'station_id':g['station_id'],'gap_start_s':g['a'],'gap_end_s':g['b'],'gap_duration_s':g['b']-g['a'],'coarse_min_clearance_km':None,'repaired_intervals':json.dumps(roots),'action':'restore_grid-confirmed_sunlit_fragment'})
 # Re-stream and merge existing D intervals with repaired pieces, source row by source row.
 dfile=dpath.open(encoding='utf-8',newline='');dit=iter(csv.DictReader(dfile));dr=next(dit,None);dfields=None;outrows=0;duration120=0;overlaps=0;prev={}
 out.mkdir(parents=True,exist_ok=False);dest=out/'windows.csv'
 def write_rows(w):
  nonlocal outrows,duration120,overlaps,dfields,dr
  with cpath.open(encoding='utf-8',newline='') as cf:
   for line,c in enumerate(csv.DictReader(cf),2):
    existing=[];template=None
    while dr is not None and int(dr['source_C_line'])==line:
     row=dict(dr);template=template or row;existing.append((float(row['start_s']),float(row['end_s'])));dr=next(dit,None)
    intervals=existing+repaired.get(line,[]);merged=[]
    for a,b in sorted(intervals):
     if b<=a:continue
     if merged and a<=merged[-1][1]+2*args.root_tolerance_seconds:merged[-1]=(merged[-1][0],max(merged[-1][1],b))
     else:merged.append((a,b))
    for a,b in merged:
     row=dict(template or c);row.update(c);row.update(start_s=a,end_s=b,duration_s=b-a,meets_120s=(b-a)>=120,source_C_line=line,c_start_s=c['start_s'],c_end_s=c['end_s'],illumination_status='sunlit',illumination_model='finite_sun_conical_umbra',illumination_boundary_method='adaptive_clearance_brent_gap_refinement')
     if dfields is None:dfields=list(row)
     w.writerow(row);outrows+=1;duration120+=(b-a)>=120
 if dfields is None:
  with cpath.open(encoding='utf-8',newline='') as f:cfields=next(csv.reader(f))
  dfields=cfields+['source_C_line','c_start_s','c_end_s','illumination_status','illumination_model','illumination_boundary_method']
 atomic_csv(dest,dfields,write_rows);dfile.close()
 logpath=out/'repair_log.csv';logfields=['source_C_line','target_id','station_id','gap_start_s','gap_end_s','gap_duration_s','coarse_min_clearance_km','repaired_intervals','action'];atomic_csv(logpath,logfields,lambda w:[w.writerow(x) for x in log])
 src_manifest=json.loads((dpath.parent/'manifest.json').read_text())
 manifest={'schema_version':'m1-illumination-gap-refinement-aug2026-2.0','layer':'D_illumination_refined','planning':src_manifest['planning'],'source_C_sha256':sha(cpath),'source_D_sha256':sha(dpath),'source_D_manifest_sha256':sha(dpath.parent/'manifest.json'),'tle_sha256':sha(tlepath),'ephemeris_sha256':sha(ephpath),'algorithm':{'gap_scan_max_seconds':args.max_gap_seconds,'coarse_samples_per_gap':args.coarse_gap_samples,'fine_grid_step_seconds':args.fine_grid_step_seconds,'root_tolerance_seconds':args.root_tolerance_seconds,'clearance_lipschitz_km_s':dgen.SUNLIGHT_CLEARANCE_LIPSCHITZ_KM_S,'undetected_subgrid_events':'not excluded by a mathematical proof; reported sampling limitation'},'source_C_rows':source_rows,'source_D_rows':drows,'checked_short_gaps':checked_gaps,'coarse_time_evaluations':coarse_evals,'fine_time_evaluations':fine_evals,'restored_gap_count':len(log),'restored_interval_count':sum(len(x) for x in repaired.values()),'rows':outrows,'windows_ge_120s':duration120,'elapsed_seconds':time.perf_counter()-run_started,'windows_sha256':sha(dest),'repair_log_sha256':sha(logpath)}
 atomic_json(out/'manifest.json',manifest);print(json.dumps(manifest,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
