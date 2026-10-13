import argparse,csv,json,re,time
from pathlib import Path
from datetime import datetime,timedelta,timezone
import numpy as np

def load_tle(path):
    lines=Path(path).read_text(encoding='utf-8-sig').splitlines()
    if len(lines)%3: raise ValueError('TLE记录不是完整三行组')
    records=[];errors=[]
    for k in range(0,len(lines),3):
        name,a,b=lines[k:k+3]
        if not(name.startswith('0 ') and a.startswith('1 ') and b.startswith('2 ') and a[2:7]==b[2:7] and len(a)>=69 and len(b)>=69):
            errors.append(k//3+1);continue
        records.append((name[2:].strip(),a,b))
    return records,errors

def load_stations(path):
    out=[]
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        m=re.match(r'^\s*(\d+)\s*[：:]\s*([+-]?[\d.]+)\s*,\s*([+-]?[\d.]+)\s*,\s*([+-]?[\d.]+)',line)
        if m:
            ident,lon,lat,h=m.groups();lon=float(lon)%360;lat=float(lat);h=float(h)
            if not -90<=lat<=90: raise ValueError('纬度错误 '+ident)
            out.append(dict(id=int(ident),lon=lon,lat=lat,elevation_m=h))
    if not out:raise ValueError('没有解析到站址')
    return out

def windows_from_mask(mask,times,step_seconds):
    edges=np.diff(np.r_[False,mask,False].astype(int))
    starts=np.where(edges==1)[0];ends=np.where(edges==-1)[0]
    return [(times[s],times[e] if e<len(times) else times[-1]+timedelta(seconds=step_seconds)) for s,e in zip(starts,ends)]

def main():
    p=argparse.ArgumentParser();p.add_argument('--tle',default='data/轨道.txt');p.add_argument('--stations',default='data/站址.txt');p.add_argument('--start',default='2026-08-03T00:00:00Z');p.add_argument('--hours',type=float,default=24);p.add_argument('--step',type=int,default=60);p.add_argument('--targets',type=int,default=100);p.add_argument('--out',default='output');a=p.parse_args()
    if a.hours<=0 or a.step<=0 or a.targets<=0:raise ValueError('hours/step/targets必须为正')
    rec,err=load_tle(a.tle);stations=load_stations(a.stations)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    audit=dict(targets=len(rec),tle_format_errors=len(err),unique_catalog_ids=len({r[1][2:7] for r in rec}),stations=len(stations),elevation_min_deg=10,elevation_max_deg=85,station_coordinates=stations)
    (out/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        from skyfield.api import load,EarthSatellite,wgs84
    except ImportError as e:raise SystemExit('请先执行 pip install -r requirements.txt；audit.json已生成') from e
    start=datetime.fromisoformat(a.start.replace('Z','+00:00'))
    if start.tzinfo is None:raise ValueError('开始时间必须包含时区，例如Z')
    start=start.astimezone(timezone.utc)
    n=int(np.ceil(a.hours*3600/a.step));dates=[start+timedelta(seconds=k*a.step) for k in range(n+1)]
    ts=load.timescale();t=ts.from_datetimes(dates)
    sites=[(s,wgs84.latlon(s['lat'],s['lon'],elevation_m=s['elevation_m'])) for s in stations]
    count=0;fail=[];tic=time.perf_counter()
    with (out/'windows.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['station_id','norad_id','name','start_utc','end_utc','duration_seconds','min_elevation_deg','max_elevation_deg','sampling_step_seconds'])
        for name,l1,l2 in rec[:a.targets]:
            try:
                sat=EarthSatellite(l1,l2,name,ts)
                for site,loc in sites:
                    alt,az,distance=(sat-loc).at(t).altaz();elev=alt.degrees
                    mask=np.isfinite(elev)&(elev>=10)&(elev<=85)
                    for begin,end in windows_from_mask(mask,dates,a.step):
                        writer.writerow([site['id'],l1[2:7],name,begin.isoformat(),end.isoformat(),(end-begin).total_seconds(),10,85,a.step]);count+=1
            except Exception as ex:fail.append({'norad_id':l1[2:7],'error':str(ex)})
    result={**audit,'start_utc':start.isoformat(),'hours':a.hours,'step_seconds':a.step,'processed_targets':min(a.targets,len(rec)),'candidate_windows':count,'propagation_failures':fail[:20],'failure_count':len(fail),'elapsed_seconds':round(time.perf_counter()-tic,3),'note':'采样窗口为离散近似，边界误差可达一个采样步长；不能直接视为精确硬约束合格证明。'}
    (out/'run_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
