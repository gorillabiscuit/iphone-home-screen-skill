#!/usr/bin/env python3
"""Show what a reorganisation would involve without changing the phone.

Reads a saved layout (or reads the phone, read-only) and reports pages,
folders, widgets and sparse pages. With a plan it also checks that the plan
keeps every icon and counts the drags needed to restore the gaps. With a
timing log from drag_log.py it turns that count into minutes.

The USB read cannot show empty cells, so the report says so instead of guessing.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))
import drag_log
import layout
import plan_review

SPARSE_BELOW = 10


def kind(item):
    if isinstance(item, dict) and item.get("listType") == "folder":
        return "folder"
    if isinstance(item, dict) and (item.get("iconType") == "custom" or "gridSize" in item):
        return "widget"
    return "app"


def describe(state):
    """Summarise a USB layout: element 0 is the dock, the rest are pages."""
    pages = []
    folders = []
    for number, page in enumerate(state[1:], 1):
        items = layout.entries(page)
        kinds = [kind(x) for x in items]
        for item in items:
            if kind(item) == "folder":
                inside = sum(len(layout.entries(sub)) for sub in item.get("iconLists", []))
                folders.append({"page": number, "name": item.get("displayName", ""), "apps": inside})
        pages.append({"page": number, "items": len(items), "apps": kinds.count("app"),
                      "folders": kinds.count("folder"), "widgets": kinds.count("widget"),
                      "sparse": len(items) < SPARSE_BELOW and "widget" not in kinds})
    return {"dock_items": len(layout.entries(state[0])) if state else 0, "home_screen_pages": len(pages),
            "pages": pages, "folders": folders,
            "gaps": "Not visible: the USB read lists icons in order and leaves out empty cells. Check gaps on screen."}


def report(state, plan=None, timing=None):
    result = {"changes_made": False, "layout": describe(state)}
    if plan is not None:
        try:
            layout.build(state, plan)
            result["plan"] = {"valid": True}
        except (ValueError, KeyError) as error:
            result["plan"] = {"valid": False, "problem": str(error)}
        else:
            review = plan_review.review(plan)
            moves = review["total_gap_restoration_drags"]
            result["plan"].update({"pages_in_plan": len(plan["pages"]), "sparse_pages": [p["title"] for p in review["pages"] if p["review_sparse"]],
                                   "gap_restoration_drags": moves, "scope": review["scope"], "caveat": review["caveat"]})
            if timing:
                result["plan"]["time"] = drag_log.estimate(drag_log.summarize(timing), moves)
            else:
                result["plan"]["time"] = {"moves": moves, "estimate": "unmeasured",
                                          "reason": "No timing log yet. Time a few real moves with drag_log.py first."}
    return result


def show(result):
    lay = result["layout"]
    print(f"Home Screen pages: {lay['home_screen_pages']}   dock items: {lay['dock_items']}")
    for p in lay["pages"]:
        flag = "  <- sparse" if p["sparse"] else ""
        print(f"  page {p['page']:>2}: {p['items']:>2} items ({p['apps']} apps, {p['folders']} folders, {p['widgets']} widgets){flag}")
    for f in lay["folders"]:
        print(f"  folder on page {f['page']}: {f['apps']} apps")
    print(lay["gaps"])
    plan = result.get("plan")
    if plan:
        if not plan["valid"]:
            print("Plan is NOT valid:", plan["problem"])
        else:
            print(f"Plan is valid: {plan['pages_in_plan']} pages, {plan['gap_restoration_drags']} drags to restore gaps after a compact write.")
            print("Time:", json.dumps(plan["time"]))
            print(plan["caveat"])
    print("No changes were made to the phone.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--snapshot", help="A saved layout plist")
    source.add_argument("--live", action="store_true", help="Read the phone over USB (read-only); needs --snapshot-out")
    parser.add_argument("--snapshot-out", help="Fresh filename for the layout read with --live")
    parser.add_argument("--plan", help="Plan JSON as used by layout.py prepare")
    parser.add_argument("--timing-log", help="Log written by drag_log.py")
    parser.add_argument("--report-out", help="Fresh filename for the JSON report")
    args = parser.parse_args()
    if args.live:
        if not args.snapshot_out:
            parser.error("--live needs --snapshot-out so the layout is kept")
        asyncio.run(layout.device(SimpleNamespace(out=args.snapshot_out)))
        path = args.snapshot_out
    else:
        path = args.snapshot
    plan = json.loads(Path(args.plan).read_text()) if args.plan else None
    timing = drag_log.load(args.timing_log) if args.timing_log else None
    result = report(layout.read(path), plan, timing or None)
    show(result)
    if args.report_out:
        with Path(args.report_out).open("x") as out:
            json.dump(result, out, indent=2)


if __name__ == "__main__":
    main()
