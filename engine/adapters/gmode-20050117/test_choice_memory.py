"""Offline shape checks for the choice-memory transpiler.

The transpiler rewrites exactly one guard per native memory loop and expects a fixed
number of menu-identity reads around it. If a game patch or a parser change alters
that shape the plugin throws at load, so the expectations are pinned here as well as
in the Cecil binding check.
"""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
ASSEMBLY = ROOT / 'games/09-samidare/research/kibu9-assembly.json'

# Mirrors NativeChoiceMemory.Rewrite: how many guards and identity reads per method.
EXPECTED = {'Game_adv': (2, 2), 'Game_command': (1, 2)}


def load():
    return json.loads(ASSEMBLY.read_text(encoding='utf-8-sig'))


def instructions(data, name):
    key = [k for k in data['methods'] if k.endswith('CanvasEx::' + name + '()')][0]
    return data['methods'][key]['il']


def guards(lines, window):
    """Yield (index, identity_reads) for every `if (komando_modori != -1) skip` guard."""
    found = []
    for index in range(len(lines) - 3):
        if not lines[index].startswith('ldfld') or 'komando_modori' not in lines[index]:
            continue
        if 'ldc.i4.m1' not in lines[index + 1]:
            continue
        if 'bne.un' not in lines[index + 2]:
            continue
        if 'ldc.i4.0' not in lines[index + 3]:
            continue
        section = lines[index + 4:index + window]
        if not any('Sentaku_kioku_id' in line for line in section):
            raise AssertionError('guard at %d does not precede the native table' % index)
        reads = sum(1 for line in section if line.startswith('ldfld') and 'CanvasEx::Pos' in line)
        found.append((index, reads))
    return found


class ChoiceMemoryTests(unittest.TestCase):
    def setUp(self):
        self.data = load()

    def test_guard_and_identity_counts(self):
        for name, (expected_guards, expected_reads) in EXPECTED.items():
            with self.subTest(method=name):
                window = 70 if name == 'Game_command' else 41
                found = guards(instructions(self.data, name), window)
                self.assertEqual(len(found), expected_guards)
                self.assertEqual(sum(reads for _, reads in found), expected_reads)

    def test_every_guard_precedes_the_native_table(self):
        # guards() raises when a guard is no longer followed by the memory table, which
        # is the condition the transpiler refuses to patch.
        for name in EXPECTED:
            with self.subTest(method=name):
                guards(instructions(self.data, name), 70 if name == 'Game_command' else 41)

    def test_transpiler_fields_exist(self):
        fields = {key.split('::')[-1] for key in self.data['fields'] if 'CanvasEx::' in key}
        for name in ('Script', 'CommandCursorPos', 'CommandTop', 'SentakuStock',
                     'komando_modori', 'Pos', 'NowCommand', 'NowChobunCommand'):
            with self.subTest(field=name):
                self.assertIn(name, fields)

    def test_menu_openers_are_plain_void_methods(self):
        # The prefix hook needs a parameterless method; a coroutine would need its
        # MoveNext instead and the captured identity would be wrong.
        for name in ('KOMANDO()', 'CHOUBUN_KOMANDO()'):
            with self.subTest(method=name):
                method = self.data['methods']['System.Void CanvasEx::' + name]
                self.assertEqual(method['instructions'] > 0, True)
        keys = [k for k in self.data['methods'] if 'CanvasEx::KOMANDO()' in k or 'CanvasEx::CHOUBUN_KOMANDO()' in k]
        self.assertEqual(len(keys), 2)


if __name__ == '__main__':
    unittest.main()
