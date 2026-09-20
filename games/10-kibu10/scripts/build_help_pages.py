"""Typeset four reviewed Chinese help pages from verified tenth-game sprites."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import UnityPy

import pipeline as p


WIDTH, HEIGHT = 930, 632
FONT = Path("C:/Windows/Fonts/NotoSansSC-VF.ttf")
FONT_SHA256 = "763146584cf0710223441356b4395e279021b0806c196614377a7a0174ae074a"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_help_pages(output: Path | None = None):
    spec_path = p.WORK / "images/help-pages.translation.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    bundle = p.GAME / spec["bundle"]
    if sha(bundle) != spec["bundle_sha256"]:
        raise ValueError("Tenth-game help bundle changed")
    if not FONT.is_file() or sha(FONT) != FONT_SHA256:
        raise ValueError("Locked Noto Sans SC font is unavailable or changed")
    objects = {obj.path_id: obj for obj in UnityPy.load(str(bundle)).objects}
    model = objects[spec["model_path_id"]].read_typetree()
    if [ref["m_PathID"] for ref in model["howToPlayImages"]] != [page["sprite_path_id"] for page in spec["pages"]]:
        raise ValueError("Tenth-game help page order changed")
    output = output or p.WORK / "bepinex/build/plugin/images"
    output.mkdir(parents=True, exist_ok=True)
    pages, bounds = [], []

    for index, page in enumerate(spec["pages"]):
        sprite = objects[page["sprite_path_id"]].read()
        texture = objects[page["texture_path_id"]].read()
        if sprite.m_Name != page["sprite_name"] or [texture.m_Width, texture.m_Height] != [WIDTH, HEIGHT]:
            raise ValueError("Unexpected tenth-game help source")
        image = Image.new("RGBA", (WIDTH, HEIGHT), "#50608c")
        draw = ImageDraw.Draw(image)

        def text(value, x, y, size=27, fill="white", center=False, maxwidth=850):
            font = ImageFont.truetype(str(FONT), size)
            font.set_variation_by_name("Bold")
            box = draw.textbbox((0, 0), value, font=font)
            while box[2] - box[0] > maxwidth and size > 17:
                size -= 1
                font = ImageFont.truetype(str(FONT), size)
                font.set_variation_by_name("Bold")
                box = draw.textbbox((0, 0), value, font=font)
            if box[2] - box[0] > maxwidth:
                raise ValueError("Help text exceeds width: " + value)
            if center:
                x = (WIDTH - (box[2] - box[0])) / 2 - box[0]
            y -= box[1]
            box = draw.textbbox((x, y), value, font=font)
            if box[0] < 0 or box[1] < 0 or box[2] > WIDTH or box[3] > HEIGHT:
                raise ValueError("Help text clipped: " + value)
            draw.text((x, y), value, font=font, fill=fill)
            bounds.append({"page": index + 1, "text": value, "bounds": list(box), "size": size})

        translation = page["translation"]
        if index < 2:
            if len(translation["rows"]) != 5:
                raise ValueError("Expected five control rows")
            text(translation["title"], 0, 29, 35, center=True)
            text(translation["subtitle"], 0, 76, 24, center=True)
            for row, (control, action) in enumerate(translation["rows"]):
                y = 124 + row * 60
                draw.rectangle((37, y, 445, y + 56), fill="#5a6996")
                draw.rectangle((447, y, 894, y + 56), fill="#b4b9cd")
                text(control, 54, y + 15, 25, maxwidth=374)
                text(action, 464, y + 15, 25, fill="#10131d", maxwidth=412)
        elif index == 2:
            text(translation["title"], 0, 69, 62, center=True)
            positions = [214, 255, 296, 374, 415, 493, 534]
            if len(translation["lines"]) != len(positions):
                raise ValueError("Help page 3 text count changed; layout must be reviewed")
            for value, y in zip(translation["lines"], positions):
                text(value, 0, y, 26, center=True)
        else:
            text(translation["brand"], 0, 69, 62, center=True)
            text(translation["title"], 0, 229, 37, center=True)
            positions = [316, 354, 392, 463, 501]
            if len(translation["lines"]) != len(positions):
                raise ValueError("Help page 4 text count changed; layout must be reviewed")
            for value, y in zip(translation["lines"], positions):
                text(value, 0, y, 27, center=True)

        path = output / ("help-%02d.png" % index)
        image.save(path, format="PNG", optimize=False)
        pages.append({"page": index + 1, "sprite_name": page["sprite_name"], "png": str(path),
                      "size": [WIDTH, HEIGHT], "sha256": sha(path)})

    report = {"schema": 1, "page_count": 4, "translated_pages": 4,
              "source_bundle": spec["bundle"], "source_bundle_sha256": sha(bundle),
              "translation_sha256": sha(spec_path), "pages": pages, "text_bounds": bounds,
              "font": {"name": "Noto Sans SC Variable", "sha256": sha(FONT), "distributed": False},
              "runtime_visual_tested": False}
    p.save(p.WORK / "reports/help-pages_latest.json", report)
    print("PASS: 4 Chinese help pages, all text within 930x632 bounds")
    return report


if __name__ == "__main__":
    build_help_pages()
