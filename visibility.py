"""M1 numeric visibility only. Finite discovery is explicitly not a completeness proof."""
from dataclasses import dataclass, asdict
import numpy as np
from sgp4.api import Satrec

@dataclass(frozen=True)
class NumericPolicy:
    coarse_step_s: float = 60.0
    discovery_step_s: float = 15.0
    root_time_tol_s: float = 1e-6
    root_elevation_tol_deg: float = 2e-5
    extrema_time_tol_s: float = 1e-3
    min_elevation_deg: float = 10.0
    max_elevation_deg: float = 85.0
    max_iterations: int = 64

class PropagationError(RuntimeError):
    pass

class Geometry:
    """WGS84 ground geometry; own TEME->PEF rotation, no atmospheric refraction."""
    def __init__(self, ts, start, stations):
        self.ts, self.epoch = ts, ts.from_datetime(start)
        self.stations = stations
        lon = np.radians([s['lon'] for s in stations])
        lat = np.radians([s['lat'] for s in stations])
        h = np.array([s['elevation_m'] for s in stations]) / 1000
        a, f = 6378.137, 1 / 298.257223563
        n = a / np.sqrt(1 - f * (2 - f) * np.sin(lat)**2)
        self.xyz = np.array([(n+h)*np.cos(lat)*np.cos(lon),
                             (n+h)*np.cos(lat)*np.sin(lon),
                             (n*(1-f)**2+h)*np.sin(lat)]).T
        self.up = np.array([np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)]).T

    def times(self, seconds):
        return self.ts.tt_jd(self.epoch.whole, self.epoch.tt_fraction + np.asarray(seconds)/86400)

    def prepare(self, seconds):
        t = self.times(seconds)
        # Vallado GMST1982, UT1 from the pinned Skyfield builtin timescale.
        centuries = (t.whole - 2451545.0 + t.ut1_fraction) / 36525
        g = 67310.54841 + (8640184.812866 + (.093104 - 6.2e-6*centuries)*centuries)*centuries
        theta = ((t.whole % 1 + t.ut1_fraction + (g/86400) % 1) % 1) * 2*np.pi
        return (np.ascontiguousarray(t.whole),
                np.ascontiguousarray(t.tai_fraction-t._leap_seconds()/86400),
                np.cos(theta), np.sin(theta))

class OrbitEvaluator:
    def __init__(self, record, geometry):
        self.record, self.geometry = record, geometry
        self.sat = Satrec.twoline2rv(record[1], record[2])
        self.evaluations = self.error_samples = 0
        self.error_codes = {}

    def positions(self, seconds, prepared=None):
        seconds = np.atleast_1d(seconds).astype(float)
        jd, fr, c, s = prepared if prepared is not None else self.geometry.prepare(seconds)
        errors, r, _ = self.sat.sgp4_array(jd, fr)
        self.evaluations += len(seconds)
        bad = (errors != 0) | ~np.all(np.isfinite(r), axis=1)
        self.error_samples += int(bad.sum())
        for code, count in zip(*np.unique(errors[bad], return_counts=True)):
            self.error_codes[str(int(code))] = self.error_codes.get(str(int(code)), 0) + int(count)
        fixed = np.column_stack([c*r[:,0]+s*r[:,1], -s*r[:,0]+c*r[:,1], r[:,2]])
        fixed[bad] = np.nan
        return fixed

    def grid(self, seconds, prepared=None):
        r = self.positions(seconds, prepared)
        delta = r[None,:,:] - self.geometry.xyz[:,None,:]
        sine = np.einsum('snc,sc->sn', delta, self.geometry.up) / np.linalg.norm(delta,axis=2)
        return np.degrees(np.arcsin(np.clip(sine,-1,1)))

    def __call__(self, seconds, sites):
        r = self.positions(seconds)
        sites = np.asarray(sites, dtype=int)
        delta = r - self.geometry.xyz[sites]
        return np.degrees(np.arcsin(np.clip(np.einsum('nc,nc->n',delta,self.geometry.up[sites]) /
                                             np.linalg.norm(delta,axis=1),-1,1)))

def visible(e, p):
    return np.isfinite(e) & (e >= p.min_elevation_deg) & (e <= p.max_elevation_deg)

def coarse_windows(times, elevations, p):
    """Clip at the actual planning end; preserve legacy first-false boundary convention."""
    result=[]
    for site, values in enumerate(elevations):
        mask=visible(values,p)
        starts=np.flatnonzero(mask & ~np.r_[False,mask[:-1]])
        for begin in starts:
            stop=begin
            while stop+1<len(times) and mask[stop+1]: stop+=1
            end=min(stop+1,len(times)-1)
            if times[end]>times[begin]: result.append(dict(site=site,start_s=float(times[begin]),end_s=float(times[end])))
    return result

def refine_windows(evaluate, times, elevations, p=NumericPolicy()):
    """Detect extrema near constraints, batch golden search and bisect both constraints.

    Cannot prove no multiple sub-grid extrema. A station with failed samples or
    root/critical-point search is quarantined, never silently accepted.
    """
    times=np.asarray(times); elevations=np.asarray(elevations)
    anomalies=[]; quarantined=set(); points=[list(times) for _ in elevations]
    values=[list(v) for v in elevations]
    extrema=[]
    for site,e in enumerate(elevations):
        if not np.all(np.isfinite(e)):
            anomalies.append(dict(site=site,reason='nonfinite_discovery_or_sgp4_error'));quarantined.add(site);continue
        center=e[1:-1]
        maximum=(center>=e[:-2]) & (center>e[2:])
        minimum=(center<=e[:-2]) & (center<e[2:])
        near_max=((0<=center)&(center<p.min_elevation_deg)) | ((75<=center)&(center<=p.max_elevation_deg))
        near_min=((p.min_elevation_deg<=center)&(center<20)) | ((p.max_elevation_deg<center)&(center<=90))
        for j in np.flatnonzero((maximum & near_max) | (minimum & near_min)):
            i=j+1
            extrema.append((site,times[i-1],times[i+1],-1 if maximum[j] else 1))
        # Planning edges can contain a partial grazing peak.
        for left,right,idx in [(times[0],times[1],0),(times[-2],times[-1],-1)]:
            if 0<=e[idx]<p.min_elevation_deg or 75<=e[idx]<=85:
                extrema.append((site,left,right,-1))
    if extrema:
        s=np.array([x[0] for x in extrema]); a=np.array([x[1] for x in extrema]);b=np.array([x[2] for x in extrema]);direction=np.array([x[3] for x in extrema])
        q=(np.sqrt(5)-1)/2
        x=b-q*(b-a);y=a+q*(b-a)
        fx=evaluate(x,s)*direction;fy=evaluate(y,s)*direction
        for _ in range(p.max_iterations):
            if np.max(b-a)<=p.extrema_time_tol_s: break
            left=fx<fy
            b=np.where(left,y,b);a=np.where(left,a,x)
            x=b-q*(b-a);y=a+q*(b-a)
            fx=evaluate(x,s)*direction;fy=evaluate(y,s)*direction
        z=(a+b)/2;ez=evaluate(z,s)
        for site,t,e,width in zip(s,z,ez,b-a):
            if not np.isfinite(e) or width>p.extrema_time_tol_s:
                quarantined.add(int(site));anomalies.append(dict(site=int(site),reason='unreliable_extremum_search'))
            else: points[site].append(float(t));values[site].append(float(e))
    brackets=[]; roots=[[] for _ in elevations]
    for site in range(len(elevations)):
        if site in quarantined:continue
        order=np.argsort(points[site]); t=np.array(points[site])[order]; e=np.array(values[site])[order]
        for threshold in [p.min_elevation_deg,p.max_elevation_deg]:
            zeros=np.flatnonzero(e==threshold)
            roots[site].extend((float(t[i]),threshold,0.) for i in zeros)
            for i in np.flatnonzero((e[:-1]-threshold)*(e[1:]-threshold)<0):
                brackets.append((site,t[i],t[i+1],e[i]-threshold,threshold))
    if brackets:
        s=np.array([x[0] for x in brackets]);a=np.array([x[1] for x in brackets]);b=np.array([x[2] for x in brackets]);fa=np.array([x[3] for x in brackets]);h=np.array([x[4] for x in brackets]);bad=np.zeros(len(s),bool)
        for _ in range(p.max_iterations):
            mid=(a+b)/2;fm=evaluate(mid,s)-h;bad|=~np.isfinite(fm)
            left=(fa*fm<=0);b=np.where(left,mid,b);a=np.where(left,a,mid);fa=np.where(left,fa,fm)
            if np.max(b-a)<=p.root_time_tol_s:break
        z=(a+b)/2;residual=np.abs(evaluate(z,s)-h)
        for site,t,threshold,width,res,failed in zip(s,z,h,b-a,residual,bad):
            if failed or width>p.root_time_tol_s or not np.isfinite(res) or res>p.root_elevation_tol_deg:
                quarantined.add(int(site));anomalies.append(dict(site=int(site),reason='unreliable_root',time_s=float(t),threshold_deg=float(threshold),residual_deg=float(res) if np.isfinite(res) else None))
            else:roots[site].append((float(t),float(threshold),float(res)))
    segments=[]
    for site,rr in enumerate(roots):
        if site in quarantined:continue
        edges=[(float(times[0]),'planning_start',0.)]+[(t,f'elevation_{h:g}',r) for t,h,r in sorted(rr) if times[0]<t<times[-1]]+[(float(times[-1]),'planning_end',0.)]
        # Tangential equality alone gives a zero-duration event, never an observation interval.
        for left,right in zip(edges,edges[1:]):
            if right[0]-left[0]<=p.root_time_tol_s:continue
            segments.append((site,left,right))
    windows=[]
    if segments:
        mid=np.array([(x[1][0]+x[2][0])/2 for x in segments]);s=np.array([x[0] for x in segments]);e=evaluate(mid,s)
        for (site,left,right),v in zip(segments,e):
            if not np.isfinite(v):
                quarantined.add(site);anomalies.append(dict(site=site,reason='nonfinite_interval_probe'));continue
            if visible(v,p):
                windows.append(dict(site=site,start_s=left[0],end_s=right[0],start_kind=left[1],end_kind=right[1],start_residual_deg=left[2],end_residual_deg=right[2],refinement_status='refined'))
    # Never accept other windows at a station that had any unresolved component.
    return [w for w in windows if w['site'] not in quarantined],anomalies
