"""Shared BepInEx download, compilation and release infrastructure.
No game-specific pipeline imports or paths. Callers supply verified inputs.
"""
import hashlib, json, os, re, shutil, subprocess, urllib.request, zipfile
from pathlib import Path

def require(test,message):
    if not test: raise ValueError(message)
def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def checked(root,path):
    path=Path(path).resolve()
    require(path.is_relative_to(Path(root).resolve()),'Path outside configured root: '+str(path))
    return path

def ensure_framework(lock_path, cache_root, refresh=False):
    cache_root=Path(cache_root).resolve()
    lock=load(lock_path)
    dest=checked(cache_root, cache_root/lock['asset']); dest.parent.mkdir(parents=True,exist_ok=True)
    cached=dest.exists() and dest.stat().st_size==lock['size'] and sha(dest.read_bytes())==lock['sha256']
    downloaded=False
    if refresh or not cached:
        print('Downloading official BepInEx '+lock['version'],flush=True)
        request=urllib.request.Request(lock['url'],headers={'User-Agent':'Kibukawa-CHS-Build/1.0'})
        temp=dest.with_suffix('.download')
        try:
            with urllib.request.urlopen(request,timeout=90) as response, temp.open('wb') as out:
                shutil.copyfileobj(response,out)
            require(temp.stat().st_size==lock['size'] and sha(temp.read_bytes())==lock['sha256'],'BepInEx download hash mismatch; refusing to use it')
            os.replace(temp,dest); downloaded=True
        finally:
            if temp.exists(): temp.unlink()
    print('BepInEx SHA256 verified: '+lock['sha256'],flush=True)
    extracted=checked(cache_root, cache_root/('framework_'+lock['sha256'][:16]))
    extracted.mkdir(exist_ok=True)
    files=[]
    with zipfile.ZipFile(dest) as archive:
        for info in archive.infolist():
            target=checked(cache_root, extracted/info.filename)
            require(target.is_relative_to(extracted),'Dependency ZIP path traversal')
            if info.is_dir(): target.mkdir(parents=True,exist_ok=True); continue
            content=archive.read(info)
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() or target.read_bytes()!=content: target.write_bytes(content)
            files.append(info.filename)
    for required in ['winhttp.dll','doorstop_config.ini','BepInEx/core/BepInEx.dll','BepInEx/core/0Harmony.dll']:
        require((extracted/required).exists(),'Missing framework file: '+required)
    return extracted,dict(version=lock['version'],sha256=lock['sha256'],downloaded=downloaded,cache_verified=True,files=files)

def compile_plugin(framework, managed, output, sources, response_file, references):
    dotnet=shutil.which('dotnet'); require(dotnet,'Install a .NET SDK to compile the plugin')
    sdk_lines=subprocess.check_output([dotnet,'--list-sdks'],text=True).strip().splitlines()
    choices=[re.fullmatch(r'([^ ]+) \[(.+)\]',line) for line in sdk_lines]
    choices=[m for m in choices if m]
    require(choices,'No .NET SDK installed')
    match=choices[-1]; compiler=Path(match[2])/match[1]/'Roslyn/bincore/csc.dll'
    refs=references
    response=['-nologo','-nostdlib+','-target:library','-optimize+','-langversion:7.3','-out:"'+str(output)+'"']
    response+=['-reference:"'+str(managed/r)+'"' for r in refs]
    response+=['-reference:"'+str(framework/'BepInEx/core'/r)+'"' for r in ['BepInEx.dll','0Harmony.dll']]
    response+=['"'+str(s)+'"' for s in sources]
    rsp=Path(response_file); rsp.parent.mkdir(parents=True,exist_ok=True); rsp.write_text('\n'.join(response),encoding='utf-8-sig')
    subprocess.run([dotnet,str(compiler),'@'+str(rsp)],check=True)

def stage_package(package, framework, dependency, payload, forbidden):
    """Copy the verified framework plus a project-supplied destination/source map."""
    package=Path(package).resolve()
    require(not package.exists(),'Package directory already exists')
    sources={name:checked(framework,Path(framework)/name) for name in dependency['files']}
    require(not set(sources).intersection(payload),'Plugin overwrites framework files')
    sources.update(payload)
    for name,path in sources.items():
        checked(package,package/name)
        require(name not in forbidden and Path(name).name!='Assembly-CSharp.dll','Original game file in package: '+name)
        require(Path(path).is_file(),'Missing package input: '+str(path))
    package.mkdir(parents=True)
    for name,path in sources.items():
        target=checked(package,package/name)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)

def archive_package(package,destination):
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(Path(package).rglob('*')):
            if path.is_file(): archive.write(path,path.relative_to(package).as_posix())
    with zipfile.ZipFile(destination) as archive:
        require(archive.testzip() is None,'Release ZIP corrupted')
