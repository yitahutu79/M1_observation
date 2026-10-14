import csv, json, tempfile, unittest
from pathlib import Path
from formal_cache import parse_priority, manifest, cache_ok

class FormalCacheTests(unittest.TestCase):
    def test_priority_zip_counts_and_ids(self):
        p=parse_priority(Path(__file__).parent/'data/优先级.zip')
        self.assertEqual(len(p),10000);self.assertEqual({p.values().__iter__().__next__()}|set(p.values()),{'high','medium','low'})
    def test_manifest_hit_and_invalidation(self):
        class A: pass
        a=A();a.start='2026-10-01T00:00:00Z';a.end='2026-10-07T00:00:00Z';a.time_scale='UTC';a.step=60; a.tle='data/轨道.txt';a.stations='data/站址.txt';a.targets=1
        with tempfile.TemporaryDirectory() as q:
            q=Path(q);(q/'windows.csv').write_text('header\n');m=manifest('X',a,['data/轨道.txt']);(q/'manifest.json').write_text(json.dumps(m));self.assertTrue(cache_ok(q,m));a.step=30;m2=manifest('X',a,['data/轨道.txt']);self.assertFalse(cache_ok(q,m2))
    def test_atomic_outputs_are_regular_files(self):
        from formal_cache import atomic_json
        with tempfile.TemporaryDirectory() as q:
            p=Path(q)/'x.json';atomic_json(p,{'ok':1});self.assertEqual(json.loads(p.read_text())['ok'],1)

if __name__=='__main__':unittest.main()
