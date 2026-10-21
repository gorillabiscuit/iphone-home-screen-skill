# Testing the skill with other people

Most people will not want their phone rearranged. Test in three steps, and stop at the first one a tester is comfortable with.

## Step 1: no changes (anyone can do this)

1. Run `scripts/preflight.py --json` and keep the output.
2. Run `scripts/preview.py --live --out ~/home-screen-preview`. This reads the phone, draws pictures of the tester's own Home Screen now and sorted one way, and writes nothing to the phone. The tester can try other ways (`--strategy alphabetical`, favourites, their own groups) into a fresh folder each time. These pictures are the tester's payoff, so show them off.
3. Optionally run `scripts/dry_run.py --live --snapshot-out layout.plist --report-out report.json` for the counts.

What to send back: the preflight output, the summary.json from the preview, and what confused them. The pictures show the tester's apps, so they stay with the tester unless they choose to share them. The preflight lists the iPhone model and iOS version but not serial numbers. The layout file lists the person's apps, so ask them to share only the page and app counts unless they are happy to share more.

## Step 2: a few moves on one page (someone willing)

1. Take a screenshot of the page and save a snapshot first.
2. Move three or four icons, one at a time, checking a screenshot after each. Use the drag helper through `scripts/drag_log.py run` if it can run. It needs Accessibility permission, which the agent's session may not have; then use the agent's own screen control and record each move with `scripts/drag_log.py add`. Hold an empty cell first to enter edit mode, then drag the icon. In the 21 October 2026 test, a press-and-hold on an icon from the normal Home Screen entered edit mode but did not carry the icon. Holding an empty cell first, then a held drag (about 0.8 s hold, slow steps, about 1 s pause before release), worked 3 of 3 times at about 4.6 s per drag. Edit mode exits after roughly half a minute idle, and Mirroring pauses when idle and resumes on page 1, so expect to re-enter edit mode and swipe back to the page after waiting for the owner's yes.
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
