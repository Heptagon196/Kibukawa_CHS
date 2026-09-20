"""Check every translated INFO row against Kibu10's 240px native area."""
import json
import re
import unittest
from pathlib import Path


GAME = Path(__file__).resolve().parents[2]
TAG = re.compile(r"<[^>]+>")


def character_width(value: str) -> int:
    code = ord(value)
    return 6 if code <= 0x7F or 0xFF61 <= code <= 0xFF9F else 12


class InfoWidths(unittest.TestCase):
    def test_all_active_info_rows_fit_native_area(self):
        catalog = json.loads((GAME / "work/dialogue-tagged.json").read_text(encoding="utf-8"))
        rows = [unit for unit in catalog["units"] if unit.get("active") and unit["opcode"] == 72]
        self.assertEqual(len(rows), 123)
        overflow = []
        for row in rows:
            text = TAG.sub("", row["target"])
            width = sum(character_width(value) for value in text)
            if width > 240:
                overflow.append((row["id"], width, text))
        self.assertEqual(overflow, [])

    def test_info_alignment_padding_uses_only_full_width_cells(self):
        catalog = json.loads((GAME / "work/dialogue-tagged.json").read_text(encoding="utf-8"))
        rows = [unit for unit in catalog["units"] if unit.get("active") and unit["opcode"] == 72]
        padding = re.compile(r"^<color=\d+>.*?</color><color=0>(.*?)</color>")
        invalid = []
        for row in rows:
            match = padding.match(row["target"])
            if match and " " in match.group(1):
                invalid.append((row["id"], match.group(1)))
        self.assertEqual(invalid, [])


if __name__ == "__main__":
    unittest.main()
