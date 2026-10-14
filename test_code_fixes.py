import unittest,tempfile,json
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
import numpy as np
from visibility import refine_windows,refine_windows_legacy,refine_windows_optimized,NumericPolicy
from formal_cache import layer_c,manifest,atomic_json,atomic_csv,cache_ok,layer_a
from optical_validation import optical_visible,uncovered_records
from skyfield.api import load
from m1 import load_tle,load_stations

class FixTests(unittest.TestCase):
    def run_curve(self,f):
        t=np.arange(0,181,60.)
        return refine_windows(lambda t,s:f(t),t,f(t)[None,:])
    def test_single_crossing(self):
        w,a=self.run_curve(lambda t:5+t/10);self.assertFalse(a);self.assertEqual(len(w),1);self.assertAlmostEqual(w[0]['start_s'],50,places=5)
    def test_two_crossings_short_window(self):
        f=lambda t:-5+20*np.exp(-((t-30)/4)**2)
        w,a=self.run_curve(f);self.assertFalse(a);self.assertEqual(len(w),1)
        old,_=refine_windows_legacy(lambda t,s:f(t),np.arange(0,181,60.),f(np.arange(0,181,60.))[None,:])
        self.assertNotEqual(len(old),len(w))
    def test_upper_hole(self):
        f=lambda t:40+48*np.exp(-((t-30)/5)**2)
        w,a=self.run_curve(f);self.assertFalse(a);self.assertEqual(len(w),2)
        self.assertTrue(w[0]['end_s']<30<w[1]['start_s'])
    def test_high_pass_lobes_not_dropped(self):
        # Coarse maximum 63 deg never enters legacy 75..85 extrema gate.
        f=lambda t:90-.03*(t-90)**2
        t=np.arange(0,181,60.)
        old,_=refine_windows_legacy(lambda t,s:f(t),t,f(t)[None,:])
        new,a=self.run_curve(f)
        self.assertEqual(old,[]);self.assertFalse(a);self.assertEqual(len(new),2)
        self.assertEqual(new[0]['end_kind'],'elevation_85')
    def test_optimized_matches_adaptive_on_short_and_upper_hole(self):
        class SyntheticEvaluator:
            def __init__(self, function): self.function=function
            def grid(self, seconds): return self.function(np.asarray(seconds))[None,:]
            def __call__(self, seconds, sites): return self.function(np.asarray(seconds))
        for function in [
            lambda t:-5+20*np.exp(-((t-30)/4)**2),
            lambda t:40+48*np.exp(-((t-30)/5)**2),
        ]:
            times=np.arange(0,181,60.);e=function(times)[None,:]
            expected,_=refine_windows(lambda t,s:function(t),times,e)
            actual,anomalies=refine_windows_optimized(SyntheticEvaluator(function),times,e)
            self.assertFalse(anomalies);self.assertEqual(len(actual),len(expected))
            np.testing.assert_allclose(
                [(w['start_s'],w['end_s']) for w in actual],
                [(w['start_s'],w['end_s']) for w in expected],atol=1e-6,rtol=0)
    def test_nonfinite_not_erased(self):
        w,a=refine_windows(lambda t,s:20+0*t,[0,60,120],np.array([[20,np.nan,20]]));self.assertFalse(w);self.assertTrue(a)
    def test_optical_requires_night(self):
        np.testing.assert_array_equal(optical_visible(np.array([20,20,9]),np.array([0,-7,-7])),[False,True,False])
    def test_boundary_candidates_retained(self):
        r=uncovered_records(np.array([1.]),np.array([10.000001]),np.array([-7.]),[], 'x',1,datetime.now(timezone.utc))
        self.assertEqual(r[0]['classification'],'boundary_sensitive');self.assertEqual(len(r),1)
    def test_local_review_distinguishes_borderline(self):
        from optical_validation import review_uncovered
        record={'time_s':10.}
        confirmed=review_uncovered(record,lambda t:(20+0*t,-10+0*t),[],100)
        borderline=review_uncovered(record,lambda t:(10.000001+0*t,-10+0*t),[],100)
        self.assertEqual(confirmed['classification'],'confirmed_sampled_interior_gap')
        self.assertEqual(borderline['classification'],'boundary_sensitive_or_unresolved')
    def test_c_dependency_and_missing_output(self):
        with tempfile.TemporaryDirectory() as q:
            root=Path(q); inp=root/'input';inp.write_text('x')
            args=SimpleNamespace(start='2026-10-01T00:00:00Z',end='2026-10-07T00:00:00Z',step=60,time_scale='UTC',priority=str(inp))
            for name in ['A_orbit','B_night']:
                atomic_json(root/name/'manifest.json',{'source_version':'v1','algorithm':{'test':1}})
                rows=[dict(target_id='1',station_id='1',start_s=0,end_s=100)]
                atomic_csv(root/name/'windows.csv',rows,list(rows[0]))
            status,m=layer_c(args,root,[str(inp)],{},False);self.assertEqual(status,'miss')
            self.assertEqual(layer_c(args,root,[str(inp)],{},False)[0],'hit')
            a_before=(root/'A_orbit/manifest.json').read_bytes()
            atomic_json(root/'B_night/manifest.json',{'source_version':'v2','algorithm':{'test':2}})
            self.assertEqual(layer_c(args,root,[str(inp)],{},False)[0],'miss')
            self.assertEqual(a_before,(root/'A_orbit/manifest.json').read_bytes())
            (root/'C_optical/windows.csv').unlink();self.assertFalse(cache_ok(root/'C_optical',m))
    def test_target_anomalies_persist(self):
        from unittest.mock import patch
        class Ev:
            evaluations=3;error_samples=1;error_codes={'6':1};error_intervals=[{'start_s':60,'end_s':60,'code':6}]
            def __init__(self,*a):pass
            def grid(self,*a):return np.array([[20,np.nan,20.]])
            def __call__(self,t,s):return 20+0*t
        with tempfile.TemporaryDirectory() as q:
            q=Path(q);inp=q/'input';inp.write_text('x')
            args=SimpleNamespace(start='2026-10-01T00:00:00Z',end='2026-10-07T00:00:00Z',step=60,time_scale='UTC',tle=str(inp),stations=str(inp),targets=1)
            ts=load.timescale(builtin=True)
            with patch('formal_cache.OrbitEvaluator',Ev):
                layer_a(args,q,[('x','1 12345','2 12345')],[dict(id=1,lat=0,lon=0,elevation_m=0)],ts,datetime(2026,10,1,tzinfo=timezone.utc),np.array([0,60,120.]))
            s=json.loads((q/'A_orbit/target_status.json').read_text())[0]
            self.assertEqual(s['status'],'partial_propagation_failure');self.assertTrue(s['anomalies']);self.assertEqual(s['error_codes'],{'6':1})
            cases=[(3,[], 'full_propagation_failure'),(0,[{'site':0,'reason':'unreliable_root','time_s':30.}], 'refinement_failure'),(0,[], 'normal_no_window_sampled')]
            for error_count,anomalies,expected in cases:
                Ev.error_samples=error_count
                with patch('formal_cache.OrbitEvaluator',Ev),patch('formal_cache.refine_windows_optimized',return_value=([],anomalies)):
                    layer_a(args,q,[('x','1 12345','2 12345')],[dict(id=1,lat=0,lon=0,elevation_m=0)],ts,datetime(2026,10,1,tzinfo=timezone.utc),np.array([0,60,120.]),force=True)
                status=json.loads((q/'A_orbit/target_status.json').read_text())[0]
                self.assertEqual(status['status'],expected);self.assertEqual(status['anomalies'],anomalies)

if __name__=='__main__':unittest.main(verbosity=2)
