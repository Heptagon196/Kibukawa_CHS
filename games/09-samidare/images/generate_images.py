"""Rebuild the ninth game's localized title artwork from verified native pixels."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import UnityPy

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
sys.path.insert(0, str(WORK / "scripts"))
import pipeline as p

TITLE = "五月雨是铅灰的旋律"
SERIES = "侦探·癸生川凌介事件谭"
MENUS = ("从头开始", "继续游戏")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def font_path() -> Path:
    lock = json.loads((HERE / "font-lock.json").read_text(encoding="utf-8"))
    path = Path(lock["path"])
    if not path.is_file() or sha(path.read_bytes()) != lock["sha256"]:
        raise RuntimeError("Locked Noto Serif SC font is unavailable or changed")
    return path


def textures() -> dict[str, Image.Image]:
    data = p.GAME / "kibu9_Data"
    env = UnityPy.load(str(data / "resources.assets"), str(data / "resources.assets.resS"))
    result = {}
    for obj in env.objects:
        if obj.type.name != "Texture2D":
            continue
        value = obj.read()
        if value.m_Name in ("title", "titleimage"):
            if value.m_Name in result:
                raise RuntimeError("Duplicate native title texture: " + value.m_Name)
            result[value.m_Name] = value.image.convert("RGBA")
    if set(result) != {"title", "titleimage"}:
        raise RuntimeError("Native title textures not found")
    return result


def cover(image: Image.Image, box: tuple[int, int, int, int], alpha: int = 255) -> None:
    veil = Image.new("RGBA", image.size, (255, 255, 255, 0))
    ImageDraw.Draw(veil).rectangle(box, fill=(255, 255, 255, alpha))
    image.alpha_composite(veil)


def centered_text(image: Image.Image, text: str, font: ImageFont.FreeTypeFont, y: int,
                  fill=(130, 130, 130, 255), shadow=1) -> None:
    draw = ImageDraw.Draw(image)
    box = draw.textbbox((0, 0), text, font=font, stroke_width=0)
    x = (image.width - (box[2] - box[0])) // 2 - box[0]
    if shadow:
        layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.text((x + 1, y + 1), text, font=font, fill=(65, 65, 65, 135))
        layer = layer.filter(ImageFilter.GaussianBlur(shadow))
        image.alpha_composite(layer)
    draw.text((x, y), text, font=font, fill=fill)


def localized_title(source: Image.Image, font_file: Path) -> Image.Image:
    if source.size != (240, 240):
        raise RuntimeError("Unexpected native title size")
    out = source.copy()
    cover(out, (20, 10, 220, 35))
    cover(out, (7, 35, 233, 75))
    cover(out, (126, 132, 232, 193))
    centered_text(out, SERIES, ImageFont.truetype(str(font_file), 8), 15,
                  fill=(128, 128, 128, 255), shadow=0)
    centered_text(out, TITLE, ImageFont.truetype(str(font_file), 23), 39,
                  fill=(129, 129, 129, 255), shadow=1)
    draw = ImageDraw.Draw(out)
    menu_font = ImageFont.truetype(str(font_file), 16)
    # PaintTitle overlays the selected 87x19 sprite at x=131, y=137/171.
    # These baselines align the normal labels to the exact rendered glyph bounds.
    draw.text((141, 133), MENUS[0], font=menu_font, fill=(178, 178, 178, 255))
    draw.text((141, 167), MENUS[1], font=menu_font, fill=(178, 178, 178, 255))
    return out


def localized_shell(source: Image.Image, font_file: Path) -> Image.Image:
    if source.size != (354, 354):
        raise RuntimeError("Unexpected native shell cover size")
    out = source.copy()
    cover(out, (15, 143, 339, 207))
    centered_text(out, TITLE, ImageFont.truetype(str(font_file), 31), 158,
                  fill=(126, 126, 126, 255), shadow=1)
    return out


def selected_menu(text: str, font_file: Path) -> Image.Image:
    out = Image.new("RGBA", (87, 19), (0, 0, 0, 0))
    font = ImageFont.truetype(str(font_file), 16)
    draw = ImageDraw.Draw(out)
    box = draw.textbbox((0, 0), text, font=font, stroke_width=1)
    x = (87 - (box[2] - box[0])) // 2 - box[0]
    y = (19 - (box[3] - box[1])) // 2 - box[1]
    draw.text((x, y), text, font=font, fill=(250, 250, 250, 255),
              stroke_width=1, stroke_fill=(108, 108, 108, 255))
    return out


def main() -> None:
    p.validate_sources()
    font_file = font_path()
    native = textures()
    outputs = {
        "title-zh.png": localized_title(native["title"], font_file),
        "titleimage-zh.png": localized_shell(native["titleimage"], font_file),
        "title-menu0-zh.png": selected_menu(MENUS[0], font_file),
        "title-menu1-zh.png": selected_menu(MENUS[1], font_file),
    }
    for name, image in outputs.items():
        image.save(HERE / name, format="PNG", optimize=False)
        print(name, image.size, sha((HERE / name).read_bytes()))


if __name__ == "__main__":
    main()
