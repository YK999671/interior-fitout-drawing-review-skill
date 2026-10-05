#!/usr/bin/env python3
"""Validate the minimum structure and evidence discipline of an issue JSON file."""
from __future__ import annotations
import argparse, json
from pathlib import Path

REQ=('issue_id','title','category','severity','judgement','location','finding','evidence','impact','question_to_designer','confidence','status')
JUDGEMENTS={'confirmed_conflict','confirmed_missing','interface_open','construction_risk','needs_confirmation','undetermined'}
SEVERITY={'高','中','低'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('issues_json'); args=ap.parse_args()
    data=json.loads(Path(args.issues_json).read_text(encoding='utf-8'))
    issues=data.get('issues',data) if isinstance(data,(dict,list)) else []
    if not isinstance(issues,list): raise SystemExit('Expected a list or {"issues": [...]}')
    errors=[]; ids=set()
    for i,x in enumerate(issues):
        at=f'issues[{i}]'; miss=[k for k in REQ if k not in x]
        if miss: errors.append(f'{at}: missing {miss}')
        iid=x.get('issue_id')
        if iid in ids: errors.append(f'{at}: duplicate issue_id {iid}')
        ids.add(iid)
        if x.get('judgement') not in JUDGEMENTS: errors.append(f'{at}: invalid judgement')
        if x.get('severity') not in SEVERITY: errors.append(f'{at}: invalid severity')
        if not isinstance(x.get('evidence'),list) or not x.get('evidence'): errors.append(f'{at}: evidence required')
        c=x.get('confidence');
        if not isinstance(c,(int,float)) or not 0<=c<=1: errors.append(f'{at}: confidence must be 0..1')
        if x.get('severity')=='高' and x.get('judgement')!='undetermined' and len(x.get('evidence',[]))<2:
            direct=any(e.get('evidence_grade')=='A' for e in x.get('evidence',[]) if isinstance(e,dict))
            if not direct: errors.append(f'{at}: high severity requires 2 evidence items or grade A evidence')
    result={'valid':not errors,'issue_count':len(issues),'errors':errors}
    print(json.dumps(result,ensure_ascii=False,indent=2)); raise SystemExit(0 if not errors else 1)
if __name__=='__main__': main()
