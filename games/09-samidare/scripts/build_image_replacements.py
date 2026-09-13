"""Build the ninth game's verified title and menu image replacement package."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time

from PIL import Image
import UnityPy

import pipeline as p

sys.path.insert(0, str(p.SERIES / "engine/bepinex"))
import build as shared


def rgba_payload(image: Image.Image) -> bytes:
    rgba = image.convert("RGBA")
    return b"KMAP" + struct.pack("<ii", *rgba.size) + rgba.tobytes()


def native_textures() -> dict[str, dict]:
    data = p.GAME / "kibu9_Data"
    env = UnityPy.load(str(data / "resources.assets"), str(data / "resources.assets.resS"))
    result = {}
    for obj in env.objects:
        if obj.type.name != "Texture2D":
            continue
        value = obj.read()
        if value.m_Name not in ("title", "titleimage"):
            continue
        if value.m_Name in result:
            raise ValueError("Duplicate native title texture: " + value.m_Name)
        image = value.image.convert("RGBA")
        result[value.m_Name] = dict(path_id=obj.path_id, size=list(image.size),
            source_data_sha256=p.sha(bytes(value.get_image_data())),
            source_rgba_sha256=p.sha(image.tobytes()))
    p.require(set(result) == {"title", "titleimage"}, "Native title textures are incomplete")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=p.WORK / "images/replacements.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8-sig"))
    if spec.get("schema") != 1 or spec.get("game") != "kibu9":
        raise ValueError("Wrong image replacement specification")

    manifest = p.validate_sources()
    before = p.game_hashes()
    image_root = args.spec.resolve().parent
    output = args.output or p.WORK / "out" / ("images_" + time.strftime("%Y%m%d_%H%M%S"))
    output = p.inside(output)
    package = output / "package"
    plugin = package / "BepInEx/plugins/KibukawaImageReplacements"
    (plugin / "images").mkdir(parents=True, exist_ok=True)

    assets = p.bundle_text_assets("kibu9_Data/StreamingAssets/scratchpad")
    p.require("scratch1.dat" in assets, "Missing scratch1.dat TextAsset")
    scratch = dict(p.entries(assets["scratch1.dat"]))
    native = native_textures()

    assembly = p.GAME / "kibu9_Data/Managed/Assembly-CSharp.dll"
    scratchpad = p.GAME / "kibu9_Data/StreamingAssets/scratchpad"
    lines = ["\t".join(("KIMG1", "kibu9", p.sha(assembly.read_bytes()), p.sha(scratchpad.read_bytes())))]
    ids, routes, entries = set(), set(), []
    for entry in spec["images"]:
        ident = entry["id"]
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", ident) or ident in ids:
            raise ValueError("Invalid or duplicate image id: " + ident)
        ids.add(ident)
        png = (image_root / entry["png"]).resolve()
        if not png.is_relative_to(image_root):
            raise ValueError("Image path escapes image root")
        image = Image.open(png).convert("RGBA")
        if list(image.size) != entry["size"]:
            raise ValueError("Replacement dimensions mismatch: " + ident)
        payload = rgba_payload(image)
        relative = "images/" + ident + ".rgba"
        (plugin / relative).write_bytes(payload)
        shutil.copyfile(png, plugin / "images" / (ident + ".png"))
        for route in entry["sources"]:
            loader, name = route["loader"], route["name"]
            if loader != "LoadGraphic" or not name or any(c in name for c in "\t\r\n@"):
                raise ValueError("Invalid ninth-game image route")
            if "." not in name:
                name += ".gif"
            p.require(name in scratch, "Native scratch image route absent: " + name)
            original = Image.open(io.BytesIO(scratch[name])).convert("RGBA")
            p.require(list(original.size) == entry["size"], "Native image dimensions changed: " + name)
            key = "CanvasEx.LoadGraphic#*@" + name
            if key in routes:
                raise ValueError("Duplicate named image route")
            routes.add(key)
            lines.append("\t".join((ident, key, "0", relative, p.sha(payload))))
            entries.append(dict(id=ident, route=key, size=list(image.size),
                source_name=name, source_data_sha256=p.sha(scratch[name]),
                source_rgba_sha256=p.sha(original.tobytes()),
                png_sha256=p.sha(png.read_bytes()), payload_sha256=p.sha(payload)))
    p.require(routes, "No named image routes")
    (plugin / "image-replacements.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    title_spec = spec["title"]
    title_png = (image_root / title_spec["png"]).resolve()
    title = Image.open(title_png).convert("RGBA")
    p.require(list(title.size) == title_spec["size"] == native["title"]["size"], "Title dimensions changed")
    title_payload = rgba_payload(title)
    (plugin / "title-background.rgba").write_bytes(title_payload)
    shutil.copyfile(title_png, plugin / "images/title.png")

    cover = (image_root / spec["shellCover"]).resolve()
    p.require(cover.is_relative_to(image_root), "Shell cover path escapes image root")
    p.require(Image.open(cover).size == (354, 354) and native["titleimage"]["size"] == [354, 354],
              "Shell cover dimensions changed")
    shutil.copyfile(cover, plugin / "titleimage-zh.png")

    source_files = [
        p.GAME / "kibu9_Data/resources.assets",
        p.GAME / "kibu9_Data/resources.assets.resS",
        p.GAME / "kibu9_Data/globalgamemanagers.assets",
        scratchpad,
    ]
    (plugin / "image-sources.sha256").write_text("".join(
        p.sha(path.read_bytes()) + "  " + path.relative_to(p.GAME).as_posix() + "\n"
        for path in source_files), encoding="utf-8")

    profile = p.load(p.SERIES / "engine/bepinex/profiles/mono-win-x64-5.4.23.5.json")
    framework, _ = shared.ensure_framework(p.SERIES / "engine/bepinex/locks" / profile["lock"],
        p.SERIES / "cache/bepinex/mono-win-x64-5.4.23.5")
    common = p.SERIES / "engine/image-replacements"
    sources = [
        p.SERIES / "engine/adapters/gmode-v2/src/NamedImageRuntime.cs",
        common / "ReplacementManifest.cs",
        common / "TextureReplacement.cs",
        p.WORK / "bepinex/src/ImageReplacementPlugin.cs",
        p.WORK / "bepinex/images/TitleBackground.cs",
        p.WORK / "bepinex/images/ShellCover.cs",
    ]
    refs = ["mscorlib.dll", "System.dll", "System.Core.dll", "netstandard.dll", "UnityEngine.dll",
            "UnityEngine.CoreModule.dll", "UnityEngine.UI.dll", "UnityEngine.ImageConversionModule.dll"]
    dll = plugin / "KibukawaImageReplacements.dll"
    shared.compile_plugin(framework, p.GAME / "kibu9_Data/Managed", dll, sources,
                          output / "compile.rsp", refs)
    validation = subprocess.run([p.shell(), "-NoProfile", "-File", str(p.WORK / "scripts/validate_images.ps1"),
        "-PluginDll", str(dll), "-GameDll", str(assembly), "-ReportPath", str(output / "bindings.json")],
        check=True, capture_output=True, text=True)
    print(validation.stdout.strip())
    subprocess.run([p.shell(), "-NoProfile", "-File",
                    str(p.SERIES / "games/08-kibu8/bepinex/tests/Run-ImageLifetimeTests.ps1")], check=True)

    report = dict(schema=1, game="kibu9", version="1.0.0", package=str(package), entries=entries,
        title=dict(source=native["title"], png_sha256=p.sha(title_png.read_bytes()),
                   payload_sha256=p.sha(title_payload)),
        shell_cover=dict(source=native["titleimage"], png_sha256=p.sha(cover.read_bytes())),
        generation="images/generate_images.py with images/font-lock.json",
        runtime_visual_tested=False, binding_test=validation.stdout.strip(),
        source_hashes={path.relative_to(p.SERIES).as_posix(): p.sha(path.read_bytes()) for path in sources},
        package_files={path.relative_to(package).as_posix(): p.sha(path.read_bytes())
                       for path in package.rglob("*") if path.is_file()},
        original_game_unchanged=before == p.game_hashes())
    p.require(report["original_game_unchanged"], "Game changed during image build")
    p.save(output / "build-report.json", report)
    p.save(p.WORK / "reports/images_latest.json", report)
    print("PASS: built ninth-game image replacement package: " + str(package))


if __name__ == "__main__":
    main()
