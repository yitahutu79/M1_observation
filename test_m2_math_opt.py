import unittest
from types import SimpleNamespace

from m2_math_opt_feasibility import Candidate, conflict_pairs, solve_milp


RULES = SimpleNamespace(different_target_switch_s=30.0, target_revisit_cooldown_s=172800.0)


def candidate(target, station, start, end, score):
    return Candidate(target, target, int(target), station, start, end, end-start,
                     "high", score, int(target), start, end)


class MathOptimizationModelTests(unittest.TestCase):
    def test_station_conflict_respects_mandatory_coverage(self):
        rows=[candidate("1",1,0,120,3),candidate("2",1,100,220,5)]
        pairs=conflict_pairs(rows,RULES)
        self.assertIn((0,1),pairs)
        selected,result=solve_milp(rows,pairs,{"1"},1.0)
        self.assertEqual(selected,{0})
        self.assertEqual(result["mip_gap"],0.0)

    def test_cross_station_cooldown_is_global(self):
        rows=[candidate("1",1,0,120,3),candidate("1",2,1000,1120,5)]
        pairs=conflict_pairs(rows,RULES)
        self.assertIn((0,1),pairs)
        selected,_=solve_milp(rows,pairs,set(),1.0)
        self.assertEqual(selected,{1})

    def test_exact_48_hour_boundary_is_allowed(self):
        rows=[candidate("1",1,0,120,3),candidate("1",2,172920,173040,5)]
        pairs=conflict_pairs(rows,RULES)
        self.assertNotIn((0,1),pairs)
        selected,_=solve_milp(rows,pairs,set(),1.0)
        self.assertEqual(selected,{0,1})


if __name__ == "__main__":
    unittest.main()
