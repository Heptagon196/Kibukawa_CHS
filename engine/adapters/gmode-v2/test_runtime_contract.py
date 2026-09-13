"""Check the shared rendering seam against inspected, shipped 8/9 assemblies."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]

class RuntimeContractTests(unittest.TestCase):
    def test_shipped_graphics_contract(self):
        snapshots = []
        for game in (8, 9):
            data = json.loads((ROOT / f'games/08-kibu8/research/kibu{game}-assembly.json').read_text(encoding='utf-8-sig'))
            dll = ROOT.parent.parent / f'GmodeArchivesPlus_kibu{game}/kibu{game}_Data/Managed/Assembly-CSharp.dll'
            self.assertEqual(hashlib.sha256(dll.read_bytes()).hexdigest(), data['assembly_sha256'])
            snapshots.append(data)
            for field in ('Socotra.UI.StFont Socotra.UI.StGraphics::currentFont', 'UnityEngine.RenderTexture Socotra.UI.StGraphics::renderTexture', 'UnityEngine.Color Socotra.UI.StGraphics::currentColor', 'UnityEngine.Font Socotra.UI.StFont::font'):
                self.assertIn(field, data['fields'])
            for method in ('System.Single Socotra.UI.StFont::get_Size()', 'System.Void Socotra.UI.StGraphics::RenderStart()', 'System.Void Socotra.UI.StGraphics::RenderEnd()'):
                self.assertIn(method, data['methods'])
        for method in ('System.Void Socotra.UI.StGraphics::DrawCharImpl(System.Char[],System.Int32,System.Int32)', 'System.Void Socotra.UI.StGraphics::DrawString(System.String,System.Int32,System.Int32)', 'System.Void Socotra.UI.StGraphics::DrawChars(System.Char[],System.Int32,System.Int32,System.Int32,System.Int32)'):
            self.assertEqual(snapshots[0]['methods'][method]['sha256'], snapshots[1]['methods'][method]['sha256'])
        # Different native lifecycles must remain native; shared code invokes each pair.
        for method in ('RenderStart', 'RenderEnd'):
            key = f'System.Void Socotra.UI.StGraphics::{method}()'
            self.assertNotEqual(snapshots[0]['methods'][key]['sha256'], snapshots[1]['methods'][key]['sha256'])

if __name__ == '__main__':
    unittest.main()
