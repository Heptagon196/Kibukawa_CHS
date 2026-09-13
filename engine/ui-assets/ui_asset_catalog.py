"""Resolve explicitly selected, fingerprint-locked shared UI artwork."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent


def resolve_asset(asset_id, root=ROOT):
    root = Path(root).resolve()
    catalog = json.loads((root/'catalog.json').read_text(encoding='utf-8'))
    if catalog.get('schema') != 1:
        raise ValueError('Unsupported shared UI catalog')
    entry = catalog['assets'][asset_id]
    path = (root/entry['png']).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError('Shared UI path escapes catalog')
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry['png_sha256']:
        raise ValueError('Shared UI image hash mismatch: '+asset_id)
    with Image.open(path) as image:
        if list(image.size) != entry['size']:
            raise ValueError('Shared UI image dimensions mismatch: '+asset_id)
    return path, entry


def validate_source(entry, source):
    if entry.get('kind') == 'build-template':
        raise ValueError('Build template cannot be a replacement')
    if source['size'] != entry['size'] or source['source_rgba_sha256'] not in entry['source_rgba_sha256']:
        raise ValueError('Original image does not match shared UI asset')
