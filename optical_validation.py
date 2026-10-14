"""Independent optical outside checks; numerical tolerances label, never hide residuals."""
import numpy as np

def optical_visible(elevation, solar):
    return np.isfinite(elevation)&np.isfinite(solar)&(elevation>=10)&(elevation<=85)&(solar<-6)

def coverage(seconds, intervals):
    result=np.zeros(len(seconds),bool)
    for lo,hi in intervals:result|=(seconds>=lo)&(seconds<=hi)
    return result

def uncovered_records(seconds, elevation, solar, intervals, target_id, station_id, start):
    from datetime import timedelta
    uncovered=optical_visible(elevation,solar)&~coverage(seconds,intervals)
    result=[]
    for i in np.flatnonzero(uncovered):
        t=float(seconds[i]);distance=min((min(abs(t-a),abs(t-b)) for a,b in intervals),default=float('inf'))
        margin=min(float(elevation[i])-10,85-float(elevation[i]),-6-float(solar[i]))
        result.append(dict(target_id=target_id,station_id=station_id,time_s=t,utc=(start+timedelta(seconds=t)).isoformat(),
            satellite_elevation_deg=float(elevation[i]),solar_altitude_deg=float(solar[i]),constraint_margin_deg=margin,
            closest_boundary_s=distance if np.isfinite(distance) else None,
            classification='boundary_sensitive' if distance<=2e-6 or margin<=5e-5 else 'candidate_requires_local_review'))
    return result

def review_uncovered(record, evaluator, intervals, horizon):
    """Independent +/-1 second, 0.1-second probes; preserve borderline samples.

    Confirms sampled interior coverage failures, not completeness of all windows.
    """
    t=record['time_s'];q=np.unique(np.clip(t+np.arange(-10,11)*.1,0,horizon))
    el,solar=evaluator(q)
    margin=np.minimum.reduce([el-10,85-el,-6-solar])
    raw=optical_visible(el,solar)&~coverage(q,intervals)
    stable=raw&(margin>5e-5)
    adjacent=bool(np.any(stable[:-1]&stable[1:]))
    record=dict(record,local_probe_count=len(q),local_uncovered_count=int(raw.sum()),
                local_min_margin_deg=float(np.nanmin(margin)),
                classification='confirmed_sampled_interior_gap' if adjacent else 'boundary_sensitive_or_unresolved',
                local_times_s=q.tolist(),local_elevation_deg=el.tolist(),local_solar_deg=solar.tolist())
    return record
