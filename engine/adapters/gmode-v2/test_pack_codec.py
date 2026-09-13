import unittest

import pack_codec


class ScriptSlotIdentityTests(unittest.TestCase):
    def entry(self, instruction, source='　', slot=1):
        return dict(script='c0_00', instruction=instruction, slot=slot, opcode=255,
                    source=source, target='　')

    def test_repeated_source_at_different_instructions_is_allowed(self):
        pack = pack_codec.make_script_pack(
            [self.entry(100), self.entry(200)], 'assembly', 'scratch',
            [dict(source='戻る', target='返回')])
        self.assertEqual(2, len(pack['scripts']))

    def test_same_instruction_and_slot_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate translation slot'):
            pack_codec.make_script_pack(
                [self.entry(100), self.entry(100, source='別の原文')],
                'assembly', 'scratch', [dict(source='戻る', target='返回')])


if __name__ == '__main__':
    unittest.main()
