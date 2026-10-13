"""Run one isolated measured M1 scale; refuse to overwrite any result directory."""
import argparse,csv,json,time,resource,sys,platform,hashlib
from pathlib import Path
from datetime import datetime,timedelta,timezone
from dataclasses import asdict
from collections import Counter
import numpy as np
from skyfield.api import load
from m1 import load_tle,load_stations
from visibility import NumericPolicy,Geometry,OrbitEvaluator,refine_windows,coarse_windows
from validator import IndependentValidator,ValidationPolicy

def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def run(args):
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    start=datetime.fromisoformat(args.start.replace('Z','+00:00'))
    if start.tzinfo is None:raise ValueError('start must include timezone')
    start=start.astimezone(timezone.utc)
    horizon=args.hours*3600
    if horizon<=0 or args.targets<=0:raise ValueError('positive horizon and target count required')
    p=NumericPolicy();vp=ValidationPolicy();records,format_errors=load_tle(args.tle);stations=load_stations(args.stations)
    if args.targets>len(records):raise ValueError('requested scale exceeds actual dataset')
    ts=load.timescale(builtin=True);geometry=Geometry(ts,start,stations)
    grid=np.r_[np.arange(0,horizon,p.discovery_step_s),horizon]
    coarse_t=np.r_[np.arange(0,horizon,p.coarse_step_s),horizon]
    if horizon % p.discovery_step_s or p.coarse_step_s%p.discovery_step_s:raise ValueError('this runner requires divisible sampling intervals')
    coarse_idx=np.searchsorted(grid,coarse_t)
    prepared=geometry.prepare(grid)
    counts=Counter();reasons=Counter();failures=[];station_counts=Counter();opportunities=[]
    fields=['target_index','norad_id','name','station_id','site','start_utc','end_utc','start_s','end_s','duration_s','start_kind','end_kind','start_residual_deg','end_residual_deg','refinement_status','validation_status','validation_reasons','checked_samples','min_elevation_deg','max_elevation_deg','max_final_gap_s','coarse_start_s','coarse_end_s','start_error_s','end_error_s']
    t0=time.perf_counter();generation_s=validation_s=0.
    with (out/'windows.csv').open('w',newline='',encoding='utf-8') as f, (out/'coarse_windows.csv').open('w',newline='',encoding='utf-8') as cf, (out/'anomalies.jsonl').open('w',encoding='utf-8') as af:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        cw=csv.DictWriter(cf,fieldnames=['target_index','norad_id','station_id','site','start_s','end_s']);cw.writeheader()
        for idx,record in enumerate(records[:args.targets]):
            tic=time.perf_counter();ev=OrbitEvaluator(record,geometry);el=ev.grid(grid,prepared)
            coarse=coarse_windows(coarse_t,el[:,coarse_idx],p);counts['coarse_windows']+=len(coarse)
            for w in coarse:cw.writerow(dict(target_index=idx,norad_id=record[1][2:7],station_id=stations[w['site']]['id'],**w))
            windows,anomalies=refine_windows(ev,grid,el,p)
            # Even finite-position error codes reject all candidates for the target.
            if ev.error_samples:
                windows=[];anomalies.append(dict(site=None,reason='target_sgp4_error',error_samples=ev.error_samples,error_codes=ev.error_codes))
                counts['generation_failed_targets']+=1
            counts['generation_error_samples']+=ev.error_samples;counts['generation_evaluations']+=ev.evaluations
            generation_s+=time.perf_counter()-tic
            counts['refined_windows']+=len(windows)
            counts['quarantined_station_target_pairs']+=len({x['site'] for x in anomalies if x.get('site') is not None})
            counts['quarantined_coarse_windows']+=sum(any(x.get('site')==w['site'] or x.get('site') is None for x in anomalies) for w in coarse)
            for anomaly in anomalies:
                anomaly.update(scope_start_s=0,scope_end_s=horizon,scope='entire_station_target_pair' if anomaly.get('site') is not None else 'entire_target')
                reasons[anomaly['reason']]+=1;af.write(json.dumps(dict(target_index=idx,norad_id=record[1][2:7],**anomaly),ensure_ascii=False,allow_nan=False)+'\n')
            tic=time.perf_counter();validator=IndependentValidator(record,ts,start,stations,horizon,vp);target_count=0
            for w in windows:
                result=validator.check(w);counts[result['status']]+=1
                row=dict(target_index=idx,norad_id=record[1][2:7],name=record[0],station_id=stations[w['site']]['id'],**w,
                         start_utc=(start+timedelta(seconds=w['start_s'])).isoformat(),end_utc=(start+timedelta(seconds=w['end_s'])).isoformat(),duration_s=w['end_s']-w['start_s'],validation_status=result['status'],validation_reasons=';'.join(result['reasons']),
                         **{k:result[k] for k in ['checked_samples','min_elevation_deg','max_elevation_deg','max_final_gap_s']})
                matches=[c for c in coarse if c['site']==w['site'] and min(c['end_s'],w['end_s'])>max(c['start_s'],w['start_s'])]
                if len(matches)==1:
                    c=matches[0];row.update(coarse_start_s=c['start_s'],coarse_end_s=c['end_s'],start_error_s=c['start_s']-w['start_s'],end_error_s=c['end_s']-w['end_s'])
                    counts['coarse_matched_refined_windows']+=1
                elif not matches:counts['recovered_without_coarse_overlap']+=1
                else:counts['multiple_coarse_matches']+=1
                writer.writerow(row)
                if result['status']=='sampled_valid':station_counts[stations[w['site']]['id']]+=1;target_count+=1
                else:
                    for reason in result['reasons']:reasons[reason]+=1
                    af.write(json.dumps(dict(target_index=idx,norad_id=record[1][2:7],site=w['site'],start_s=w['start_s'],end_s=w['end_s'],validator=result),ensure_ascii=False,allow_nan=False)+'\n')
            counts['validator_error_samples']+=validator.error_samples;counts['validator_evaluations']+=validator.evaluations
            if validator.error_samples:counts['validation_failed_targets']+=1
            validation_s+=time.perf_counter()-tic;opportunities.append(target_count)
            if (idx+1)%100==0:print(f'{idx+1}/{args.targets}: refined={counts["refined_windows"]}, valid={counts["sampled_valid"]}, elapsed={time.perf_counter()-t0:.1f}s',flush=True)
    elapsed=time.perf_counter()-t0
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**2 if sys.platform=='darwin' else 1024)
    summary=dict(measurement_kind='actual_single_process_wall_clock_and_os_peak_rss',targets=args.targets,stations=len(stations),start_utc=start.isoformat(),hours=args.hours,coarse_step_s=p.coarse_step_s,discovery_step_s=p.discovery_step_s,
                 elapsed_s=elapsed,generation_s=generation_s,validation_s=validation_s,peak_rss_mib=rss,**counts,
                 candidate_windows=counts['refined_windows']+counts['quarantined_coarse_windows'],
                 refinement_success_rate=counts['refined_windows']/max(1,counts['refined_windows']+counts['quarantined_coarse_windows']),
                 numeric_validation_pass_rate=counts['sampled_valid']/max(1,counts['refined_windows']),
                 refinement_rate_denominator_note='refined components + quarantined coarse components; splitting/recovery changes components; unknown missed windows are not in denominator',
                 propagation_failure_count=counts['generation_failed_targets']+counts['validation_failed_targets'],
                 propagation_failure_note='phase-specific target failures; generation and validator sample counts separately; same SGP4 model is shared',
                 anomaly_reasons=dict(reasons),station_candidate_counts={str(s['id']):station_counts[s['id']] for s in stations},format_error_count=len(format_errors),numeric_policy=asdict(p),validation_policy=asdict(vp),
                 environment=dict(python=sys.version,platform=platform.platform(),processor=platform.processor(),numpy=np.__version__),
                 source_sha256={str(x):hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in ['m1.py','visibility.py','validator.py','run_validation.py']},
                 input_sha256={str(x):hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in [args.tle,args.stations]},
                 limits=['Finite discovery/extremum search cannot prove complete detection of arbitrarily short windows or multiple sub-grid extrema.', 'sampled_valid is numerical sampled evidence, not a continuous visibility proof or real orbit accuracy guarantee.', 'No atmospheric refraction/polar motion correction, builtin UT1 timescale; demonstration date, not official scheduling date.', 'No scheduling, single-observation duration, switching time or target priorities.'])
    dump(out/'summary.json',summary);dump(out/'target_opportunities.json',opportunities)
    dump(out/'stations.json',stations)
    print(json.dumps({k:summary[k] for k in ['targets','elapsed_s','peak_rss_mib','coarse_windows','candidate_windows','refinement_success_rate','numeric_validation_pass_rate','propagation_failure_count']},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--targets',type=int,required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--tle',default='data/轨道.txt');parser.add_argument('--stations',default='data/站址.txt');parser.add_argument('--start',default='2026-08-03T00:00:00Z');parser.add_argument('--hours',type=float,default=24)
    run(parser.parse_args())
