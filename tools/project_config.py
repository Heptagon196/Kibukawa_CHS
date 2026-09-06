"""Series paths are relative to series.json, never the current directory."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read():
    data = json.loads((ROOT / 'series.json').read_text(encoding='utf-8-sig'))
    if data.get('schema') != 1:
        raise ValueError('Unsupported series configuration schema')
    return data

def relative_path(value, internal=False):
    if not isinstance(value, str) or not value or Path(value).is_absolute() or Path(value).drive:
        raise ValueError('Configuration requires relative paths: ' + str(value))
    path = (ROOT / value).resolve()
    if internal and (not path.is_relative_to(ROOT) or path == ROOT):
        raise ValueError('Project must be inside the series workspace')
    return path

def resolve(game_id=None, project=None):
    data = read()
    if project is not None:
        matches = [key for key, value in data['games'].items()
                   if relative_path(value['project'], True) == Path(project).resolve()]
        if len(matches) != 1:
            raise ValueError('Project must have exactly one entry in series.json')
        game_id = matches[0]
    game_id = game_id or data['default_game']
    entry = data['games'][game_id]
    if not entry.get('enabled', False):
        raise ValueError('Game has not been enabled after compatibility review: ' + game_id)
    adapter = relative_path('engine/adapters/' + entry['adapter'], True)
    manifest = relative_path(entry['project'], True) / 'project.json'
    if manifest.is_file():
        project_data = json.loads(manifest.read_text(encoding='utf-8-sig'))
        if project_data.get('id') != game_id or project_data.get('adapter') != entry['adapter']:
            raise ValueError('series.json and project.json disagree on game id or adapter')
    return dict(entry, id=game_id, root=ROOT,
                project=relative_path(entry['project'], True),
                installation=relative_path(entry['installation']), adapter_path=adapter)
