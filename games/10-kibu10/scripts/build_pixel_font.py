"""Reuse the eighth-game atlas builder with tenth-game output/input roots."""
import importlib.util
import json
from pathlib import Path
WORK = Path(__file__).resolve().parents[1]
SERIES = WORK.parents[1]
spec = importlib.util.spec_from_file_location('_shared_eighth_font_builder', SERIES/'games/08-kibu8/scripts/build_pixel_font.py')
impl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impl)
impl.WORK = WORK
impl.ROOT = WORK/'bepinex'
impl.FIXED_UI_TEXT += '永劫会事件历史记录关闭上一页下一页'

def build_font(output=None, dialogue=None, ui_paths=None):
    lock = WORK/'bepinex/font-dependency.lock.json'
    if not lock.exists():
        lock.write_bytes((SERIES/'games/08-kibu8/bepinex/font-dependency.lock.json').read_bytes())
    if ui_paths is None:
        ui_paths = []
        inputs = WORK/'bepinex/build/font-inputs'
        inputs.mkdir(parents=True,exist_ok=True)
        for source in sorted((WORK/'work').glob('ui-*.zh-CN.json')):
            data=json.loads(source.read_text(encoding='utf-8-sig'))
            # Internal line-breaking tables/resource identifiers are never painted.
            # All actual player-visible excluded source text remains covered.
            data['entries']=[e for e in data['entries'] if e.get('classification') not in ('excluded_internal','technical_sentinel')]
            dest=inputs/source.name
            dest.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
            ui_paths.append(dest)
    result = impl.build_font(output, dialogue, ui_paths)
    out = Path(output) if output else WORK/'bepinex/build/plugin'
    for file in (out/'licenses').glob('*Notice.txt'):
        file.write_text(file.read_text(encoding='utf-8').replace('Kibu8', 'Kibu10'), encoding='utf-8')
    return result

if __name__ == '__main__':
    build_font()
