#!/usr/bin/env python3
"""Extract candidate requirement lines from text, Markdown, DOCX and XLSX files."""
from __future__ import annotations
import argparse, json, re, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

KEYS=('应','必须','不得','严禁','需','须','采用','按照','执行','完成面','深化','甲供','防火','防水','检修','收口','标高')
NS='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def docx_lines(p):
    with zipfile.ZipFile(p) as z: root=ET.fromstring(z.read('word/document.xml'))
    for para in root.iter(NS+'p'):
        s=''.join((t.text or '') for t in para.iter(NS+'t')).strip()
        if s: yield s

def xlsx_lines(p):
    try:
        import openpyxl
    except ImportError as exc:
        raise SystemExit('XLSX parsing requires openpyxl: pip install openpyxl') from exc
    wb=openpyxl.load_workbook(p,read_only=True,data_only=True)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value,str) and c.value.strip(): yield f'{ws.title}!{c.coordinate}: {c.value.strip()}'

def lines(p):
    ext=p.suffix.lower()
    if ext in ('.txt','.md'):
        yield from p.read_text(encoding='utf-8',errors='ignore').splitlines()
    elif ext=='.docx': yield from docx_lines(p)
    elif ext=='.xlsx': yield from xlsx_lines(p) or ()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('-o','--output',required=True)
    args=ap.parse_args(); root=Path(args.root).resolve(); rows=[]; idx=1
    if not root.exists(): raise SystemExit(f'Path does not exist: {root}')
    files=[root] if root.is_file() else root.rglob('*')
    for p in files:
        if not p.is_file() or p.suffix.lower() not in ('.txt','.md','.docx','.xlsx'): continue
        for line_no,s in enumerate(lines(p),1):
            s=re.sub(r'\s+',' ',s).strip()
            if len(s)<4 or not any(k in s for k in KEYS): continue
            rows.append({'rule_id':f'CAND-{idx:05d}','source_file':str(p),'source_location':line_no,
             'original_text':s,'scope':'待识别','check_target':'待识别','acceptance_condition':'待人工转译',
             'precedence':'待确认','automation':'待评估','conflict_status':'unchecked','enabled':False}); idx+=1
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'schema_version':'1.0','candidate_count':len(rows),'rules':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(out.resolve()),'candidate_count':len(rows)},ensure_ascii=False))
if __name__=='__main__': main()
