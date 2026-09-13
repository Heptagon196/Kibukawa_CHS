"""Compile production UI runtime + game policy with recording-free platform doubles."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[5]
game = root/'games/08-kibu8'
out = game/'bepinex/build/ui-tests/UiRuntimeTests.exe'
out.parent.mkdir(parents=True, exist_ok=True)
sources = [Path(__file__).with_name('UiRuntimeTests.cs'), root/'engine/adapters/gmode-v2/ui/src/UiLocalizationRuntime.cs', game/'bepinex/src/UiLocalization.cs', game/'bepinex/src/UiLocalizationData.cs']
subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/out:'+str(out),*map(str,sources)],check=True)
subprocess.run([str(out)],check=True)
