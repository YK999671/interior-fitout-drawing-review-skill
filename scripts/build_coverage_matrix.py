#!/usr/bin/env python3
"""Build a coverage CSV from a scope CSV and a list of review columns."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

DEFAULT=['平面','天花','地面','立面','节点','材料','门窗','强电','弱电','给排水','暖通','消防','家具','界面']

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('scope_csv',help='UTF-8 CSV with building,floor_type,unit_type,room')
    ap.add_argument('-o','--output',required=True)
    ap.add_argument('--columns',help='Comma-separated review columns')
    args=ap.parse_args(); cols=[x.strip() for x in args.columns.split(',')] if args.columns else DEFAULT
    with open(args.scope_csv,encoding='utf-8-sig',newline='') as f: scopes=list(csv.DictReader(f))
    required=('building','floor_type','unit_type','room')
    missing=[k for k in required if not scopes or k not in scopes[0]]
    if missing: raise SystemExit('Missing scope columns: '+','.join(missing))
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',encoding='utf-8-sig',newline='') as f:
        fields=list(required)+cols; w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for s in scopes:
            row={k:s.get(k,'') for k in required}; row.update({c:'pending_parse' for c in cols}); w.writerow(row)
    print(json.dumps({'output':str(out.resolve()),'scope_count':len(scopes),'review_columns':cols},ensure_ascii=False))
if __name__=='__main__': main()
