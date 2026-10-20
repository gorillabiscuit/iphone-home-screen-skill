# Layout design: colour and wallpaper style

This is the author's own style, one option among several. See sorting-options.md for the others and for the evidence. Use this file when the owner chooses purpose pages with colour order and wallpaper bands.

## Build a visual inventory

Record page number, app identity, purpose, folder membership, slot, dominant background colour, secondary glyph colour and user constraints. App names alone are insufficient: icon variants change with updates and appearance mode.

Use screenshots or actual icon images to make a contact sheet. Match what the eye sees. A white tile with a strong blue circle may fit beside blue icons better than beside mostly white icons. Do not classify colour from a whole-image pixel average; that loses contrast and multicoloured structure.

## Choose the page sequence and density together

Consolidate related purpose groups first. Books, podcasts, music and video often form a useful media page; multiple game pages may fit on one page. Do not mix unrelated apps solely to fill a colour row.

A page with fewer than about ten icons deserves review, not automatic removal. Prefer around 12–20 icons when the inventory supports it; a game collection can use most of the grid. These are design heuristics, not requirements. Identify when preserving purpose would require an intentionally sparse page.

Keep purchased games and seasonal apps unless the user explicitly chooses otherwise. Offloaded apps still belong in the layout. Folders can be grouped on the final page when requested; never assume folders should be dissolved.

## Colour rhythm

Decide a global top-to-bottom rhythm before ordering individual pages. If matching wallpaper, use the wallpaper's actual visible bands in the icon area. The dock, clock and margins affect those bands. A dark-blue-to-orange wallpaper needs a different sequence from a conventional red-to-violet rainbow.

Keep strong neighbouring colours together. Give incompatible colours separate rows when space allows. Separate black-heavy icons from white-heavy icons consistently, but let a recognisable dominant glyph influence placement. Multicoloured icons often work as a transition or as their own group.

Represent all grid slots, including nulls. Sparse groups should sit at their matching colour band, not automatically at the top. Avoid manufacturing many near-empty pages to achieve perfect colour purity.

## Review the full sequence

Check:
- Apps remain easy to find by purpose.
- The same colour appears at a comparable height across pages.
- Similar icons share rows instead of being scattered by minor background differences.
- Empty space is deliberate and not excessive.
- Folders, widgets, dock and labels follow the user's preferences.

Test a representative page before repeating a design. After merging pages, re-evaluate density and colour balance together. Do not claim that the final arrangement is objectively aesthetic; show it and incorporate feedback.


## Offline classifier

Run scripts/classify_icons.py --manifest icons.json --out /fresh/output. The manifest is a list of objects with path, label, identity and source. Keep source explicit: cached phone PNG, current phone PNG, screenshot or App Store artwork. Never call cached artwork current.

The helper masks transparent/rounded corners, converts embedded profiles when supported, samples an inset border in OKLab, separates a contrasting glyph when the background is uniform, and clusters colours deterministically. It reports background and accent separately, neutral categories, multicolour/ambiguity flags and a visual contact sheet. A strong accent can be an alternate bucket for a neutral tile.

Visually review the sheet. Photo icons such as Kindle or game artwork can be classified by a large dark silhouette instead of the colour the user perceives. A multicolour mark must not be reduced to a single confident accent. Default artwork may not match dark/tinted/clear appearance; use current screenshots to resolve discrepancies.

## Cost before application

Run scripts/plan_review.py on the full affected plan. A trailing blank costs no corrective drag after compaction. A leading blank can force every subsequent icon to move. Choose touch-only for small edits when cheaper than rebuilding all spacing. Report the count as a strategy estimate, not a mathematical minimum.
