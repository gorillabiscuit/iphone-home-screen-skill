#!/usr/bin/env python3
"""Extract IconState from an unencrypted local backup and report pins, read-only.

No restore, decryption, backup creation, phone access, or index-base guessing.
"""
from contextlib import closing
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import sqlite3

def extract(backup):
    root=Path(backup)
    manifest=plistlib.loads((root/'Manifest.plist').read_bytes())
    if manifest.get('IsEncrypted'):
        raise ValueError('Encrypted backup: stop; do not change password or encryption settings')
    with closing(sqlite3.connect((root/'Manifest.db').resolve().as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
        matches=db.execute('SELECT fileID FROM Files WHERE domain=? AND relativePath=?',
                           ('HomeDomain','Library/SpringBoard/IconState.plist')).fetchall()
    if len(matches)!=1:raise ValueError('Expected exactly one HomeDomain IconState.plist')
    ident=matches[0][0]
    if not re.fullmatch('[0-9a-fA-F]{40}',ident):raise ValueError('Unexpected backup fileID')
    path=root/ident[:2]/ident
    if not path.exists():path=root/ident
    return path.read_bytes()

def analyse(raw, observations=None):
    state=plistlib.loads(raw)
    if not isinstance(state,dict):raise ValueError('Expected backup root dictionary, not USB list')
    ids=state.get('listUniqueIdentifiers',[])
    metadata=state.get('listMetadata',{})
    if not isinstance(ids,list) or not isinstance(metadata,dict):raise ValueError('Unrecognised metadata schema')
    pages=[];all_candidates={0,1};evidence_count=0
    for i,uid in enumerate(ids):
        meta=metadata.get(uid,{})
        pins=meta.get('fixedLocations',{})
        rows=meta.get('fixedLocationsGridRows');cols=meta.get('fixedLocationsGridColumns')
        if not isinstance(pins,dict):raise ValueError('Unrecognised fixedLocations schema')
        valid_grid=type(rows) is int and type(cols) is int and rows>0 and cols>0
        decoded=[]
        for ident,cell in pins.items():
            entry={'identity':ident,'stored_cell':cell}
            if type(cell) is int and valid_grid:
                entry['candidate_cells']={}
                for base in (0,1):
                    n=cell-base
                    if 0<=n<rows*cols:
                        entry['candidate_cells'][str(base)]={'row':n//cols+1,'column':n%cols+1}
            decoded.append(entry)
        pages.append({'page_index':i,'uuid':uid,'rows':rows,'columns':cols,'pins':decoded,
                      'hidden':bool(meta.get('hiddenDate')),
                      'focus_assignment_count':len(meta.get('focusModeIdentifiers',[]))})
    for obs in observations or []:
        page=pages[obs['page_index']]
        pin=next((p for p in page['pins'] if p['identity']==obs['identity']),None)
        if pin is None or not pin.get('candidate_cells'):
            raise ValueError('Observation cannot be matched to a numeric pin and grid')
        possible={int(b) for b,c in pin['candidate_cells'].items()
                  if c=={'row':obs['row'],'column':obs['column']}}
        all_candidates &= possible;evidence_count+=1
    base=next(iter(all_candidates)) if evidence_count and len(all_candidates)==1 else None
    return {'sha256':hashlib.sha256(raw).hexdigest(),'root_keys':sorted(state.keys()),
            'pages':pages,'pins_found':sum(len(p['pins']) for p in pages),
            'index_base':base,'matched_observations':evidence_count,
            'status':'contradictory observations' if evidence_count and not all_candidates else
                     'base confirmed against supplied observations' if base is not None else
                     'index base unconfirmed; needs current screenshot observations'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--backup',help='Directory containing Manifest.plist and Manifest.db')
    source.add_argument('--plist',help='Already-extracted backup IconState.plist')
    p.add_argument('--observations',help='JSON page_index,identity,row,column observations; row/column start at 1')
    p.add_argument('--out',required=True)
    args=p.parse_args()
    raw=extract(args.backup) if args.backup else Path(args.plist).read_bytes()
    obs=json.loads(Path(args.observations).read_text()) if args.observations else None
    result=analyse(raw,obs)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    (out/'IconState.plist').write_bytes(raw)
    (out/'positions.json').write_text(json.dumps(result,indent=2,default=str))
    print(json.dumps({k:result[k] for k in ('pins_found','index_base','status')}))
if __name__=='__main__':main()
