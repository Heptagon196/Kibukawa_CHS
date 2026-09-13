import unittest
from pathlib import Path
from vm import parse_bin
from pagination import groups

class PaginationTests(unittest.TestCase):
    def test_actual_investigation_pages(self):
        game=Path(__file__).resolve().parents[3]/'games/08-kibu8'
        parsed=parse_bin((game/'raw/scratch3_2.dat/c2-02.bin').read_bytes())
        self.assertEqual(groups(parsed), [[1,1332,1403],[1,1544,1675]])
        # The original second page cancels to the first-page label.
        menu=next(c for c in parsed['commands'] if c['offset']==1402)
        self.assertEqual(parsed['labels'][menu['args'][-1]['value']],1331)

    def test_metadata_only_contains_direct_reciprocal_pages(self):
        game=Path(__file__).resolve().parents[3]/'games/08-kibu8'
        count=0
        for path in (game/'raw').rglob('*.bin'):
            parsed=parse_bin(path.read_bytes());by_offset={c['offset']:c for c in parsed['commands']}
            for group in groups(parsed):
                count+=1
                self.assertNotIn(parsed['labels'][group[0]]+1,group[1:])
                for start in group[1:]:
                    self.assertIn(by_offset[start-1]['name'],('KOMANDO','CHOUBUN_KOMANDO'))
        self.assertGreaterEqual(count,8)
