"""Independent M1 validator: does not import generator or its geometry/root code.

Uses Skyfield's independent TEME-to-ITRF conversion and WGS84 site coordinates, but shares the SGP4 physical
model. Numeric acceptance is finite sampled evidence, not continuous proof.
"""
from dataclasses import dataclass, asdict
import numpy as np
from skyfield.api import EarthSatellite, wgs84
from skyfield.constants import AU_KM

@dataclass(frozen=True)
class ValidationPolicy:
    time_tolerance_s: float = 2e-6
    elevation_tolerance_deg: float = 5e-5
    boundary_probe_s: float = .05
    base_gap_s: float = 5.
    near_boundary_gap_s: float = .1
    minimum_gap_s: float = .01
    curvature_tolerance_deg: float = .005
    near_constraint_deg: float = .02
    sample_budget: int = 250000
    max_depth: int = 20

class IndependentValidator:
    def __init__(self, record, ts, start, stations, horizon_s, policy=ValidationPolicy()):
        self.ts=ts;self.epoch=ts.from_datetime(start);self.horizon=horizon_s;self.policy=policy
        self.sat=EarthSatellite(record[1],record[2],record[0],ts)
        self.topos=[wgs84.latlon(s['lat'],s['lon'],elevation_m=s['elevation_m']) for s in stations]
        self.error_samples=0;self.evaluations=0

    def elevations(self, seconds, site):
        seconds=np.atleast_1d(seconds)
        t=self.ts.tt_jd(self.epoch.whole,self.epoch.tt_fraction+seconds/86400)
        # Skyfield's direct TEME->ITRF path avoids cancelling expensive celestial
        # rotations. This validator never calls generator geometry or root helpers.
        position,_,messages=self.sat.ITRF_position_velocity_error(t)
        errors=np.array([m is not None for m in messages],bool)
        loc=self.topos[site]
        delta=position.T*AU_KM-loc.itrs_xyz.km
        lon=loc.longitude.radians;lat=loc.latitude.radians
        east=-np.sin(lon)*delta[:,0]+np.cos(lon)*delta[:,1]
        north=-np.sin(lat)*np.cos(lon)*delta[:,0]-np.sin(lat)*np.sin(lon)*delta[:,1]+np.cos(lat)*delta[:,2]
        up=np.cos(lat)*np.cos(lon)*delta[:,0]+np.cos(lat)*np.sin(lon)*delta[:,1]+np.sin(lat)*delta[:,2]
        e=np.degrees(np.arctan2(up,np.hypot(east,north)))
        errors|=~np.isfinite(e);e[errors]=np.nan
        self.error_samples+=int(errors.sum());self.evaluations+=len(seconds)
        return e

    def check(self, window):
        p=self.policy;a=float(window['start_s']);b=float(window['end_s']);site=int(window['site'])
        reasons=[];before=self.evaluations;errors_before=self.error_samples
        result=dict(status='unresolved',reasons=reasons,min_elevation_deg=None,max_elevation_deg=None,checked_samples=0,max_final_gap_s=None)
        if not np.isfinite(a+b) or a < -p.time_tolerance_s or b>self.horizon+p.time_tolerance_s or b<=a:
            reasons.append('invalid_time_range');return result
        # Boundary declarations cannot excuse non-boundary entries.
        for key,t,expected in [('start_kind',a,'planning_start'),('end_kind',b,'planning_end')]:
            kind=window.get(key)
            if kind==expected:
                if abs(t-(0 if key=='start_kind' else self.horizon))>p.time_tolerance_s:reasons.append('invalid_clipped_boundary')
            elif kind not in ('elevation_10','elevation_85'):reasons.append('unknown_boundary_kind')
        edge=self.elevations([a,b],site)
        for kind,e in zip([window.get('start_kind'),window.get('end_kind')],edge):
            if kind in ('elevation_10','elevation_85'):
                if not np.isfinite(e) or abs(e-float(kind.split('_')[1]))>p.elevation_tolerance_deg:reasons.append('boundary_residual')
        delta=min(p.boundary_probe_s,(b-a)/4)
        # Validate orientation on both sides unless another boundary is too close.
        inside=self.elevations([a+delta,b-delta],site)
        if np.any(~np.isfinite(inside)) or np.any((inside<10-p.elevation_tolerance_deg)|(inside>85+p.elevation_tolerance_deg)):reasons.append('boundary_inside_not_visible')
        for t,sign,kind in [(a,-1,window.get('start_kind')),(b,1,window.get('end_kind'))]:
            outside=t+sign*delta
            if kind in ('elevation_10','elevation_85') and 0<=outside<=self.horizon:
                e=self.elevations([outside],site)[0]
                if not np.isfinite(e):reasons.append('outside_propagation_failure')
                elif 10+p.elevation_tolerance_deg<e<85-p.elevation_tolerance_deg:reasons.append('boundary_outside_still_visible')
        n=int(np.ceil((b-a)/p.base_gap_s))+1
        if n>p.sample_budget:reasons.append('sample_budget');return result
        t=np.linspace(a,b,n);e=self.elevations(t,site);all_values=[e]
        left=t[:-1];right=t[1:];el=e[:-1];er=e[1:];max_gap=0.;unresolved=False
        for depth in range(p.max_depth):
            if not len(left):break
            if self.evaluations-before+len(left)>p.sample_budget:
                reasons.append('sample_budget');unresolved=True;break
            middle=(left+right)/2;em=self.elevations(middle,site);all_values.append(em)
            gap=right-left
            curvature=np.abs(em-(el+er)/2)
            margin=np.minimum(np.min(np.array([el,em,er])-10,axis=0),np.min(85-np.array([el,em,er]),axis=0))
            variation=np.maximum(np.abs(em-el),np.abs(er-em))
            # Long nearly flat grazing arcs do not need sub-second samples solely
            # because they are near 10 degrees. Refine where variation competes
            # with the constraint margin, or where curvature is significant.
            near_risk=(margin<p.near_constraint_deg)&(variation>np.maximum(margin,0)*.25)
            split=(curvature>p.curvature_tolerance_deg)|(near_risk&(gap>p.near_boundary_gap_s))
            if np.any((curvature>p.curvature_tolerance_deg)&(gap<=p.minimum_gap_s)):
                unresolved=True;reasons.append('curvature_at_resolution_limit')
            split&=gap>p.minimum_gap_s
            if np.any(~split):max_gap=max(max_gap,float(np.max(gap[~split]/2)))
            l=left[split];r=right[split];m=middle[split];le=el[split];re=er[split];me=em[split]
            left=np.r_[l,m];right=np.r_[m,r];el=np.r_[le,me];er=np.r_[me,re]
        if len(left) and not unresolved:unresolved=True;reasons.append('adaptive_depth_limit')
        values=np.concatenate(all_values);finite=values[np.isfinite(values)]
        if np.any(~np.isfinite(values)):reasons.append('sgp4_or_nonfinite')
        if np.any((finite<10-p.elevation_tolerance_deg)|(finite>85+p.elevation_tolerance_deg)):reasons.append('interior_elevation_violation')
        result.update(checked_samples=self.evaluations-before,propagation_error_samples=self.error_samples-errors_before,
                      min_elevation_deg=float(np.min(finite)) if len(finite) else None,max_elevation_deg=float(np.max(finite)) if len(finite) else None,
                      max_final_gap_s=max_gap,reasons=sorted(set(reasons)),status='sampled_valid' if not reasons and not unresolved else 'unresolved')
        return result
