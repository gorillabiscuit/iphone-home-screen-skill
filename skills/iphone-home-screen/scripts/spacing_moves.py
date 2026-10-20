#!/usr/bin/env python3
"""Print drag coordinates for a compact page; sends no mouse input."""
import argparse
import json


def moves(slots, xs, ys):
    if len(xs) != 4 or len(slots) != len(xs)*len(ys):
        raise ValueError("Geometry must match the complete four-column slot grid")
    occupied = [(i, item) for i, item in enumerate(slots) if item is not None]
    result = []
    for source in range(len(occupied)-1, -1, -1):
        target, item = occupied[source]
        if target == source:
            continue
        result.append({"identity": item, "from": [xs[source%4], ys[source//4]],
                       "to": [xs[target%4], ys[target//4]]})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--page-index", type=int, required=True,
                        help="Zero-based index within plan.pages")
    parser.add_argument("--geometry", required=True,
                        help="JSON with xs (four centres) and ys (row centres)")
    args = parser.parse_args()
    plan = json.load(open(args.plan))
    geometry = json.load(open(args.geometry))
    print(json.dumps(moves(plan["pages"][args.page_index]["slots"],
                           geometry["xs"], geometry["ys"]), indent=2))
