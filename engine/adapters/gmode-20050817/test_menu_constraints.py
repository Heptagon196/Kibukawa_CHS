import unittest
from menu_constraints import short_choice_offsets

class MenuConstraintsTests(unittest.TestCase):
    def test_only_short_menu_choices_and_color_commands_do_not_reset_mode(self):
        names=['SENTAKUSI','KOMANDO','SENTAKUSI','KOMANDO_SYOKU','SENTAKUSI','CHOUBUN_KOMANDO','SENTAKUSI','KOMANDO','SENTAKUSI','JIYUU_KOMANDO','SENTAKUSI','ICON_KOMANDO','SENTAKUSI']
        commands=[dict(name=name,offset=i) for i,name in enumerate(names)]
        self.assertEqual(list(short_choice_offsets(commands)),[2,4,8])
