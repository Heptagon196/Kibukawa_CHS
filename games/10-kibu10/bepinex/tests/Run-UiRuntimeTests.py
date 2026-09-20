"""Compile the shared UI runtime with the tenth game's actual policy class."""
from pathlib import Path
import subprocess


game = Path(__file__).resolve().parents[2]
root = game.parents[1]
output = game / "bepinex/build/ui-tests/UiRuntimeTests.exe"
generated_test = output.with_suffix(".cs")
output.parent.mkdir(parents=True, exist_ok=True)

template = (root / "engine/adapters/gmode-v2/ui/tests/UiRuntimeTests.cs").read_text(encoding="utf-8")
generated_test.write_text(template.replace("Kibu8ZhCN", "Kibu10ZhCN"), encoding="utf-8")
sources = [
    generated_test,
    root / "engine/adapters/gmode-v2/ui/src/UiLocalizationRuntime.cs",
    game / "bepinex/src/UiLocalization.cs",
    game / "bepinex/src/UiLocalizationData.cs",
]
subprocess.run(
    [
        "C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe",
        "/nologo",
        "/out:" + str(output),
        *map(str, sources),
    ],
    check=True,
)
subprocess.run([str(output)], check=True)
