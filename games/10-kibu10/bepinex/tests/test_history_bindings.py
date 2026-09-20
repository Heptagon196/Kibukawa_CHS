"""Offline guards against accidentally applying coroutine hooks to bool methods."""
import json
from pathlib import Path
import unittest
GAME = Path(__file__).resolve().parents[2]
SERIES = GAME.parents[1]
class HistoryBindings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assembly = json.loads((GAME / 'research/kibu10-assembly.json').read_text(encoding='utf-8-sig'))
        cls.source = (SERIES / 'engine/adapters/gmode-20050817-direct/src/HistoryRuntime.cs').read_text()
    def test_entry_return_types_and_hooks(self):
        self.assertIn('System.Collections.IEnumerator CanvasEx::Run()', self.assembly['methods'])
        self.assertIn('Patch(type, "Run", null, "AfterScript")', self.source)
        for name in ('Game', 'Game_adv', 'Game_command'):
            self.assertIn('System.Boolean CanvasEx::' + name + '()', self.assembly['methods'])
            self.assertIn('Patch(type, "' + name + '", "BeforeDirectScript", null)', self.source)
    def test_drawn_only_capture_binding(self):
        methods = self.assembly['methods']
        self.assertIn('System.Void CanvasEx::DrawAdvString(Socotra.UI.StGraphics,System.Int32,System.Int32,System.Int32,System.Int32,System.Int32)', methods)
        for name in ('BUNSYOU', 'KeyFlush'):
            self.assertIn('System.Void CanvasEx::' + name + '()', methods)
        self.assertTrue('System.Void Socotra.UI.StCanvas::ProcessEvent(System.Int32,System.Int32)' in methods)
        fields = self.assembly['fields']
        for name in ('FrameTask', 'MainTask', 'Script', 'bg_itigyougun_mojiretu', 'bg_itigyougun_color', 'bg_itigyougun_control', 'ColorTable', 'NowNamae', 'Namae_nafuda', 'Namae_color', 'command'):
            self.assertTrue(any(key.endswith(' CanvasEx::' + name) for key in fields), name)
        self.assertTrue(any(key.endswith(' CanvasEx::phraseTrack') and 'Static' in value for key, value in fields.items()))
        self.assertTrue(any(key.endswith('::audioSource') for key in fields))
if __name__ == '__main__': unittest.main()
