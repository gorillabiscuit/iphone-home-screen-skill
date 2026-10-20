# Testing the skill with other people

Most people will not want their phone rearranged. Test in three steps, and stop at the first one a tester is comfortable with.

## Step 1: no changes (anyone can do this)

1. Run `scripts/preflight.py --json` and keep the output.
2. Run `scripts/dry_run.py --live --snapshot-out layout.plist --report-out report.json`. This reads the phone and writes nothing to it.
3. Optionally build a plan and run the dry run again with `--plan plan.json`.

What to send back: the preflight output, the dry-run summary, and what confused them. The preflight lists the iPhone model and iOS version but not serial numbers. The layout file lists the person's apps, so ask them to share only the page and app counts unless they are happy to share more.

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
