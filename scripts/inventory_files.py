#!/usr/bin/env python3
"""Create a read-only project file manifest with SHA-256 hashes and rough types."""
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

SUPPORTED={'.dwg','.dxf','.pdf','.rvt','.ifc','.xlsx','.xls','.docx','.txt','.md','.png','.jpg','.jpeg','.tif','.tiff'}

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def classify(name: str) -> list[str]:
    n=name.lower(); tags=[]
    groups={
      '目录':['目录','封面','index','cover'], '总说明':['总说明','施工说明','施工细则','设计说明','general note'],
      '平面':['平面','plan'], '天花':['天花','吊顶','rcp','ceiling'], '地面':['地面','铺装','floor finish'],
      '立面':['立面','elevation'], '节点':['节点','大样','detail'], '材料':['材料','物料','material'],
      '门窗':['门表','门窗','door'], '给排水':['给排水','plumbing','dw-'], '电气':['电气','照明','插座','power','de-'],
      '暖通':['暖通','通风','空调','hvac'], '消防':['消防','火警','sprinkler','fire'], '智能化':['弱电','智能','通信','security','dt-']}
    for tag,keys in groups.items():
        if any(k in n for k in keys): tags.append(tag)
    return tags

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('root', help='Project folder or file')
    ap.add_argument('-o','--output', required=True)
    ap.add_argument('--all-files', action='store_true')
    args=ap.parse_args(); root=Path(args.root).resolve()
    if not root.exists(): raise SystemExit(f'Path does not exist: {root}')
    files=[root] if root.is_file() else [p for p in root.rglob('*') if p.is_file()]
    items=[]
    for p in sorted(files, key=lambda x:str(x).lower()):
        ext=p.suffix.lower()
        if not args.all_files and ext not in SUPPORTED: continue
        st=p.stat()
        items.append({'relative_path':p.name if root.is_file() else str(p.relative_to(root)),
          'extension':ext,'size':st.st_size,'modified_utc':datetime.fromtimestamp(st.st_mtime,timezone.utc).isoformat(),
          'sha256':sha256(p),'tags':classify(p.name),'parse_status':'not_attempted'})
    data={'schema_version':'1.0','root':str(root),'created_utc':datetime.now(timezone.utc).isoformat(),
          'file_count':len(items),'supported_extensions':sorted(SUPPORTED),'files':items}
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(out.resolve()),'file_count':len(items)},ensure_ascii=False))
if __name__=='__main__': main()
