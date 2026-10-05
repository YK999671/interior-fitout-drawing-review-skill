#!/usr/bin/env python3
"""Compare two manifests created by inventory_files.py."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def load(p):
    d=json.loads(Path(p).read_text(encoding='utf-8')); return {x['relative_path']:x for x in d['files']}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('old'); ap.add_argument('new'); ap.add_argument('-o','--output')
    args=ap.parse_args()
    a=load(args.old); b=load(args.new); ka=set(a); kb=set(b)
    data={'added':sorted(kb-ka),'removed':sorted(ka-kb),'changed':sorted(k for k in ka&kb if a[k]['sha256']!=b[k]['sha256']),
          'unchanged_count':sum(a[k]['sha256']==b[k]['sha256'] for k in ka&kb)}
    text=json.dumps(data,ensure_ascii=False,indent=2)
    if args.output: Path(args.output).write_text(text,encoding='utf-8')
    print(text)
if __name__=='__main__': main()
