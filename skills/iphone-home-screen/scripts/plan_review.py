#!/usr/bin/env python3
"""Review page density and cost of restoring gaps after a compact USB write."""
import argparse
import json

def review(plan):
    results=[]
    for page in plan['pages']:
        occupied=[i for i,x in enumerate(page['slots']) if x is not None]
        results.append({'title':page.get('title','Untitled'),'icons':len(occupied),
            'density':len(occupied)/len(page['slots']) if page['slots'] else 0,
            'review_sparse':len(occupied)<10,
            'gap_restoration_drags':sum(slot!=n for n,slot in enumerate(occupied)),
            'leading_empty_cells':occupied[0] if occupied else len(page['slots'])})
    return {'pages':results,'total_gap_restoration_drags':sum(p['gap_restoration_drags'] for p in results),
            'scope':'Only supplied pages; include every page affected by a whole-layout write',
            'caveat':'Model for last-to-first spacing from compact order, not a proof of globally minimal moves. Compare against a fresh screenshot-based touch-only plan.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan')
    print(json.dumps(review(json.load(open(p.parse_args().plan))),indent=2))
