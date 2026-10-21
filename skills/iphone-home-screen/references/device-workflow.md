# Device workflow and evidence boundaries

Read evidence.md before choosing a new automation backend. Separate a source-code capability from a demonstrated icon move.

## Read-only discovery

Run scripts/preflight.py before anything else (see requirements.md). It reports the Mac, tools, phone and USB speed and changes nothing.

Use existing tools first. Check the connected device count and select the intended phone before reading. Record model, ProductType, ProductVersion and build without publishing serials, UDIDs, pairing records or account details. Do not mistake cached snapshots for the live phone.

The USB route uses an existing pairing with autopair=False and connection_type="USB". Do not silently trust a new device. scripts/layout.py snapshot --out /absolute/work/before.plist reads a layout into a fresh binary plist with a timeout. It refuses overwrite. Its present automatic device selection is suitable only after confirming exactly one connected USB phone.

Inspect installed pymobiledevice3 source and signatures. Version 11.36.0 worked in both the original session and the live research follow-up. The earlier temporary environment disappeared; the authorized replacement is persistent and project-local. Software installation/upgrades need the user's agreement under this project's brief. Use a persistent task-local environment once authorized. Missing dependencies are a reason to skip a live experiment, not permission to install.

Save device screenshots and the raw array. Format 2 contains compact membership/order and can omit important page metadata. Never infer an empty cell from that list alone. Preserve web clips, Safari web apps, widget dictionaries, offloaded icons and duplicate instances when observed. Helpers that cannot understand an entry should fail rather than drop it.

Read get_homescreen_icon_metrics. Fetch icons with get_icon_pngdata, caching by identity and modification metadata. Fetch get_wallpaper_preview_image('homescreen') twice with independent reads and compare hashes, dimensions and the visible wallpaper. Equal bytes only establish repeatability, not freshness. On the tested iOS 27.0.1 phone, this API returned a composited preview with icons, badges and a placeholder widget. Its dark icon rendering differed from live Mirroring. Do not treat it as a clean wallpaper or a faithful device screenshot. NEVER use --reload or reload_icon_state: those write the layout.

## Backup positions

A backup may contain HomeDomain/Library/SpringBoard/IconState.plist with listUniqueIdentifiers and listMetadata. fixedLocations appears to map identities to cell numbers with fixedLocationsGridRows/Columns. These fields are research evidence until measured on the actual phone.

With user authorization, create a local backup in a fresh task-owned directory. Prefer an unencrypted backup if the phone's existing settings permit one. Do not disable existing backup encryption or set a password. If encrypted, inaccessible or prompting for protected access, skip and record the limitation. Do not bypass macOS Full Disk Access restrictions.

Before starting, check actual destination capacity. A filtered acquisition on the tested phone still demanded about 187 GB at its initial space check and failed before delivering IconState. Filtering the files retained locally does not guarantee a small space requirement. Use an adequate destination; do not falsify free-space reporting. A filtered acquisition is not a restorable device backup.

scripts/backup_positions.py --backup /path/to/one-backup --out /path/to/fresh-output uses the backup's Manifest.db read-only to extract only the layout file. Or pass --plist for an already-extracted file. It does not create or restore backups. It refuses encrypted manifests.

The parser reports both candidate cell interpretations and leaves the base unknown until current screenshot observations disambiguate it. Supply --observations as JSON objects with page_index, identity, row and column (row/column start at 1). Use several matching pins across pages. Never choose a base because a third-party article says so. Missing grid sizes remain unknown. Widget footprints and unpinned-flow reconstruction require separate work; the parser does not invent them.

Retain the extracted layout and analysis only in private task files. Delete only the newly created temporary backup/acquisition directory after the experiment as authorized. Never delete pre-existing Finder backups. Confirm deletion according to applicable tools/policies. A layout snapshot is not an app-data backup and the USB array cannot restore exact gaps.

## Offline planning

Use the actual snapshot and explicit slot plan. scripts/layout.py prepare --baseline before.plist --plan plan.json --out planned.plist validates without contacting the phone.

Plan schema:
- replace_pages is [start,end), zero-based in USB state. State index 0 is the dock and must remain outside the range.
- pages holds destination objects with title and slots.
- slots contains four-column rows, up to six rows, using displayIdentifier strings or null.
- Every identity in the replaced range must occur exactly once. Unique folders can use "folder:" plus displayName.
- Preserve widget pages outside the range. Duplicate identities or unsupported types require a richer planner rather than weakening checks.

Run scripts/plan_review.py plan.json. It estimates spacing drags from compact order, flags sparse pages and reports leading blanks. Include ALL pages affected by a whole-layout write, not just changed pages. Compare with a screenshot-based touch-only plan. It is a useful cost model, not an optimal movement solver.

Run scripts/spacing_moves.py --plan plan.json --page-index 0 --geometry geometry.json only for a freshly compact page. Geometry contains measured xs (four centres) and ys (row centres). It prints last-to-first moves and sends no input. Do not replay on a partly spaced page.

## Write routes

No automatic USB write command is enabled in the packaged helper. It provides snapshot, offline prepare and offline verify. The source-guided dictionary route has NOT been verified on this phone; do not silently promote it to the default.

Three different payloads must not be confused:
1. Compact list: previously worked for membership/order in this project but removed gaps.
2. Constructed dictionary with buttonBar, iconLists and ignored: research reports use elsewhere. This alone does not establish preservation of fixedLocations.
3. The backup's complete unchanged root dictionary, including metadata: an experimental hypothesis.

Experiment B may be attempted only when live version/model and backup-position validation succeed, a fresh binary snapshot and exact backup layout exist, the user's requested experiment authorizes the write, and recovery can actually be performed. A full-root command affects the WHOLE layout even if only one page is inspected. If the stated constraint is truly last-page-only, this command cannot satisfy it.

The brief's condition that only the last page have a deliberate gap is not met by a phone with gaps throughout. Do not remove those other gaps to make the test possible. Defer B and document the failed precondition. Do not run a full-root write under a misleading claim that it touches only the last page.

For a separately authorized experiment, inspect the current service implementation. Research suggests a raw send_plist setIconState request with an explicit nonempty dictionary and a bounded send timeout avoids waiting indefinitely for a reply. A returned send is not success. One attempt only, followed by new-connection readback, screenshots and a new backup to inspect pins. Use bounded verification retries. Do not resend on timeout.

Fresh snapshot before EVERY write, including rollback. On mismatch stop input, read/snapshot the actual state on a new connection, then perform the agreed rollback once if its prerequisites remain valid. Verify rollback on another new connection and restore gaps visually. If no reliable state can be read, report that rather than looping blindly. Never use a full backup restore to repair only icon placement.

Never call set_icon_state() without an explicit argument, send an empty dictionary, or use reload_icon_state / --reload.

## Touch routes

Mirroring remains the demonstrated fallback. The iPhone normally stays locked; the Mac must be unlocked. The research comparison table's claim that both must stay unlocked is incorrect for this workflow.

Try the provided UI controller. Control-click → Edit Home Screen is a candidate way to enter editing if that menu is actually observed. Otherwise use the known long-press route. Verify minus badges and Done visually. After swiping, inspect the settled page; an unchanged AX tree is not enough.

Use current screenshots to calibrate coordinates. The historical capture was 708×1564 with x centres 122/277/431/586 and y centres 273/441/608/775/943/1110. Never treat these as universal.

If alternative input is authorized, compile precise_drag.swift locally. It checks existing Accessibility access and sends one held drag to the visible Mirroring window. Do not grant broader access silently. Test a reversible move, screenshot before/after every drop, and stop on dialogs, Remove App/Delete App text or unintended folders. Never click an icon's minus badge. Avoid cross-page edge dragging; timing proved unreliable.

precise_drag needs Accessibility permission for the app that runs it, and the agent's own session may not have it. Then the agent's own screen control is the fallback: a held drag sent through its own mouse control, still one move at a time with screenshots.

Measured on 21 October 2026 (iPhone 16 Pro Max, iOS 27.0.1, macOS 26.6.2, the agent's own screen control over Mirroring): a press-and-hold on an icon from the normal Home Screen entered edit mode but did not carry the icon. Hold an empty cell first to enter edit mode, then drag the icon with a held drag: about 0.8 s hold, slow steps, about 1 s pause before release. That worked 3 of 3 times, at about 4.6 s per drag. Edit mode exits by itself after roughly half a minute with no input, so waiting for the owner's yes usually means holding an empty cell again. Mirroring pauses when idle; after Resume it shows page 1, so swipe back and screenshot the working page before the next drag.

HID touch is OPTIONAL AND EXPERIMENTAL. Current upstream code exposes touch_session/send_touchscreen, gated by an active media stream. The research reports iOS 27+ plus Developer Mode and a developer disk image. Check exact installed support; the tested phone meets the reported iOS version threshold, but Developer Mode, media-stream setup and icon-drag reliability were not tested. Developer Mode, new software and permission changes require agreement. Do not equate code availability with verified headless Home Screen editing.

XCUITest, ESP32, VoiceOver and simulator transfer are not default paths. Do not erase, supervise, restore or jailbreak a personal phone for aesthetics.

## Verification and interruption

After a permitted write, verify on a NEW connection. scripts/layout.py verify compares saved baseline/plan/readback offline, ignoring two volatile fields and empty-list placeholders. It establishes membership/order and protected content only, not positions.

Separately check screenshots of every affected page and, if available, fresh backup pins. Stop immediately on disconnection, Mac lock, lost editing mode or unexpected UI. Record completed pages and remaining moves. Resume from live observations, not a command replay. Exit editing and quit Mirroring when finished.
