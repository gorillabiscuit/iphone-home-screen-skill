#!/usr/bin/env python3
"""Read, plan and verify a Home Screen page reorganisation.

Offline commands use the standard library. Device commands additionally need
pymobiledevice3. No layout writes, deletion, installation, pairing or spacing automation.
"""
import argparse
import asyncio
from collections import Counter
import copy
import json
from pathlib import Path
import plistlib

VOLATILE = {"iconModDate", "userSelectedElementIdentifier"}


def normal(value):
    if isinstance(value, list):
        return [normal(x) for x in value if x != []]
    if isinstance(value, dict):
        return {k: normal(v) for k, v in value.items() if k not in VOLATILE}
    return value


def entries(page):
    if not isinstance(page, list):
        raise ValueError("Expected a list of icons")
    return [x for x in page if x != []]


def inventory(pages):
    return Counter(plistlib.dumps(normal(x)) for p in pages for x in entries(p))


def key(item):
    if not isinstance(item, dict):
        raise ValueError("Unsupported icon entry; inspect the snapshot")
    if item.get("listType") == "folder":
        return "folder:" + item["displayName"]
    value = item.get("displayIdentifier")
    if not value or item.get("listType") not in (None, "icon"):
        raise ValueError("Unsupported widget or icon entry in movable pages")
    return value


def build(baseline, plan):
    """Replace a contiguous range, copying original objects without app loss."""
    start, end = plan["replace_pages"]
    if not all(type(x) is int for x in (start, end)) or not 1 <= start < end <= len(baseline):
        raise ValueError("replace_pages must exclude dock and be a valid [start,end) range")
    if not plan["pages"]:
        raise ValueError("At least one destination page is required")
    originals = {}
    for page in baseline[start:end]:
        for item in entries(page):
            k = key(item)
            if k in originals:
                raise ValueError("Duplicate identity in movable pages; narrow the range: " + k)
            originals[k] = item
    selected = []
    compact = []
    for page in plan["pages"]:
        slots = page["slots"]
        if not isinstance(slots, list) or not slots or len(slots) % 4:
            raise ValueError("Use complete four-column rows, including null slots")
        if len(slots) > 24:
            raise ValueError("This helper supports up to six four-column rows")
        ids = [x for x in slots if x is not None]
        if not ids or any(not isinstance(x, str) for x in ids):
            raise ValueError("Pages need nonempty string identities or null slots")
        if any(x not in originals for x in ids):
            raise ValueError("Plan contains an identity absent from the movable range")
        selected.extend(ids)
        compact.append([copy.deepcopy(originals[x]) for x in ids])
    if Counter(selected) != Counter(originals.keys()):
        raise ValueError("Plan must contain every movable identity exactly once")
    result = copy.deepcopy(baseline[:start]) + compact + copy.deepcopy(baseline[end:])
    if inventory(result) != inventory(baseline):
        raise ValueError("Inventory changed")
    return result


def verify(actual, expected):
    if normal(actual) != normal(expected):
        raise ValueError("Readback differs in inventory, protected content or app order")
    return {"verified": True, "home_screen_pages": len(actual) - 1,
            "spacing": "Requires separate visual verification"}


def read(path):
    return plistlib.loads(Path(path).read_bytes())


def save_new(path, value):
    with Path(path).open("xb") as output:
        plistlib.dump(value, output, fmt=plistlib.FMT_BINARY)


async def device(args):
    # Read-only live helper. No write backend is enabled by this skill.
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.springboard import SpringBoardServicesService
    if Path(args.out).exists():
        raise FileExistsError('Choose a fresh snapshot filename')
    async with await create_using_usbmux(autopair=False, connection_type='USB') as lockdown:
        async with SpringBoardServicesService(lockdown) as service:
            current = await asyncio.wait_for(service.get_icon_state(), 15)
    save_new(args.out, current)
    print(json.dumps({'snapshot_saved': args.out, 'home_screen_pages': len(current)-1}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    snap = subs.add_parser("snapshot", help="Read a paired USB device to a new plist")
    snap.add_argument("--out", required=True)
    prep = subs.add_parser("prepare", help="Validate a JSON plan offline and save compact plist")
    prep.add_argument("--baseline", required=True)
    prep.add_argument("--plan", required=True)
    prep.add_argument("--out", required=True)
    check = subs.add_parser("verify", help="Compare saved readback against baseline and plan offline")
    check.add_argument("--baseline", required=True)
    check.add_argument("--plan", required=True)
    check.add_argument("--actual", required=True)
    args = parser.parse_args()
    if args.command == "snapshot":
        asyncio.run(device(args))
    else:
        expected = build(read(args.baseline), json.loads(Path(args.plan).read_text()))
        if args.command == "prepare":
            save_new(args.out, expected)
            print(json.dumps({"plan_valid": True, "home_screen_pages": len(expected)-1,
                              "warning": "Compact order only; restore spacing through UI"}))
        else:
            print(json.dumps(verify(read(args.actual), expected)))


if __name__ == "__main__":
    main()
