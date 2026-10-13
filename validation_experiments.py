"""Independent dense and scalar-root audit of generated CSV artifacts."""
import argparse,csv,json,time
from collections import defaultdict
from pathlib import Path
from datetime import datetime
import numpy as np
from scipy.optimize import brentq
from skyfield.api import load
from m1 import load_tle,load_stations
from validator import IndependentValidator

def write_json(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False))

def main(root):
    root=Path(root);out=root/'experiments';out.mkdir(exist_ok=False)
    records,_=load_tle('data/轨道.txt');stations=load_stations('data/站址.txt');ts=load.timescale(builtin=True)
    summary=json.loads((root/'scale_100/summary.json').read_text());start=datetime.fromisoformat(summary['start_utc']);horizon=summary['hours']*3600
    all_windows=list(csv.DictReader((root/'scale_10000/windows.csv').open()))
    windows=all_windows
    target_indices=list(range(100))+np.linspace(100,9999,100).astype(int).tolist()
    grouped=defaultdict(list)
    for w in windows:grouped[(int(w['target_index']),int(w['site']))].append(w)
    tic=time.perf_counter();dense=[];samples=errors=0
    # Independent coverage census at 1-second resolution, first 100 plus 100 stratified targets, all 10 stations.
    t=np.arange(0,horizon+1,1.)
    for ordinal,idx in enumerate(target_indices):
        record=records[idx]
        v=IndependentValidator(record,ts,start,stations,horizon)
        for site in range(len(stations)):
            e=v.elevations(t,site);actual=np.isfinite(e)&(e>=10)&(e<=85)
            represented=np.zeros(len(t),bool)
            for w in grouped[(idx,site)]:represented|=(t>=float(w['start_s']))&(t<=float(w['end_s']))
            missing=actual&~represented;extra=represented&~actual
            dense.append(dict(target_index=idx,station_id=stations[site]['id'],visible_sample_count=int(actual.sum()),missed_visible_samples=int(missing.sum()),invalid_included_samples=int(extra.sum())))
        samples+=v.evaluations;errors+=v.error_samples
        if (ordinal+1)%10==0:print(f'dense independent reference {ordinal+1}/{len(target_indices)}, {time.perf_counter()-tic:.1f}s',flush=True)
    with (out/'dense_1s_coverage.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(dense[0]));writer.writeheader();writer.writerows(dense)
    dense_summary=dict(measurement_kind='actual',targets=len(target_indices),target_indices=target_indices,stations=len(stations),step_s=1,evaluated_samples=samples,propagation_error_samples=errors,missed_visible_samples=sum(r['missed_visible_samples'] for r in dense),invalid_included_samples=sum(r['invalid_included_samples'] for r in dense),elapsed_s=time.perf_counter()-tic,limits='Independent finite 1-second census; does not prove sub-second completeness.')
    write_json(out/'dense_summary.json',dense_summary)
    short=sorted(all_windows,key=lambda w:float(w['duration_s']))[:40]
    high=[w for w in all_windows if '85' in w['start_kind'] or '85' in w['end_kind']]
    chosen=short+high[:100]+[all_windows[i] for i in np.linspace(0,len(all_windows)-1,200).astype(int)]
    unique={(w['target_index'],w['site'],w['start_s'],w['end_s']):w for w in chosen};chosen=list(unique.values())
    references=[];short_results=[];cached={}
    for w in chosen:
        idx=int(w['target_index']);site=int(w['site']);a=float(w['start_s']);b=float(w['end_s'])
        if idx not in cached:cached[idx]=IndependentValidator(records[idx],ts,start,stations,horizon)
        v=cached[idx]
        for edge in ['start','end']:
            kind=w[edge+'_kind'];value=float(w[edge+'_s'])
            if kind.startswith('planning'):continue
            threshold=float(kind.split('_')[1]);delta=min(.1,(b-a)/4)
            left=max(0,value-delta);right=min(horizon,value+delta)
            function=lambda x:float(v.elevations([x],site)[0]-threshold)
            try:
                root_s=brentq(function,left,right,xtol=1e-9)
                coarse=w.get('coarse_'+edge+'_s','')
                references.append(dict(target_index=idx,station_id=stations[site]['id'],site=site,edge=edge,threshold_deg=threshold,generated_s=value,reference_s=root_s,refined_abs_error_s=abs(value-root_s),coarse_abs_error_s=abs(float(coarse)-root_s) if coarse else '',reference_residual_deg=abs(function(root_s)),status='ok'))
            except Exception as ex:
                references.append(dict(target_index=idx,station_id=stations[site]['id'],site=site,edge=edge,threshold_deg=threshold,generated_s=value,status=str(ex)))
    for w in short:
        idx=int(w['target_index']);site=int(w['site']);a=float(w['start_s']);b=float(w['end_s']);v=cached[idx]
        t=np.linspace(a,b,max(3,int(np.ceil((b-a)/.1))+1));e=v.elevations(t,site)
        short_results.append(dict(target_index=idx,norad_id=w['norad_id'],station_id=stations[site]['id'],duration_s=b-a,dense_max_gap_s=float(np.max(np.diff(t))),samples=len(t),min_elevation_deg=float(np.nanmin(e)),max_elevation_deg=float(np.nanmax(e)),violations=int(np.sum(~np.isfinite(e)|(e<10-5e-5)|(e>85+5e-5))),has_coarse_overlap=bool(w['coarse_start_s'])))
    with (out/'boundary_reference.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['target_index','station_id','site','edge','threshold_deg','generated_s','reference_s','refined_abs_error_s','coarse_abs_error_s','reference_residual_deg','status']);writer.writeheader();writer.writerows(references)
    with (out/'short_windows.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(short_results[0]));writer.writeheader();writer.writerows(short_results)
    good=[r for r in references if r['status']=='ok']
    write_json(out/'reference_summary.json',dict(measurement_kind='actual',selected_windows=len(chosen),boundary_roots=len(references),boundary_reference_failures=len(references)-len(good),max_refined_abs_error_s=max(r['refined_abs_error_s'] for r in good),p95_refined_abs_error_s=float(np.percentile([r['refined_abs_error_s'] for r in good],95)),short_real_windows=len(short),short_window_violations=sum(r['violations'] for r in short_results),shortest_duration_s=min(r['duration_s'] for r in short_results),propagation_error_samples=sum(v.error_samples for v in cached.values()),reference_method='independent validator + scipy Brent scalar root; selected subset, not all boundaries'))
    # Constructed grazing cases have analytic boundaries; explicitly label them
    # synthetic so they cannot be mistaken for measured satellite opportunities.
    from visibility import NumericPolicy,refine_windows,coarse_windows
    synthetic=[];policy=NumericPolicy();grid=np.arange(0,181,15.);coarse=np.arange(0,181,60.)
    for duration in [.2,1,3,10,25,45]:
        function=lambda t:10+.005*((duration/2)**2-(t-67.3)**2)
        recovered,anomalies=refine_windows(lambda t,s:function(t),grid,function(grid)[None,:],policy)
        expected_start=67.3-duration/2;expected_end=67.3+duration/2
        synthetic.append(dict(data_kind='synthetic_analytic_case',expected_duration_s=duration,coarse_detected=bool(coarse_windows(coarse,function(coarse)[None,:],policy)),discovery_grid_detected=bool(np.any(function(grid)>=10)),recovered_count=len(recovered),anomaly_count=len(anomalies),start_abs_error_s=abs(recovered[0]['start_s']-expected_start) if recovered else None,end_abs_error_s=abs(recovered[0]['end_s']-expected_end) if recovered else None))
    with (out/'synthetic_short_windows.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(synthetic[0]));writer.writeheader();writer.writerows(synthetic)
    write_json(out/'synthetic_summary.json',dict(data_kind='synthetic_analytic_cases',cases=len(synthetic),all_recovered=all(r['recovered_count']==1 and r['anomaly_count']==0 for r in synthetic),coarse_missed=sum(not r['coarse_detected'] for r in synthetic),discovery_grid_missed=sum(not r['discovery_grid_detected'] for r in synthetic)))
    print(json.dumps(dense_summary,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='m1_validation/final');main(p.parse_args().root)
