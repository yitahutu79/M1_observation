"""Audit shortest natural windows separately from planning-boundary clipping."""
import csv,json
from pathlib import Path
from datetime import datetime
import numpy as np
from skyfield.api import load
from m1 import load_tle,load_stations
from validator import IndependentValidator

root=Path('m1_validation/final');out=root/'experiments'
with (root/'scale_10000/windows.csv').open() as f:rows=list(csv.DictReader(f))
unclipped=[w for w in rows if 'planning' not in w['start_kind']+w['end_kind']]
short=sorted(unclipped,key=lambda w:float(w['duration_s']))[:40]
records,_=load_tle('data/轨道.txt');stations=load_stations('data/站址.txt');ts=load.timescale(builtin=True)
start=datetime.fromisoformat(json.loads((root/'scale_10000/summary.json').read_text())['start_utc'])
checks=[]
for w in short:
    idx=int(w['target_index']);site=int(w['site']);a=float(w['start_s']);b=float(w['end_s'])
    validator=IndependentValidator(records[idx],ts,start,stations,86400)
    t=np.linspace(a,b,max(3,int(np.ceil((b-a)/.01))+1));e=validator.elevations(t,site)
    checks.append(dict(data_kind='actual_unclipped_window',target_index=idx,norad_id=w['norad_id'],station_id=w['station_id'],duration_s=b-a,samples=len(t),max_gap_s=float(np.max(np.diff(t))),min_elevation_deg=float(e.min()),max_elevation_deg=float(e.max()),violations=int(np.sum(~np.isfinite(e)|(e<10-5e-5)|(e>85+5e-5))),propagation_error_samples=validator.error_samples,coarse_overlap=bool(w['coarse_start_s'])))
with (out/'short_unclipped_windows.csv').open('x',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(checks[0]));writer.writeheader();writer.writerows(checks)
summary=dict(measurement_kind='actual',all_unclipped_count=len(unclipped),all_clipped_count=len(rows)-len(unclipped),audited_windows=len(checks),shortest_unclipped_duration_s=checks[0]['duration_s'],shortest_unclipped_norad_id=checks[0]['norad_id'],shortest_unclipped_station_id=checks[0]['station_id'],audited_windows_without_coarse_overlap=sum(not r['coarse_overlap'] for r in checks),violations=sum(r['violations'] for r in checks),propagation_error_samples=sum(r['propagation_error_samples'] for r in checks),max_sampling_gap_s=max(r['max_gap_s'] for r in checks))
(out/'short_unclipped_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
