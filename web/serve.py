"""Serve this folder on localhost only. Ctrl+C stops the server."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import argparse

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766);args=p.parse_args()
    root=Path(__file__).resolve().parent
    print(f'Open http://127.0.0.1:{args.port}/',flush=True)
    try:ThreadingHTTPServer(('127.0.0.1',args.port),partial(SimpleHTTPRequestHandler,directory=str(root))).serve_forever()
    except KeyboardInterrupt:pass
