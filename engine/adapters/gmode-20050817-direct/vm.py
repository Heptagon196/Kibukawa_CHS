"""Direct-bin 20050817 variant. Reuse eighth-game row decoding without mutations."""
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / 'gmode-20050817/vm.py'
_spec = importlib.util.spec_from_file_location('_gmode_20050817_base', _path)
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
frame = base.frame
VERSION = base.VERSION

# CanvasEx.Game_adv's two switches, excluding default/no-operation cases.
NAMES = {k: v for k, v in base.NAMES.items()
         if k <= 75 or k in (240, 248, 250, 255)}
NAMES.pop(80, None)
NAMES.update({73: 'SABUTAITORU', 76: 'SINARIOSENTAKU'})
FORMATS = dict(base.FORMATS)
FORMATS.update({5: 'h', 73: 'Bs', 76: ''})


def _background(reader, command, read):
    # Tenth-game HAIKEI_SETTI has only the flag and conditional filename.
    if read('B') == 1:
        read('s')


SPECIAL = {k: v for k, v in base.SPECIAL.items() if k in NAMES and k != 5}
SPECIAL[40] = _background


def parse_bin(raw, codec='cp932'):
    labels, script, start = frame.split_script(raw, VERSION)
    commands = frame.parse_commands(script, NAMES, FORMATS, SPECIAL, codec, with_rows=True)
    frame.validate_labels(labels, commands, len(script))
    return dict(script_offset=start, labels=labels, commands=commands, script_size=len(script))


def entries(data):
    return frame.offset_table(data, 1)
