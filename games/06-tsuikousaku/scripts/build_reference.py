"""Build the optional knowledge sidebar using the shared BepInEx layer; never install or launch."""
import sys
import time
import pipeline as p

sys.path.insert(0, str(p.SERIES / 'engine/bepinex'))
import build as shared

def main():
    before = p.game_hashes()
    previous = p.first_project_hashes()
    text_hash = p.sha((p.WORK / 'work/cache.json').read_bytes())
    target = p.load(p.WORK / 'project.json')['bepinex']
    profile = p.load(p.SERIES / 'engine/bepinex/profiles' / (target['profile'] + '.json'))
    framework, dependency = shared.ensure_framework(
        p.SERIES / 'engine/bepinex/locks' / profile['lock'],
        p.SERIES / 'cache/bepinex' / target['profile'])
    output = p.inside(p.WORK / 'out' / ('reference_' + str(time.time_ns())))
    output.mkdir(parents=True)
    plugin = output / 'Kibu6Reference.dll'
    shared.compile_plugin(framework, p.GAME / target['managed'], plugin,
        [p.WORK / 'bepinex/src/ReferencePlugin.cs'], output / 'compile.rsp', target['references'])
    folder = 'BepInEx/plugins/Kibu6Reference/'
    shared.stage_package(output / 'package', framework, dependency, {
        folder + plugin.name: plugin,
        folder + 'reference.html': p.WORK / 'bepinex/reference.html',
        'README_REFERENCE.txt': p.WORK / 'bepinex/README_REFERENCE.txt',
        'BepInEx/licenses/BepInEx-LICENSE.txt': p.SERIES / 'engine/bepinex/licenses/BepInEx-LICENSE.txt',
    }, set(before))
    archive = output / 'Kibu6_KnowledgeReference.zip'
    shared.archive_package(output / 'package', archive)
    p.require(before == p.game_hashes(), 'Game files changed')
    p.require(previous == p.first_project_hashes(), 'Previous projects changed')
    p.require(text_hash == p.sha((p.WORK / 'work/cache.json').read_bytes()), 'Translation changed')
    p.save(p.WORK / 'reports/reference-build.json', dict(
        archive=str(archive), sha256=p.sha(archive.read_bytes()), runtime_tested=False,
        original_game_unchanged=True, previous_projects_unchanged=True, translation_unchanged=True))
    print(archive)

if __name__ == '__main__':
    main()
