import unittest
from datetime import datetime,timezone
import numpy as np
from skyfield.api import load
from m1 import load_tle,load_stations
from visibility import NumericPolicy,Geometry,OrbitEvaluator,refine_windows,coarse_windows
from validator import IndependentValidator

class SyntheticTests(unittest.TestCase):
    def windows(self,f,end=180):
        t=np.arange(0,end+1,15.)
        def evaluate(seconds,sites):return f(np.asarray(seconds))
        return refine_windows(evaluate,t,f(t)[None,:])

    def test_two_constraints_and_internal_split(self):
        # 95-degree maximum puts an invisible hole between two visible intervals.
        f=lambda t:95-.02*(t-90)**2
        w,a=self.windows(f)
        self.assertEqual(a,[]);self.assertEqual(len(w),2)
        for item in w:
            self.assertTrue(np.all((f(np.linspace(item['start_s']+.00001,item['end_s']-.00001,100))>=10)&(f(np.linspace(item['start_s']+.00001,item['end_s']-.00001,100))<=85)))
        self.assertEqual(w[0]['end_kind'],'elevation_85');self.assertEqual(w[1]['start_kind'],'elevation_85')

    def test_short_grazing_windows_missed_by_both_grids(self):
        for duration in [0.2,1,3,10,25,45]:
            with self.subTest(duration=duration):
                f=lambda t:10+.005*((duration/2)**2-(t-67.3)**2)
                w,a=self.windows(f);self.assertEqual(a,[]);self.assertEqual(len(w),1)
                self.assertAlmostEqual(w[0]['end_s']-w[0]['start_s'],duration,places=4)
                coarse_t=np.arange(0,181,60.)
                if duration<10:self.assertEqual(coarse_windows(coarse_t,f(coarse_t)[None,:],NumericPolicy()),[])

    def test_upper_hole_hidden_between_discovery_samples(self):
        f=lambda t:84+2*np.exp(-((t-67.3)/3)**2)
        self.assertTrue(np.all(f(np.arange(0,181,15.))<85))
        w,a=self.windows(f)
        self.assertEqual(a,[]);self.assertEqual(len(w),2)
        self.assertEqual(w[0]['end_kind'],'elevation_85')
        self.assertEqual(w[1]['start_kind'],'elevation_85')

    def test_lower_hole_hidden_between_discovery_samples(self):
        f=lambda t:10.2-.5*np.exp(-((t-67.3)/3)**2)
        self.assertTrue(np.all(f(np.arange(0,181,15.))>10))
        w,a=self.windows(f)
        self.assertEqual(a,[]);self.assertEqual(len(w),2)
        self.assertEqual(w[0]['end_kind'],'elevation_10')
        self.assertEqual(w[1]['start_kind'],'elevation_10')

    def test_failure_is_quarantined(self):
        f=lambda t:20+0*t
        t=np.arange(0,181,15.);e=f(t);e[5]=np.nan
        w,a=refine_windows(lambda x,s:f(x),t,e[None,:]);self.assertEqual(w,[]);self.assertTrue(a)

    def test_nonfinite_during_root_not_legal(self):
        t=np.arange(0,181,15.);f=lambda t:t/3
        def broken(t,s):return np.full_like(t,np.nan)
        w,a=refine_windows(broken,t,f(t)[None,:]);self.assertEqual(w,[]);self.assertTrue(a)

    def test_planning_clip_and_tangent(self):
        w,a=self.windows(lambda t:20+0*t)
        self.assertEqual((w[0]['start_s'],w[0]['end_s']),(0,180))
        w,a=self.windows(lambda t:10-.01*(t-67.3)**2)
        self.assertEqual(w,[])

    def test_resolution_exhaustion_is_quarantined(self):
        p=NumericPolicy(max_iterations=1)
        t=np.arange(0,181,15.);f=lambda t:t/3
        w,a=refine_windows(lambda t,s:f(t),t,f(t)[None,:],p)
        self.assertEqual(w,[]);self.assertTrue(a)

class OrbitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ts=load.timescale(builtin=True);cls.start=datetime(2026,8,3,tzinfo=timezone.utc)
        cls.stations=load_stations('data/站址.txt');cls.record=load_tle('data/轨道.txt')[0][30]
        cls.geometry=Geometry(cls.ts,cls.start,cls.stations)

    def test_independent_geometry_agreement(self):
        ev=OrbitEvaluator(self.record,self.geometry);t=np.arange(0,86401,600.)
        elev=ev.grid(t);validator=IndependentValidator(self.record,self.ts,self.start,self.stations,86400)
        for s in range(10):
            np.testing.assert_allclose(elev[s],validator.elevations(t,s),atol=1e-7,rtol=0)
            full=(validator.sat-validator.topos[s]).at(self.geometry.times(t)).altaz()[0].degrees
            np.testing.assert_allclose(full,validator.elevations(t,s),atol=1e-7,rtol=0)

    def test_validator_rejects_interior_hole_and_bad_ranges(self):
        v=IndependentValidator(self.record,self.ts,self.start,self.stations,180)
        v.elevations=lambda t,s:95-.02*(np.asarray(t)-90)**2
        root=np.sqrt(85/.02)
        result=v.check(dict(site=0,start_s=90-root,end_s=90+root,start_kind='elevation_10',end_kind='elevation_10'))
        self.assertEqual(result['status'],'unresolved');self.assertIn('interior_elevation_violation',result['reasons'])
        self.assertEqual(v.check(dict(site=0,start_s=-1,end_s=10))['status'],'unresolved')

    def test_validator_rejects_finite_sgp4_error(self):
        from skyfield.positionlib import Geocentric
        v=IndependentValidator(self.record,self.ts,self.start,self.stations,180)
        original_at=v.sat.ITRF_position_velocity_error
        def failed(t):
            r,vel,messages=original_at(t)
            return r,vel,['satellite has decayed']*len(t.whole)
        v.sat.ITRF_position_velocity_error=failed
        self.assertTrue(np.all(np.isnan(v.elevations([0,1],0))))

if __name__=='__main__':unittest.main(verbosity=2)
