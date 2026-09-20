"""Offline ABI assertions against the dump of the original SHA256-locked assembly."""
import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
GAME=ROOT/'games/10-kibu10'
DUMP=json.loads((GAME/'research/kibu10-assembly.json').read_text(encoding='utf-8'))

class RuntimeABI(unittest.TestCase):
    def test_original_assembly_identity(self):
        original=ROOT.parent.parent/'GmodeArchivesPlus_kibu10/kibu10_Data/Managed/Assembly-CSharp.dll'
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),DUMP['assembly_sha256'])

    def test_direct_hook_methods_exist(self):
        source=(ROOT/'engine/adapters/gmode-20050817-direct/src/DirectCanvasRuntime.cs').read_text()
        methods=re.findall(r'AccessTools.Method\(canvasType,\s*"([^"]+)"',source)
        for method in methods:
            self.assertTrue(any('CanvasEx::'+method+'(' in name for name in DUMP['methods']),method)
        for method in ('Game_adv','Game_command'):
            self.assertIn('System.Boolean CanvasEx::'+method+'()',DUMP['methods'])
        self.assertIn('System.Void CanvasEx::PaintMain_info(Socotra.UI.StGraphics)',DUMP['methods'])

    def test_shared_row_plane_fields(self):
        fields={name.split('CanvasEx::')[1]:name.split(' ')[0] for name in DUMP['fields'] if 'CanvasEx::' in name}
        for prefix in ('bg_itigyougun_','rollitigyougun_'):
            for suffix,kind in [('mojiretu','System.String[]'),('zenkakusuu','System.SByte[]'),('color','System.SByte[][]'),('rubi_index','System.Int32[][]'),('rubisuu','System.SByte[]')]:
                self.assertEqual(fields[prefix+suffix],kind)
        self.assertEqual(fields['Script'],'System.SByte[]')
        self.assertEqual(fields['Pos'],'System.Int32')

    def test_hook_argument_abi(self):
        for signature in (
            'System.String CanvasEx::StringRead()',
            'System.Void CanvasEx::DrawAdvString(Socotra.UI.StGraphics,System.Int32,System.Int32,System.Int32,System.Int32,System.Int32)',
            'System.Void CanvasEx::DrawAdvStringRoll(Socotra.UI.StGraphics,System.Int32,System.Int32,System.Int32,System.Int32,System.Int32)',
            'System.Void CanvasEx::DrawAdvNafuda(Socotra.UI.StGraphics,System.Int32,System.Int32)',
            'System.Void CanvasEx::PaintADV_text(Socotra.UI.StGraphics)',
        ): self.assertIn(signature,DUMP['methods'])

    def test_typewriter_catch_is_the_verified_infinite_loop(self):
        il=DUMP['methods']['System.Boolean CanvasEx::Game_adv()']['il']
        self.assertEqual(il[778:783],[
            'leave.s branch:781','pop ','br.s branch:780','ldc.i4.1 ','ret '
        ])
        source=(ROOT/'engine/adapters/gmode-20050817-direct/src/DirectCanvasRuntime.cs').read_text()
        self.assertNotIn('RewriteAdvanceFailure',source)
        self.assertNotIn('RecoverDirectAdvance',source)

if __name__=='__main__': unittest.main()
