#!/usr/bin/env python3
"""Draw your Home Screen as it is now and as a chosen arrangement would look. Changes nothing.

Reads the layout and the app icons, either from a saved snapshot and icon
manifest or from the phone over USB (read-only). It then draws current.png and
proposed.png and saves the arrangement as plan.json, the same format that
layout.py and plan_review.py use.

The arrangement is yours to choose. Built-in starting points:
  colour        loose apps in colour order, folders on the last page
  alphabetical  loose apps A to Z, folders on the last page
  favourites    your favourite apps in the bottom rows of page one, nearest the thumb, then the rest in colour order,
                A to Z order or your own groups (--then). Page one keeps its top empty unless --fill-page-one is given.
  groups        your own named groups, one page each, colour order inside a group
Or write your own plan.json and pass it with --plan. Pages with widgets are
left alone. The USB read cannot see empty spaces, so the current picture
shows icons packed together; a plan can leave spaces.

Needs Pillow and numpy. Reading the phone also needs pymobiledevice3.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import dry_run
import layout
import plan_review

WIDGET_CELLS = {"small": (2, 2), "medium": (4, 2), "large": (4, 4), "extraLarge": (4, 4)}
CELL_W, CELL_H, ICON = 78, 92, 58
PAGES_PER_ROW = 4
MIN_PAGE = 10
STRATEGIES = ("colour", "alphabetical", "favourites", "groups")


def ident(item):
    if isinstance(item, str):
        return item
    return item.get("displayIdentifier") or item.get("bundleIdentifier")


def label(item):
    if isinstance(item, dict):
        return (item.get("displayName") or item.get("displayIdentifier") or "").replace("‎", "")
    return item


def key_of(item):
    try:
        return layout.key(item)
    except (ValueError, KeyError):
        return None


def footprint(item, columns):
    if dry_run.kind(item) == "widget":
        w, h = WIDGET_CELLS.get(item.get("gridSize"), (2, 2))
        return min(w, columns), h
    return 1, 1


def flow(items, columns, rows):
    """Place items in reading order, first fit. Returns the placed cells and what did not fit."""
    grid = [[False] * columns for _ in range(rows)]
    placed = []
    for number, item in enumerate(items):
        w, h = footprint(item, columns)
        spot = next(((c, r) for r in range(rows - h + 1) for c in range(columns - w + 1)
                     if not any(grid[r + i][c + j] for i in range(h) for j in range(w))), None)
        if spot is None:
            return placed, items[number:]
        for i in range(h):
            for j in range(w):
                grid[spot[1] + i][spot[0] + j] = True
        placed.append({"item": item, "col": spot[0], "row": spot[1], "w": w, "h": h})
    return placed, []


def current_pages(state, first, last, columns, rows):
    """Pages first..last-1 of the USB state, packed the way the USB read lists them."""
    pages = []
    for page in state[first:last]:
        items = layout.entries(page)
        while items:
            placed, items = flow(items, columns, rows)
            if not placed:
                raise ValueError("An item does not fit on a page")
            pages.append(placed)
    return pages


def movable_range(state):
    """Pages after the last page that holds a widget. Those are the pages a plan may rearrange."""
    last_widget = max((n for n, page in enumerate(state[1:], 1)
                       if any(dry_run.kind(x) == "widget" for x in layout.entries(page))), default=0)
    if last_widget + 1 >= len(state):
        raise ValueError("No pages without widgets to rearrange")
    return last_widget + 1, len(state)


def colour_key(record):
    """Colours first, around the hue circle from red, then greys light to dark, then anything unclassified."""
    if not record or "base_oklch" not in record:
        return (2, 0, 0)
    lightness, chroma, hue = record["base_oklch"]
    if record.get("neutral"):
        return (1, 0, -lightness)
    return (0, int(((hue - 20) % 360) // 30), -lightness)


def order_colour(keys, colours):
    return sorted(keys, key=lambda k: colour_key(colours.get(k)) + (keys.index(k),))


def order_alpha(keys, names):
    return sorted(keys, key=lambda k: (names.get(k, k).casefold(), k))


def as_pages(keys, columns, rows):
    """Cut an ordered list of keys into full-row pages. Empty cells only pad the last row."""
    cap = columns * rows
    pages = []
    for start in range(0, len(keys), cap):
        slots = list(keys[start:start + cap])
        slots += [None] * (-len(slots) % columns)
        pages.append(slots)
    return pages


def pack_groups(groups, columns, rows):
    """One page per group; a group too small for a page is joined to the one after it. Returns pages and titles."""
    cap = columns * rows
    pages, titles, current, name = [], [], [], ""
    for title, keys in groups:
        if current and len(current) < MIN_PAGE and len(current) + len(keys) <= cap:
            current, name = current + keys, f"{name} + {title}"
            continue
        made = as_pages(current, columns, rows)
        pages += made
        titles += [name if i == 0 else f"{name} (more)" for i in range(len(made))]
        current, name = list(keys), title
    made = as_pages(current, columns, rows)
    return pages + made, titles + [name if i == 0 else f"{name} (more)" for i in range(len(made))]


def match(name, by_key, names):
    """Find an app by identifier or by display name, ignoring case."""
    if name in by_key:
        return name
    lowered = name.casefold()
    return next((k for k, n in names.items() if n.casefold() == lowered), None)


def grouped(apps, groups, by_key, names, colours, within):
    """Named groups in the order given, then an Other group. Orders each group by colour, A to Z or as listed."""
    def inside(found):
        if within == "colour":
            return order_colour(found, colours)
        return order_alpha(found, names) if within == "alphabetical" else found
    listed, taken = [], set()
    for title, entries in (groups or {}).items():
        found = [k for k in (match(e, by_key, names) for e in entries) if k in apps and k not in taken]
        taken.update(found)
        listed.append((title, inside(found)))
    other = inside([k for k in apps if k not in taken])
    return listed + ([("Other", other)] if other else [])


def arrange(strategy, items, colours, columns, rows, favourites=None, groups=None, within="colour", then="colour",
            fill_page_one=False):
    """Turn the movable items into pages of keys (None is an empty cell) and a list of page titles."""
    by_key = {key_of(i): i for i in items if key_of(i)}
    names = {k: label(i) for k, i in by_key.items()}
    folders = [k for k, i in by_key.items() if dry_run.kind(i) == "folder"]
    apps = [k for k in by_key if k not in folders]
    cap = columns * rows
    chosen, order = [], strategy
    if strategy == "favourites":
        wanted = (match(n, by_key, names) for n in (favourites or []))
        chosen = list(dict.fromkeys(k for k in wanted if k in apps))[:12]
        if not chosen:
            raise ValueError("None of the favourites matched an app on these pages")
        apps, order = [k for k in apps if k not in chosen], then
    if order == "colour":
        flat = order_colour(apps, colours)
    elif order == "alphabetical":
        flat = order_alpha(apps, names)
    elif order == "groups":
        listed = grouped(apps, groups, by_key, names, colours, within)
        flat = [k for _, keys in listed for k in keys]
    else:
        raise ValueError("Unknown strategy: " + order)
    if chosen and fill_page_one:
        room = cap - len(chosen)
        pages, titles = as_pages(flat[:room] + chosen, columns, rows) + as_pages(flat[room:], columns, rows), []
    else:
        if order == "groups":
            pages, titles = pack_groups(listed, columns, rows)
        else:
            pages, titles = as_pages(flat, columns, rows), []
        if chosen:
            pages = [[None] * (cap - len(chosen)) + chosen] + pages
            titles = ["Favourites"] + titles + [""] * (len(pages) - 1 - len(titles))
    folder_pages = as_pages(folders, columns, rows)
    titles = (titles + [""] * (len(pages) - len(titles))) if titles else titles
    if any(titles):
        titles = titles + ["Folders"] * len(folder_pages)
    return pages + folder_pages, titles


def make_plan(state, strategy, colours, columns, rows, **options):
    start, end = movable_range(state)
    items = [x for page in state[start:end] for x in layout.entries(page)]
    pages, titles = arrange(strategy, items, colours, columns, rows, **options)
    plan = {"replace_pages": [start, end], "strategy": strategy,
            "pages": [{"title": titles[n] if titles and titles[n] else f"Page {n + 1}", "slots": slots} for n, slots in enumerate(pages)]}
    layout.build(state, plan)
    return plan


def plan_view(state, plan, columns, rows):
    """Placed cells for every page: untouched pages as they are, plan pages cell by cell."""
    start, end = plan["replace_pages"]
    items = {}
    for page in state[start:end]:
        for item in layout.entries(page):
            items[key_of(item)] = item
    drawn = []
    for page in plan["pages"]:
        drawn.append([{"item": items[k], "col": n % columns, "row": n // columns, "w": 1, "h": 1}
                      for n, k in enumerate(page["slots"]) if k is not None])
    head, tail = current_pages(state, 1, start, columns, rows), current_pages(state, end, len(state), columns, rows)
    titles = [None] * len(head) + [p.get("title") for p in plan["pages"]] + [None] * len(tail)
    return head + drawn + tail, titles


def font(size):
    from PIL import ImageFont
    path = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default(size=size)


def draw_pages(pages, icons, path, title, columns, rows, titles=None):
    from PIL import Image, ImageDraw
    pad, head = 14, 30
    card_w = columns * CELL_W + 2 * pad
    card_h = rows * CELL_H + head + pad
    lines = (max(len(pages), 1) + PAGES_PER_ROW - 1) // PAGES_PER_ROW
    sheet = Image.new("RGB", (PAGES_PER_ROW * (card_w + 16) + 16, lines * (card_h + 16) + 56), "#e9ecf1")
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 14), title, font=font(22), fill="#111827")
    small = font(11)
    for n, page in enumerate(pages):
        x0 = 16 + (n % PAGES_PER_ROW) * (card_w + 16)
        y0 = 56 + (n // PAGES_PER_ROW) * (card_h + 16)
        draw.rounded_rectangle((x0, y0, x0 + card_w, y0 + card_h), radius=16, fill="white")
        heading = f"Page {n + 1}" + (f": {titles[n]}" if titles and titles[n] and not titles[n].startswith("Page ") else "")
        draw.text((x0 + pad, y0 + 8), heading[:42], font=small, fill="#6b7280")
        for cell in page:
            item = cell["item"]
            x = x0 + pad + cell["col"] * CELL_W
            y = y0 + head + cell["row"] * CELL_H
            kind = dry_run.kind(item)
            if kind == "widget":
                box = (x + 4, y + 2, x + cell["w"] * CELL_W - 6, y + cell["h"] * CELL_H - 20)
                draw.rounded_rectangle(box, radius=12, fill="#dfe3ea")
                draw.text((box[0] + 8, box[1] + 8), "widget", font=small, fill="#4b5563")
                continue
            box = (x + (CELL_W - ICON) // 2, y, x + (CELL_W + ICON) // 2, y + ICON)
            if kind == "folder":
                draw.rounded_rectangle(box, radius=13, fill="#c9ced8")
                inside = sum(len(layout.entries(sub)) for sub in item.get("iconLists", []))
                draw.text((box[0] + 20, box[1] + 18), str(inside), font=font(18), fill="#374151")
            else:
                tile = icons.get(ident(item))
                if tile:
                    tile = tile.convert("RGBA").resize((ICON, ICON))
                    sheet.paste(tile, box[:2], tile)
                else:
                    draw.rounded_rectangle(box, radius=13, fill="#d1d5db")
                    draw.text((box[0] + 22, box[1] + 18), (label(item) or "?")[:1], font=font(18), fill="#374151")
            draw.text((x + CELL_W // 2, y + ICON + 4), (label(item) or "")[:11], font=small, fill="#374151", anchor="ma")
    sheet.save(path)


def need_imaging():
    """Stop early, before touching the phone, if the picture libraries are missing."""
    for name in ("numpy", "PIL"):
        try:
            __import__(name)
        except ImportError:
            sys.exit(f"Needs Pillow and numpy ({name} is missing). Installing them needs the owner's agreement.")


def classify_all(manifest):
    import classify_icons
    colours = {}
    for record in manifest:
        try:
            colours[record["identity"]] = classify_icons.classify(record["path"])
        except Exception:
            continue
    return colours


def apps_in(value):
    if isinstance(value, list):
        for x in value:
            yield from apps_in(x)
    elif isinstance(value, dict):
        if value.get("listType") == "folder":
            yield from apps_in(value.get("iconLists", []))
        elif dry_run.kind(value) == "app":
            yield value


async def read_phone(out):
    """Read the layout, the grid size and every icon over USB. Writes only into the new output folder."""
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.springboard import SpringBoardServicesService
    from pymobiledevice3.usbmux import list_devices
    phones = [d for d in await list_devices() if d.connection_type == "USB"]
    if len(phones) != 1:
        raise RuntimeError(f"Need exactly one USB phone, found {len(phones)}")
    icons_dir = out / "icons"
    icons_dir.mkdir()
    manifest = []
    async with await create_using_usbmux(serial=phones[0].serial, autopair=False, connection_type="USB") as lockdown:
        async with SpringBoardServicesService(lockdown) as service:
            state = await asyncio.wait_for(service.get_icon_state(), 15)
            try:
                metrics = await asyncio.wait_for(service.get_homescreen_icon_metrics(), 15)
            except Exception:
                metrics = {}
            for item in apps_in(state):
                for name in dict.fromkeys(x for x in (item.get("displayIdentifier"), item.get("bundleIdentifier")) if x):
                    try:
                        data = await asyncio.wait_for(service.get_icon_pngdata(name), 8)
                    except Exception:
                        continue
                    if data:
                        path = icons_dir / (hashlib.sha256(name.encode()).hexdigest()[:24] + ".png")
                        path.write_bytes(data)
                        manifest.append({"identity": ident(item), "label": label(item), "path": str(path)})
                        break
    layout.save_new(out / "layout.plist", state)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return state, metrics, manifest


def load_images(manifest):
    from PIL import Image
    images = {}
    for record in manifest:
        try:
            images[record["identity"]] = Image.open(record["path"]).copy()
        except Exception:
            continue
    return images


def build(state, manifest, out, columns=4, rows=6, plan=None, strategy="colour", **options):
    colours = classify_all(manifest)
    images = load_images(manifest)
    if plan is None:
        plan = make_plan(state, strategy, colours, columns, rows, **options)
    else:
        layout.build(state, plan)
    before = current_pages(state, 1, len(state), columns, rows)
    after, after_titles = plan_view(state, plan, columns, rows)
    name = plan.get("strategy", "your plan")
    draw_pages(before, images, out / "current.png", "Your Home Screen now (empty spaces are not visible in the USB read)", columns, rows)
    draw_pages(after, images, out / "proposed.png", f"Preview: {name} (nothing was moved)", columns, rows, after_titles)
    (out / "plan.json").write_text(json.dumps(plan, indent=2))
    (out / "colours.json").write_text(json.dumps(colours, indent=2))
    review = plan_review.review(plan)
    unknown = sorted({str(x["item"].get("gridSize")) for page in before for x in page
                      if dry_run.kind(x["item"]) == "widget" and x["item"].get("gridSize") not in WIDGET_CELLS})
    summary = {"changes_made": False, "arrangement": name, "pages_now": len(before), "pages_proposed": len(after),
               "apps_with_icons": len(images), "apps_classified": len(colours),
               "sparse_pages_in_plan": [p["title"] for p in review["pages"] if p["review_sparse"]],
               "drags_to_restore_gaps_after_a_compact_write": review["total_gap_restoration_drags"],
               "unrecognised_widget_sizes": unknown,
               "files": ["current.png", "proposed.png", "plan.json", "colours.json"]}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def read_json(path):
    return json.loads(Path(path).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--live", action="store_true", help="Read the phone over USB (read-only)")
    source.add_argument("--snapshot", help="A saved layout plist; needs --manifest")
    parser.add_argument("--manifest", help="JSON list of identity, label and path for each icon PNG")
    parser.add_argument("--out", required=True, help="A new folder; it must not exist yet")
    how = parser.add_mutually_exclusive_group()
    how.add_argument("--strategy", choices=STRATEGIES, default="colour", help="A built-in starting point")
    how.add_argument("--plan", help="Your own plan.json (same format as layout.py prepare)")
    parser.add_argument("--favourites", help="JSON list of app names or identifiers, for the favourites strategy")
    parser.add_argument("--groups", help='JSON {"Group name": ["app name or identifier", ...]}, for the groups strategy')
    parser.add_argument("--within", choices=("colour", "alphabetical", "none"), default="colour", help="Order inside a group")
    parser.add_argument("--then", choices=("colour", "alphabetical", "groups"), default="colour", help="How the other apps follow the favourites")
    parser.add_argument("--fill-page-one", action="store_true", help="With favourites: fill the rest of page one instead of leaving the top empty")
    args = parser.parse_args()
    if (args.strategy == "groups" or (args.strategy == "favourites" and args.then == "groups")) and not args.plan and not args.groups:
        parser.error("Grouping needs --groups")
    if args.strategy == "favourites" and not args.plan and not args.favourites:
        parser.error("The favourites strategy needs --favourites")
    if args.snapshot and not args.manifest:
        parser.error("--snapshot needs --manifest")
    need_imaging()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    if args.live:
        state, metrics, manifest = asyncio.run(asyncio.wait_for(read_phone(out), 300))
    else:
        state, metrics, manifest = layout.read(args.snapshot), {}, read_json(args.manifest)
    summary = build(state, manifest, out, metrics.get("homeScreenIconColumns", 4), metrics.get("homeScreenIconRows", 6),
                    plan=read_json(args.plan) if args.plan else None, strategy=args.strategy,
                    favourites=read_json(args.favourites) if args.favourites else None,
                    groups=read_json(args.groups) if args.groups else None, within=args.within, then=args.then,
                    fill_page_one=args.fill_page_one)
    print(json.dumps(summary, indent=2))
    print(f"Pictures are in {out}. No changes were made to the phone.")


if __name__ == "__main__":
    main()
