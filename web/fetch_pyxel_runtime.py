"""Download the pinned Pyxel/Pyodide web runtime used by operation-check-2."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "vendor" / "pyxel-2.9.6"

PYXEL_BASE = "https://raw.githubusercontent.com/kitao/pyxel/v2.9.6/wasm/"
PYODIDE_BASE = "https://cdn.jsdelivr.net/pyodide/v314.0.0/full/"

FILES = {
    "unifont-16.0.04.hex.gz": (
        "https://ftp.gnu.org/gnu/unifont/unifont-16.0.04/"
        "unifont_all-16.0.04.hex.gz"
    ),
    "pyxel.js": PYXEL_BASE + "pyxel.js",
    "pyxel.css": PYXEL_BASE + "pyxel.css",
    "import_hook.py": PYXEL_BASE + "import_hook.py",
    "pyxel-2.9.6-cp311-abi3-emscripten_5_0_3_wasm32.whl": (
        PYXEL_BASE + "pyxel-2.9.6-cp311-abi3-emscripten_5_0_3_wasm32.whl"
    ),
    "images/pyxel_icon_64x64.ico": PYXEL_BASE + "images/pyxel_icon_64x64.ico",
    "images/pyxel_logo_76x32.png": PYXEL_BASE + "images/pyxel_logo_76x32.png",
    "images/touch_to_start_114x14.png": PYXEL_BASE + "images/touch_to_start_114x14.png",
    "images/click_to_start_114x14.png": PYXEL_BASE + "images/click_to_start_114x14.png",
    "images/gamepad_cross_98x98.png": PYXEL_BASE + "images/gamepad_cross_98x98.png",
    "images/gamepad_button_98x98.png": PYXEL_BASE + "images/gamepad_button_98x98.png",
    "images/gamepad_menu_92x26.png": PYXEL_BASE + "images/gamepad_menu_92x26.png",
    "pyodide.js": PYODIDE_BASE + "pyodide.js",
    "pyodide.asm.mjs": PYODIDE_BASE + "pyodide.asm.mjs",
    "pyodide.asm.wasm": PYODIDE_BASE + "pyodide.asm.wasm",
    "python_stdlib.zip": PYODIDE_BASE + "python_stdlib.zip",
    "pyodide-lock.json": PYODIDE_BASE + "pyodide-lock.json",
}

SHA256 = {
    "unifont-16.0.04.hex.gz": "20e8b505f602488697979eefc69857f7f6106bceab702f5ac559f4f84e0e7494",
    "pyxel.js": "1c7ff392e4d86c5638dcd30275a2bafcc9ffa4115f39cc94a38cb5a8f1225fd3",
    "pyxel.css": "db758aca69b4e0cac875022ba9b4a031a98e2f45f1774cf709016edb5f1427a7",
    "import_hook.py": "4c71efd32b2c17828a88f8995b2d246eb74240b242d10f959c67d7f91f656c15",
    "pyxel-2.9.6-cp311-abi3-emscripten_5_0_3_wasm32.whl": "31af21f1a9b0a8937fc00cc6bfa77ad5f66c1383c7d244cc3a847939fb32b183",
    "images/pyxel_icon_64x64.ico": "62280f322d64fc702441b5216477c5b5b3f3045916eb3936e88ddd37d8dda02c",
    "images/pyxel_logo_76x32.png": "4272ab5584a292162215b4db039ac028b362a05c8d53077e315ff3e3409786d3",
    "images/touch_to_start_114x14.png": "fb7b2c53cb9cb72ef1921094cd375723e64feed3a1b8d4d12c96694847d7305a",
    "images/click_to_start_114x14.png": "05eaccb3b2d44225b3b8b90657d664c07abfe495336c7a8af50049886383f48c",
    "images/gamepad_cross_98x98.png": "cf97365abfe0a9d4221e4300c21040fb0640fd4e18c4a5ef5a40bcb2e02a9b7e",
    "images/gamepad_button_98x98.png": "d5e3a83196ec9c5cdf953825c6b7b416f9a9c54921554578e2de3d1d5bb6d9d5",
    "images/gamepad_menu_92x26.png": "33a576bf3e6e4f0ca3dba491d86ed66c8e983dabc43a59a4e3338ba33f354309",
    "pyodide.js": "bb1105d77fde118fb0a8b05d688cb8c3a86c7cb0a2ff01d3e289744a5eed33f9",
    "pyodide.asm.mjs": "7808c4d7a9fee23a02b0c8b7bbd51b1358e8d41bbe89e5c0ee9c0c4db7b9328f",
    "pyodide.asm.wasm": "4d23bd074cc536a96660c9168e223e3aaf01944096ad829737a9c87fec4b28eb",
    "python_stdlib.zip": "1215cd239a270c13a3ecb1a84c84b7b3241baf7ea7f54615f00d79ff69c82787",
    "pyodide-lock.json": "f545248ab161ead36adf7110a358334974e97b08f40c7219e97077d380f7247b",
}


def download(url: str, attempts: int = 5) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Kibukawa-CHS-builder/1.0"})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except OSError:
            if attempt == attempts:
                raise
            time.sleep(attempt * 2)
    raise RuntimeError("unreachable")


def main() -> None:
    results = []
    for relative_path, url in FILES.items():
        destination = OUTPUT / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            current = hashlib.sha256(destination.read_bytes()).hexdigest()
            if current != SHA256[relative_path]:
                destination.unlink()
        if not destination.exists():
            print(f"Downloading {relative_path}...")
            destination.write_bytes(download(url))
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if digest != SHA256[relative_path]:
            raise ValueError(f"SHA-256 mismatch for {relative_path}: {digest}")
        results.append(
            {
                "path": relative_path,
                "url": url,
                "size": destination.stat().st_size,
                "sha256": digest,
            }
        )
        print(f"{digest}  {relative_path}")

    (OUTPUT / "runtime-manifest.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
