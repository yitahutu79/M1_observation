"""Standalone revalidation entry point: consumes CSV, never invokes generation."""
import argparse,csv,json,hashlib,math
from pathlib import Path
from datetime import datetime
from skyfield.api import load
from m1 import load_tle,load_stations
from validator import IndependentValidator

def main():
    p=argparse.ArgumentParser();p.add_argument('--windows',required=True);p.add_argument('--summary',required=True);p.add_argument('--out',required=True)
    p.add_argument('--tle',default='data/轨道.txt');p.add_argument('--stations',default='data/站址.txt');args=p.parse_args()
    out=Path(args.out)
    if out.exists():raise FileExistsError(out)
    metadata=json.loads(Path(args.summary).read_text());records,_=load_tle(args.tle);stations=load_stations(args.stations)
    for path in [args.tle,args.stations]:
        expected=metadata.get('input_sha256',{}).get(path)
        if expected and hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('input file differs from recorded SHA256: '+path)
    ts=load.timescale(builtin=True);start=datetime.fromisoformat(metadata['start_utc']);current=None;v=None
    with Path(args.windows).open(newline='') as source,out.open('x',encoding='utf-8') as dest:
        for row in csv.DictReader(source):
            try:
                idx=int(row['target_index'])
                if not 0<=idx<len(records):raise ValueError('target index out of range')
                if idx!=current:v=IndependentValidator(records[idx],ts,start,stations,metadata['hours']*3600);current=idx
                if records[idx][1][2:7]!=row['norad_id']:raise ValueError('catalog identity mismatch')
                for field in ['start_s','end_s','duration_s']:
                    if not math.isfinite(float(row[field])):raise ValueError('nonfinite '+field)
                site=int(row['site'])
                if not 0<=site<len(stations) or int(row['station_id'])!=stations[site]['id']:raise ValueError('station identity mismatch')
                for edge in ['start','end']:
                    timestamp=datetime.fromisoformat(row[edge+'_utc'])
                    if timestamp.tzinfo is None:raise ValueError('naive UTC timestamp')
                    if abs((timestamp-start).total_seconds()-float(row[edge+'_s']))>2e-6:raise ValueError('UTC and relative seconds disagree')
                if abs(float(row['duration_s'])-(float(row['end_s'])-float(row['start_s'])))>2e-6:raise ValueError('duration mismatch')
                result=v.check(row)
            except Exception as exc:
                result=dict(status='unresolved',reasons=['input_or_validation_exception: '+str(exc)])
                idx=row.get('target_index')
            dest.write(json.dumps(dict(target_index=idx,norad_id=row['norad_id'],station_id=row['station_id'],start_s=row['start_s'],end_s=row['end_s'],**result),ensure_ascii=False,allow_nan=False)+'\n')
if __name__=='__main__':main()
