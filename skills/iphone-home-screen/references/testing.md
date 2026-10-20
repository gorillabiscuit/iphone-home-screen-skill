# Testing the skill with other people

Most people will not want their phone rearranged. Test in three steps, and stop at the first one a tester is comfortable with.

## Step 1: no changes (anyone can do this)

1. Run `scripts/preflight.py --json` and keep the output.
2. Run `scripts/preview.py --live --out ~/home-screen-preview`. This reads the phone, draws pictures of the tester's own Home Screen now and sorted one way, and writes nothing to the phone. The tester can try other ways (`--strategy alphabetical`, favourites, their own groups) into a fresh folder each time. These pictures are the tester's payoff, so show them off.
3. Optionally run `scripts/dry_run.py --live --snapshot-out layout.plist --report-out report.json` for the counts.

What to send back: the preflight output, the summary.json from the preview, and what confused them. The pictures show the tester's apps, so they stay with the tester unless they choose to share them. The preflight lists the iPhone model and iOS version but not serial numbers. The layout file lists the person's apps, so ask them to share only the page and app counts unless they are happy to share more.

## Step 2: a few moves on one page (someone willing)

1. Take a screenshot of the page and save a snapshot first.
2. Move three or four icons with the drag helper through `scripts/drag_log.py run`, one at a time, checking a screenshot after each.
3. Move them back, or leave them.

This produces the first real timing numbers and shows whether Mirroring and the helper work on their setup.

## Step 3: a full run (one or two volunteers)

Follow the main workflow with the timer running: every move goes through `drag_log.py`. Afterwards run `drag_log.py summary` and send the output.

## What to record

- macOS, Mac chip, iPhone model, iOS, pymobiledevice3 version (the preflight prints these).
- Did Mirroring connect? Did a held drag pick up an icon? Did swipes between pages work?
- The `drag_log.py summary` output. Quote "seconds between moves", not only "drag seconds": it includes the checking, which is most of the real time.
- Anything that went wrong, with what was on screen at the time.

Do not publish a time per move until at least two people on different setups have produced one.
