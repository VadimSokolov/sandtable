"""Build, regenerate, or serve the combined convoy learning environment.

Run from any directory: python /path/to/sandtable/tools/convoy_study.py build
The full run-all experiment regenerates outputs in dependency order.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/'studies/convoy-study'
ORDER=('baseline_09_14','contact_09_12_14','leader_12_17','console_19',
       'integrated','red_priority_18','route_13','urban_16')

def build():
    missing=[name for name in ORDER if not (STUDY/name/'replays.json').exists()]
    if missing:
        raise SystemExit('Missing generated replays: '+', '.join(missing)+
                         '. Run: python tools/convoy_study.py run-all')
    sys.path.insert(0,str(STUDY/'leader_12_17'))
    spec=importlib.util.spec_from_file_location('convoy_learning_viewer',STUDY/'leader_12_17/run.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    traces=[]
    for name in ORDER:traces+=json.loads((STUDY/name/'replays.json').read_text())
    module.build_viewer(traces)
    out=ROOT/'report/viz/convoy_study.html'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes((STUDY/'baseline_09_14/viewer.html').read_bytes())
    print(f'Built {out} ({len(traces)} options)')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('build','run-all','serve'))
    parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args()
    if args.action=='run-all':
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
        for name in ORDER:
            subprocess.run([sys.executable,'-B',str(STUDY/name/'run.py')],cwd=ROOT,env=env,check=True)
    build()
    if args.action=='serve':
        from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
        from functools import partial
        server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(SimpleHTTPRequestHandler,directory=str(ROOT/'report/viz')))
        print(f'Open http://127.0.0.1:{args.port}/convoy_study.html',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()

if __name__=='__main__':main()
