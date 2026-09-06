"""Fetch the pinned Mono.Cecil tool dependency; no game assets are downloaded."""
import hashlib
from pathlib import Path
import urllib.request
import zipfile

root=Path(__file__).resolve().parents[1]
archive=root/'bin/ilspycmd.8.2.0.7535.nupkg'
expected='d7cd4f2b6d03875db8228cc2d5a4dc76e000dd64ba625a735848454f346445fd'
archive.parent.mkdir(exist_ok=True)
if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:
    data=urllib.request.urlopen('https://api.nuget.org/v3-flatcontainer/ilspycmd/8.2.0.7535/ilspycmd.8.2.0.7535.nupkg',timeout=60).read()
    if hashlib.sha256(data).hexdigest()!=expected: raise ValueError('ILSpy package checksum mismatch')
    archive.write_bytes(data)
destination=root/'bin/ilspy'
with zipfile.ZipFile(archive) as z:
    for name in z.namelist():
        if not (destination/name).resolve().is_relative_to(destination.resolve()): raise ValueError('Unsafe archive path')
    z.extractall(destination)
print('Pinned ILSpy / Mono.Cecil dependency ready.')
