"""One entry point for all registered games. Never installs during build."""
import argparse
import os
import subprocess
import sys
from project_config import resolve, read, ROOT

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['list','paths','status','extract','build','verify','install','apply','batch','legacy-build'])
    parser.add_argument('--game')
    args, rest = parser.parse_known_args()
    if args.action == 'list':
        for key, entry in read()['games'].items():
            print(key + ': ' + entry['title'] + ' [' + entry['adapter'] + ']')
        return
    config = resolve(args.game)
    project = config['project']
    if args.action == 'paths':
        for key in ('id','project','installation','adapter_path'): print(str(key) + ': ' + str(config[key]))
        return
    if not (project/'project.json').is_file(): raise ValueError('Project manifest missing')
    scripts = project/'scripts'
    if args.action == 'install':
        command = ['pwsh','-NoProfile','-File',str(scripts/'install_bepinex.ps1')]
    elif args.action in ('build','verify'):
        command = [sys.executable,str(scripts/'build_bepinex.py')]
    else:
        command = [sys.executable,str(scripts/'pipeline.py'),'build' if args.action == 'legacy-build' else args.action]
    # Each game keeps its own build orchestration and fixtures until engine parity is proven.
    subprocess.run(command + rest, cwd=ROOT, check=True)

if __name__ == '__main__': main()
