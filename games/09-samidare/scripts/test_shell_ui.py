from __future__ import annotations

import json
import struct
import unittest
from pathlib import Path

import UnityPy


ROOT = Path(__file__).resolve().parents[1]
GAME_DIR = ROOT.parents[2].parent / "GmodeArchivesPlus_kibu9"
RESOURCES_ASSET = GAME_DIR / "kibu9_Data" / "resources.assets"
MAPPING_FILE = ROOT / "work" / "shell-ui-localization.zh-CN.json"
KEYED_MAPPING_FILE = ROOT / "work" / "ui-localization.zh-CN.json"


def aligned_utf8_strings(data: bytes, minimum_length: int = 2) -> set[str]:
    strings: set[str] = set()
    for offset in range(0, len(data) - 4, 4):
        length = struct.unpack_from("<I", data, offset)[0]
        if length < minimum_length or length > len(data) - offset - 4:
            continue
        payload = data[offset + 4 : offset + 4 + length]
        try:
            value = payload.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if "\x00" not in value and any("\u3040" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff" for c in value):
            strings.add(value)
    return strings


def title_model_strings() -> set[str]:
    environment = UnityPy.load(str(RESOURCES_ASSET))
    for obj in environment.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        raw = obj.get_raw_data()
        if b"TitleDataModel" in raw:
            return aligned_utf8_strings(raw)
    raise AssertionError("TitleDataModel was not found in resources.assets")


class ShellUiLocalizationTests(unittest.TestCase):
    def test_homepage_metadata_is_covered(self) -> None:
        sources = title_model_strings()
        expected_fragments = {
            "探偵・癸生川凌介事件譚",
            "五月雨は鈍色の調べ",
            "ジャンル：推理アドベンチャー",
            "8年前の癸生川探偵事務所、もうひとりの名探偵。",
        }
        for fragment in expected_fragments:
            self.assertTrue(any(fragment in source for source in sources), fragment)

        self.assertTrue(MAPPING_FILE.is_file(), f"missing {MAPPING_FILE}")
        mappings = json.loads(MAPPING_FILE.read_text(encoding="utf-8"))
        translated_sources = {entry["source"] for entry in mappings["entries"]}
        self.assertTrue(sources <= translated_sources, f"untranslated TitleDataModel strings: {sources - translated_sources}")

    def test_player_facing_serialized_labels_are_covered(self) -> None:
        shell = json.loads(MAPPING_FILE.read_text(encoding="utf-8"))["entries"]
        keyed = json.loads(KEYED_MAPPING_FILE.read_text(encoding="utf-8"))["entries"]
        translated_sources = {entry["source"] for entry in shell + keyed}
        expected = {
            "あそびかた", "いいえ", "はい", "ウィンドウ設定", "ゲームを終了する",
            "タイトルに戻る", "フィルタ", "フルスクリーン", "フレーム", "プレイヤー名",
            "ランキング", "ランキングを取得する", "入力して下さい", "操作説明", "決定",
            "閉じる", "＜ゲーム画面＞", "終了", "文字装飾あり", "文字装飾なし",
            "失敗しました｡ 　　　", "■　データ確認中…　■",
            "本ゲームはオートセーブに対応しておりません。\r\n終了する際は、ゲーム内のセーブ機能をご利用ください。",
        }
        self.assertTrue(expected <= translated_sources, f"untranslated serialized UI: {expected - translated_sources}")


if __name__ == "__main__":
    unittest.main()
