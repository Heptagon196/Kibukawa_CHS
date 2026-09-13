"""Offline reader for the 20050117 scenario container, not a runtime adapter.

The ninth title ships its scenarios in two places:

* ``kibu9_Data/StreamingAssets/scratchpad`` TextAsset ``scratch1.dat`` holds the
  scenario set ``c1_01``..``c5_01`` together with the character and background
  graphics, ``define.bin``, ``scn0.bin`` and ``start.bin``.
* ``kibu9_Data/StreamingAssets/file`` holds the opening scenario set
  ``c0_00``/``c0_01``/``c1_00`` as standalone TextAssets.

Both use the same offset table, which is read by the shared gmode-v2 frame. What
differs from 20050817 is the table's one-byte member count and, above all, the
member payload: there is no ``FFFF`` envelope, no declared size and no
per-scenario ZIP, so a payload starts directly with its version string.

Opcode decoding, click boundaries and Chinese rendering live in ``vm.py``.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / 'gmode-v2'))
import vm_frame as frame

VERSION = b'20050117'
# scn0.bin carries its own marker and no label table or script region.
INDEX_VERSION = b'20050524'
COUNT_SIZE = 1


def require(condition, message):
    if not condition:
        raise ValueError(message)


def entries(data):
    """Split a scratch container into ordered ``(name, payload)`` pairs."""
    return frame.offset_table(data, COUNT_SIZE)


def scenario_names(data):
    """Return the ``.bin`` member names of a scratch container in order."""
    return [name for name, _ in entries(data) if name.endswith('.bin')]


def scenarios(data):
    """Return ``dict(name=..., raw=...)`` for every scenario member."""
    return [dict(name=name, raw=payload) for name, payload in entries(data) if name.endswith('.bin')]
