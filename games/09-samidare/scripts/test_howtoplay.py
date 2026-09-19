from __future__ import annotations

import hashlib
import json
import unittest

import UnityPy

import pipeline as p


SPEC = p.WORK / "images/help-pages.translation.json"


class HowToPlayTests(unittest.TestCase):
    def test_all_native_pages_have_complete_chinese_content(self) -> None:
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        bundle = p.GAME / spec["bundle"]
        self.assertEqual(hashlib.sha256(bundle.read_bytes()).hexdigest(), spec["bundle_sha256"])
        objects = {obj.path_id: obj for obj in UnityPy.load(str(bundle)).objects}
        model = objects[spec["model_path_id"]].read_typetree()
        self.assertEqual([ref["m_PathID"] for ref in model["howToPlayImages"]],
                         [page["sprite_path_id"] for page in spec["pages"]])
        self.assertEqual(len(spec["pages"]), 4)
        for index, page in enumerate(spec["pages"]):
            sprite = objects[page["sprite_path_id"]].read_typetree()
            texture = objects[page["texture_path_id"]].read()
            self.assertEqual(sprite["m_Name"], page["sprite_name"])
            self.assertEqual([texture.m_Width, texture.m_Height], [930, 632])
            translated = page["translation"]
            self.assertTrue(translated["title"])
            if index < 2:
                self.assertEqual(len(translated["rows"]), 7)
                self.assertEqual(len(translated["footer"]), 2)
            else:
                self.assertGreaterEqual(len(translated["lines"]), 5)


if __name__ == "__main__":
    unittest.main()
