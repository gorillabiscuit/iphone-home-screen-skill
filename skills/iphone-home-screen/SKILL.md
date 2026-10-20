---
name: iphone-home-screen
description: Audit and reorganise a real iPhone Home Screen by purpose, colour and wallpaper using a Mac, iPhone Mirroring and optional USB layout tools. Use for app-page consolidation, icon spacing and related appearance cleanup.
---

# iPhone Home Screen

Make the phone easier to navigate and visually coherent. Treat page membership, icon position, wallpaper and information density as a single design. Work on the real phone only when the user requests changes; a request for ideas or a preview is not an instruction to apply them.

## Evidence and experiment gate

Read [references/evidence.md](references/evidence.md) before choosing an automation route. It separates demonstrated results, blocked tests and hypotheses. For a new device, run read-only discovery first. Optional dictionary writes and HID touch are not established defaults.

Use [references/device-workflow.md](references/device-workflow.md) for live reads, backup extraction and experiment prerequisites. Never run reload_icon_state, --reload or an empty-state write. Save snapshots as binary plists. Software installation and Developer Mode need agreement under this project's brief.

## Before you start

Run `scripts/preflight.py` and read [references/requirements.md](references/requirements.md). The check changes nothing. If it reports a required failure, say which route is closed and offer what still works: reading the phone, planning offline and a dry run need much less than applying moves with iPhone Mirroring. Do not install software or change settings to clear a failure without the owner's agreement.

Offer a dry run before any change: `scripts/dry_run.py` reports pages, folders, widgets, sparse pages, whether a plan keeps every icon, and how many drags it needs. It writes nothing to the phone. When helping someone else test this skill, follow [references/testing.md](references/testing.md).

## Establish the current state

Read the current phone, not just old chat screenshots. Reuse the user's existing choices and authorizations. Capture before images and a page inventory before changes. When USB access is available, save a new immutable layout snapshot with the bundled helper.

Ask only about decisions that affect the outcome and cannot be inferred. Identify purpose groups, apps that must remain, folders, dock, widgets, labels and the desired colour rhythm. A sparse page can be intentional. Do not turn the example preferences below into universal rules.

For an app cleanup, read [references/app-audit.md](references/app-audit.md). Missing usage dates do not prove an app has never been used. Recommend deletions separately from icon moves.

## Plan before moving

Read [references/layout-design.md](references/layout-design.md). Produce an explicit row-and-column plan with empty slots represented, plus an icon contact sheet or preview when useful. Check the entire sequence of pages, not just each page in isolation.

For the style developed in this project, the useful starting point is:
- Purpose groups determine pages.
- Dominant icon colours determine adjacent rows.
- Colour bands follow the chosen wallpaper vertically.
- Merge related groups before creating extra sparse pages.
- Keep labels, and put folders together at the end if the user wants that.

These are defaults to adapt, not fixed requirements. Show material tradeoffs rather than optimizing colour at the expense of finding apps.

Read-only/offline helpers:
- scripts/backup_positions.py extracts layout metadata from an accessible unencrypted backup and leaves cell numbering unconfirmed until screenshot observations settle it.
- scripts/classify_icons.py produces background/accent colour candidates and contact sheets from a cached icon manifest. It needs existing Pillow/numpy.
- scripts/plan_review.py estimates how many drags a compact write would create. Compare this with changing only the affected icons.
- scripts/layout.py validates inventory and page order without enabling experimental writes.
- scripts/preflight.py checks this Mac and phone against the requirements and changes nothing.
- scripts/dry_run.py reads a snapshot or the phone and reports what a plan would involve, with no changes.
- scripts/drag_log.py times each move (`run` wraps the drag helper) and turns the log into measured minutes. Never quote a time per move that did not come from this log; say "unmeasured" instead.

## Apply with the appropriate control method

Read [references/device-workflow.md](references/device-workflow.md) before device operations. It includes setup, supported helpers, known limitations and recovery.

Prefer the provided computer-control API for UI work. The optional Swift held-drag helper requires authorization for alternative mouse input when the control environment requires it; the skill itself does not supply that authorization.

USB writes are an optional, separately validated route for an approved substantial page reorganisation. The packaged helper deliberately has no automatic write command. They can compact icons and erase intentional gaps across the layout. For a few moves or spacing changes, use the UI. Keep the current wallpaper and personal data out of any shareable skill package.

Time every drag so real timings exist: `scripts/drag_log.py run` wraps the drag helper, and `add` records a move made with another control method. Apply page membership first, then restore blank slots through Mirroring. Never write the compact layout again after spacing it. Verify each page before navigating away. A successful command or mouse event is not proof that an icon moved.

Stop input when the phone disconnects, the Mac locks, editing mode exits, or an unexpected dialog appears. Record progress and reobserve before resuming. Do not run queued drags against stale screen coordinates.

## Verify and release the phone

Compare the final inventory, folder contents, protected pages and app order against the baseline and plan. Then visually verify spacing, colour rhythm and page density; USB readback alone cannot establish those.

Save final screenshots and a concise progress record outside the skill. Exit editing and release Mirroring when finished. Report concrete changes, anything incomplete, and whether apps were deleted. Never imply that layout snapshots back up application data or that they guarantee exact restoration of blank slots.

For requested before/after images or a demonstration video, read [references/article-media.md](references/article-media.md). Recording or publishing is a separate scope, not an automatic part of tidying a phone.
