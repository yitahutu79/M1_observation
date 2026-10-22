"""Shape-safe adaptive satellite-illumination D layer for the Aug-2026 M1 cache.

The input is the newly generated C layer. Shadow clearance is signed positive in
sunlight and negative in the finite-Sun conical umbra. A conservative Lipschitz
bound triggers adaptive subdivision near possible shadow crossings; roots are
refined with Brent. Ambiguous sub-0.25 s leaves are excluded and counted.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,tempfile,time,sys

csv.field_size_limit(sys.maxsize)
from datetime import datetime,timedelta,timezone
from itertools import groupby, islice
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
from skyfield.api import load,EarthSatellite

ROOT=Path(__file__).resolve().parent
START=datetime(2026,8,1,tzinfo=timezone.utc)
END=datetime(2026,8,7,tzinfo=timezone.utc)
HORIZON=(END-START).total_seconds()
EARTH_RADIUS_KM=6378.137
SUN_RADIUS_KM=695700.0
SUNLIGHT_CLEARANCE_LIPSCHITZ_KM_S=30.0
DISCOVERY_STEP_S=60.0
MIN_AMBIGUOUS_STEP_S=0.25
MIN_CERTIFICATION_STEP_S=1e-3
ROOT_TOL_S=1e-3

def sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def atomic_json(path,value):
 path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:
   json.dump(value,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

def atomic_csv(path,fields,write_rows):
 path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w',encoding='utf-8',newline='') as f:
   writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();write_rows(writer);f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

def _rows_xyz(x,n):
 a=np.asarray(x,dtype=float)
 if a.ndim==1:
  if a.shape[0]!=3:raise ValueError(f'expected xyz vector, got {a.shape}')
  return a.reshape(1,3)
 if a.ndim!=2:raise ValueError(f'expected 1D or 2D xyz positions, got {a.shape}')
 if a.shape==(3,n):return a.T
 if a.shape==(n,3):return a
 raise ValueError(f'cannot align xyz array {a.shape} to {n} times')

def signed_shadow_clearance(position_km,sun_vector_km,n_times):
 """Return signed distance-like clearance for aligned Earth-centered vectors."""
 r=_rows_xyz(position_km,n_times); s=_rows_xyz(sun_vector_km,n_times)
 distance=np.linalg.norm(s,axis=1)
 if not np.isfinite(r).all() or not np.isfinite(s).all() or np.any(distance<=0):
  raise FloatingPointError('non-finite or zero Sun/satellite vector')
 u=s/distance[:,None]; axial=np.sum(r*u,axis=1); radius=np.linalg.norm(r,axis=1)
 clearance=np.empty(n_times,dtype=float)
 sunward=axial>=0
 clearance[sunward]=radius[sunward]-EARTH_RADIUS_KM
 behind=~sunward
 x=-axial[behind]
 umbra_radius=EARTH_RADIUS_KM-x*(SUN_RADIUS_KM-EARTH_RADIUS_KM)/distance[behind]
 perpendicular=np.linalg.norm(r[behind]-axial[behind,None]*u[behind],axis=1)
 clearance[behind]=perpendicular-umbra_radius
 return clearance

def target_evaluator(sat,earth,sun,ts,seconds):
 seconds=np.atleast_1d(np.asarray(seconds,dtype=float))
 times=ts.utc([START+timedelta(seconds=float(sec)) for sec in seconds])
 sat_pos=sat.at(times).position.km
 sun_pos=earth.at(times).observe(sun).position.km
 return signed_shadow_clearance(sat_pos,sun_pos,len(seconds))

def scalar_clearance(sat,earth,sun,ts,sec):
 return float(target_evaluator(sat,earth,sun,ts,[sec])[0])

def _root(sat,earth,sun,ts,a,b):
 return brentq(lambda t:scalar_clearance(sat,earth,sun,ts,t),a,b,xtol=ROOT_TOL_S,rtol=1e-12,maxiter=80)

def classify_interval(sat,earth,sun,ts,a,ga,b,gb,ambiguous):
 """Return sunlight subintervals inside [a,b], adaptively certifying its sign."""
 if b<=a:return []
 width=b-a; bound=SUNLIGHT_CLEARANCE_LIPSCHITZ_KM_S*width/2.0
 if ga>=0 and gb>=0 and min(ga,gb)>bound:
  return [(a,b)]
 if ga<0 and gb<0 and max(ga,gb)<-bound:
  return []
 if width<=MIN_AMBIGUOUS_STEP_S:
  mid=(a+b)/2.0; gm=scalar_clearance(sat,earth,sun,ts,mid)
  # Resolve up to two crossings within this smallest leaf. Same-sign samples
  # are accepted only when all three agree; an unresolved sign pattern is
  # conservatively omitted and counted.
  samples=[(a,ga),(mid,gm),(b,gb)]
  changes=[]
  for (left,gl),(right,gr) in zip(samples[:-1],samples[1:]):
   if (gl < 0) != (gr < 0):
    changes.append(_root(sat,earth,sun,ts,left,right))
  if not changes:
   left_bound=SUNLIGHT_CLEARANCE_LIPSCHITZ_KM_S*(mid-a)/2.0
   right_bound=SUNLIGHT_CLEARANCE_LIPSCHITZ_KM_S*(b-mid)/2.0
   if ga>=0 and gm>=0 and gb>=0:
    if min(ga,gm)>left_bound and min(gm,gb)>right_bound:return [(a,b)]
   elif ga<0 and gm<0 and gb<0:
    if max(ga,gm)<-left_bound and max(gm,gb)<-right_bound:return []
   if width<=MIN_CERTIFICATION_STEP_S:
    ambiguous[0]+=1
    return []
   left=classify_interval(sat,earth,sun,ts,a,ga,mid,gm,ambiguous)
   right=classify_interval(sat,earth,sun,ts,mid,gm,b,gb,ambiguous)
   if left and right and abs(left[-1][1]-right[0][0])<=ROOT_TOL_S*2:
    return left[:-1]+[(left[-1][0],right[0][1])]+right[1:]
   return left+right
  bounds=[a,*changes,b]; pieces=[]
  for left,right in zip(bounds[:-1],bounds[1:]):
   if right<=left:continue
   if scalar_clearance(sat,earth,sun,ts,(left+right)/2.0)>=0:
    pieces.append((left,right))
  return pieces
 mid=(a+b)/2.0; gm=scalar_clearance(sat,earth,sun,ts,mid)
 left=classify_interval(sat,earth,sun,ts,a,ga,mid,gm,ambiguous)
 right=classify_interval(sat,earth,sun,ts,mid,gm,b,gb,ambiguous)
 if left and right and abs(left[-1][1]-right[0][0])<=ROOT_TOL_S*2:
  return left[:-1]+[(left[-1][0],right[0][1])]+right[1:]
 return left+right

def load_tles(path):
 lines=Path(path).read_text(encoding='utf-8-sig').splitlines(); result={}
 for i in range(0,len(lines)-2,3):
  name,l1,l2=lines[i:i+3]; result[l1[2:7]]=(name,l1,l2)
 return result

def process_target(rows,sat,earth,sun,ts,writer,counts):
 # Build a 60-second coarse mesh per source C window, then refine only intervals
 # whose signed clearance cannot be certified by the 30 km/s bound.
 row_mesh=[]; all_seconds=[]
 for row in rows:
  a=float(row['start_s']); b=float(row['end_s'])
  if not (0<=a<b<=HORIZON):raise ValueError(f'out-of-horizon C window: {row}')
  mesh=list(np.arange(a,b,DISCOVERY_STEP_S,dtype=float))
  if not mesh or mesh[0]!=a:mesh.insert(0,a)
  elif mesh[0]!=a:mesh.insert(0,a)
  if mesh[-1]!=b:mesh.append(b)
  row_mesh.append(mesh); all_seconds.extend(mesh)
 # Deduplicate identical times across station windows for this target.
 unique=np.array(sorted(set(all_seconds)),dtype=float)
 margins=target_evaluator(sat,earth,sun,ts,unique)
 lookup={float(t):float(g) for t,g in zip(unique,margins)}
 for row,mesh in zip(rows,row_mesh):
  segments=[]; ambiguous=[0]
  for a,b in zip(mesh[:-1],mesh[1:]):
   pieces=classify_interval(sat,earth,sun,ts,a,lookup[a],b,lookup[b],ambiguous)
   segments.extend(pieces)
  if ambiguous[0]:counts['ambiguous_leaves']+=ambiguous[0]
  if not segments:counts['source_windows_no_sunlit_segment']+=1
  # Merge touching pieces and write only positive-duration sunlit intervals.
  merged=[]
  for a,b in segments:
   if b-a<=0:continue
   if merged and a<=merged[-1][1]+ROOT_TOL_S*2:merged[-1]=(merged[-1][0],max(merged[-1][1],b))
   else:merged.append((a,b))
  for a,b in merged:
   if b-a<=0:continue
   out=dict(row); out.update(start_s=a,end_s=b,duration_s=b-a,meets_120s=(b-a)>=120,
       illumination_status='sunlit',illumination_model='finite_sun_conical_umbra',
       illumination_boundary_method='adaptive_clearance_brent')
   writer.writerow(out); counts['output_rows']+=1

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--c',default='m1_validation/formal_20260801_candidate/C_optical/windows.csv'); ap.add_argument('--tle',default='data/轨道.txt'); ap.add_argument('--ephemeris',default='data/ephemeris/de421.bsp'); ap.add_argument('--out',default='m1_validation/formal_20260801_candidate'); ap.add_argument('--batch-targets',type=int,default=100); args=ap.parse_args()
 out=ROOT/args.out; cpath=ROOT/args.c; tlepath=ROOT/args.tle; ephpath=ROOT/args.ephemeris; ddir=out/'D_illumination'; batches=ddir/'batches'; batches.mkdir(parents=True,exist_ok=True); dest=ddir/'windows.csv'; tles=load_tles(tlepath); ts=load.timescale(builtin=True); planets=load(str(ephpath)); earth,sun=planets['earth'],planets['sun']; started=time.perf_counter(); source_sha=sha256(cpath); tle_sha=sha256(tlepath); eph_sha=sha256(ephpath)
 model={'type':'finite_sun_conical_umbra','earth_radius_km':EARTH_RADIUS_KM,'sun_radius_km':SUN_RADIUS_KM,'penumbra':'retained as sunlit'}
 algorithm={'coarse_discovery_step_s':DISCOVERY_STEP_S,'clearance_lipschitz_bound_km_s':SUNLIGHT_CLEARANCE_LIPSCHITZ_KM_S,'adaptive_min_step_s':MIN_AMBIGUOUS_STEP_S,'minimum_certification_step_s':MIN_CERTIFICATION_STEP_S,'root_tolerance_s':ROOT_TOL_S,'ambiguous_fragments':'conservatively excluded'}
 identity={'schema_version':'m1-illumination-adaptive-aug2026-3.0','source_C_sha256':source_sha,'tle_sha256':tle_sha,'ephemeris_sha256':eph_sha,'planning':{'start_utc':START.isoformat(),'end_utc':END.isoformat(),'time_scale':'UTC'},'model':model,'algorithm':algorithm,'batch_targets':args.batch_targets}
 identity['fingerprint']=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
 if dest.exists() and not (ddir/'manifest.json').exists():
  partial=ddir/f'windows.interrupted.{int(time.time())}.partial.csv';os.replace(dest,partial)
  print(json.dumps({'event':'preserved_unmanifested_partial','path':str(partial.relative_to(ROOT))}),flush=True)
 output_fields=None; target_count=source_rows=0; processed_target_ids=set()
 with cpath.open(encoding='utf-8',newline='') as src:
  reader=csv.DictReader(src); input_fields=reader.fieldnames; output_fields=input_fields+['source_C_line','c_start_s','c_end_s','illumination_status','illumination_model','illumination_boundary_method']
  def source_rows_with_provenance():
   for line_number,row in enumerate(reader,2):
    row['source_C_line']=line_number;row['c_start_s']=row['start_s'];row['c_end_s']=row['end_s'];yield row
  grouped=iter(groupby(source_rows_with_provenance(),key=lambda row:row['target_id']))
  batch_number=0
  while True:
   group_batch=[]
   for tid,group in islice(grouped,args.batch_targets):group_batch.append((tid,list(group)))
   if not group_batch:break
   batch_number+=1; rows_batch=group_batch; begin_index=int(rows_batch[0][1][0]['target_index']); end_index=int(rows_batch[-1][1][0]['target_index'])+1
   processed_target_ids.update(tid for tid,_ in rows_batch)
   stem=f'batch_{begin_index:05d}_{end_index-1:05d}'; chunk=batches/f'{stem}.windows.csv'; meta=batches/f'{stem}.manifest.json'
   if meta.exists():
    bm=json.loads(meta.read_text(encoding='utf-8'))
    if bm.get('fingerprint')!=identity['fingerprint'] or not chunk.exists() or bm.get('windows_sha256')!=sha256(chunk):raise RuntimeError(f'invalid D batch resume state: {stem}')
    target_count+=bm['target_count']; source_rows+=bm['source_C_rows'];
    print(json.dumps({'event':'D_batch_resume_hit','batch':batch_number,'targets':[begin_index,end_index]}),flush=True);continue
   if chunk.exists():chunk.unlink()
   batch_counts={'output_rows':0,'source_windows_no_sunlit_segment':0,'ambiguous_leaves':0}; batch_source=0
   def emit(writer):
    nonlocal batch_source
    for tid,rows in rows_batch:
     batch_source+=len(rows)
     if tid not in tles:raise KeyError(f'TLE missing for target {tid}')
     name,l1,l2=tles[tid]; sat=EarthSatellite(l1,l2,name,ts); process_target(rows,sat,earth,sun,ts,writer,batch_counts)
   atomic_csv(chunk,output_fields,emit)
   bm={'fingerprint':identity['fingerprint'],'target_begin':begin_index,'target_end_exclusive':end_index,'target_count':len(rows_batch),'source_C_rows':batch_source,**batch_counts,'windows_sha256':sha256(chunk)}
   atomic_json(meta,bm);target_count+=len(rows_batch);source_rows+=batch_source
   print(json.dumps({'event':'D_batch_committed','batch':batch_number,'targets':[begin_index,end_index],**bm}),flush=True)
 manifests=sorted(batches.glob('batch_*.manifest.json'))
 expected_index=-1;aggregate={'output_rows':0,'source_windows_no_sunlit_segment':0,'ambiguous_leaves':0}
 for mpath in manifests:
  bm=json.loads(mpath.read_text(encoding='utf-8'));chunk=mpath.parent/(mpath.name.replace('.manifest.json','.windows.csv'))
  if bm.get('fingerprint')!=identity['fingerprint'] or bm['target_begin']<expected_index or sha256(chunk)!=bm['windows_sha256']:raise RuntimeError(f'D batch coverage/hash error: {mpath}')
  expected_index=bm['target_end_exclusive']
  for key in aggregate:aggregate[key]+=bm[key]
 source_manifest=json.loads((cpath.parent/'manifest.json').read_text(encoding='utf-8'))
 if source_manifest.get('windows_sha256')!=source_sha or source_rows!=source_manifest.get('window_count'):
  raise RuntimeError(f'D did not account for every C source row: {source_rows} vs {source_manifest.get("window_count")}')
 status_ids=set()
 with (out/'A_orbit/target_status.csv').open(encoding='utf-8',newline='') as status_file:
  status_ids={row['target_id'] for row in csv.DictReader(status_file)}
 targets_without_C=sorted(status_ids-processed_target_ids)
 def merge(writer):
  for mpath in manifests:
   chunk=mpath.parent/(mpath.name.replace('.manifest.json','.windows.csv'))
   with chunk.open(encoding='utf-8',newline='') as f:
    for row in csv.DictReader(f):writer.writerow(row)
 atomic_csv(dest,output_fields,merge)
 manifest={**identity,'layer':'D_illumination','planning_target_count':len(status_ids),'target_count':target_count,'targets_without_C_windows':targets_without_C,'source_C_rows':source_rows,**aggregate,'elapsed_seconds':time.perf_counter()-started,'windows_sha256':sha256(dest)}
 atomic_json(ddir/'manifest.json',manifest); print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
