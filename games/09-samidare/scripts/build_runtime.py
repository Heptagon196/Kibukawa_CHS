"""Compile the ninth-game Chinese runtime against the real game assembly.

Compile-only: it never installs, never launches the game and never writes into the
installation. Packaging needs the translation pack and the Chinese atlas, which are
built separately; this entry exists so the runtime can be type-checked and its
reflection contract verified offline before either exists.
"""
import sys
import time
from pathlib import Path

import pipeline as p

sys.path.insert(0, str(p.SERIES / 'engine/bepinex'))
import build as shared

SOURCES = [
    'engine/core/TranslationPackReader.cs',
    'engine/core/TranslationCatalog.cs',
    'engine/adapters/gmode-v2/src/BitmapFontAtlas.cs',
    'engine/adapters/gmode-v2/src/LegacyFontRenderer.cs',
    'engine/adapters/gmode-v2/src/MenuMemory.cs',
    'engine/adapters/gmode-20050117/RuntimePack.cs',
    'engine/adapters/gmode-20050117/src/NativeChoiceMemory.cs',
    'engine/adapters/gmode-20050117/src/CanvasRuntime.cs',
    'games/09-samidare/bepinex/src/Plugin.cs',
]


def main():
    p.validate_sources()
    config = p.load(p.WORK / 'project.json')
    bepinex = config['bepinex']
    profile = p.load(p.SERIES / 'engine/bepinex/profiles' / (bepinex['profile'] + '.json'))
    p.require(profile['backend'] == 'mono' and profile['architecture'] == 'x64'
              and profile['platform'] == 'windows', 'Unsupported profile')
    framework, dependency = shared.ensure_framework(p.SERIES / 'engine/bepinex/locks' / profile['lock'],
                                                    p.SERIES / 'cache/bepinex' / bepinex['profile'])
    output = p.inside(p.WORK / 'bepinex/build/plugin')
    output.mkdir(parents=True, exist_ok=True)
    sources = [p.SERIES / name for name in SOURCES]
    for source in sources:
        p.require(source.is_file(), 'Missing runtime source: ' + str(source))
    plugin = output / bepinex['assembly']
    before = p.game_hashes()
    shared.compile_plugin(framework, p.GAME / bepinex['managed'], plugin, sources,
                          p.WORK / 'bepinex/build/compile.rsp', bepinex['references'])
    import subprocess
    binding = subprocess.run([p.shell(), '-NoProfile', '-File', str(p.WORK / 'scripts/validate_runtime.ps1'),
                              '-PluginDll', str(plugin),
                              '-GameDll', str(p.GAME / bepinex['managed'] / 'Assembly-CSharp.dll'),
                              '-ReportPath', str(p.WORK / 'reports/runtime-bindings.json')],
                             check=True, capture_output=True, text=True)
    print(binding.stdout.strip())
    p.require(p.game_hashes() == before, 'Game changed during compilation')
    report = dict(version=p.sha(plugin.read_bytes())[:16], assembly=bepinex['assembly'],
                  bytes=plugin.stat().st_size,
                  sources={str(x.relative_to(p.SERIES)).replace('\\', '/'): p.sha(x.read_bytes()) for x in sources},
                  original_game_unchanged=True, compiled_at=time.strftime('%Y-%m-%d %H:%M:%S'),
                  translation_pack=False, chinese_font=False,
                  runtime_tested=False, release_ready=False,
                  limitations=['Type check only: no release translation pack or atlas is bundled yet.',
                               'The image replacement plugin is not built by this entry point.'])
    p.save(p.WORK / 'reports/runtime_compile_latest.json', report)
    print('COMPILED ' + str(plugin) + ' (' + str(plugin.stat().st_size) + ' bytes)')


if __name__ == '__main__':
    main()
