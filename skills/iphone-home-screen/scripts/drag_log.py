#!/usr/bin/env python3
"""Time every icon move so the skill can quote real numbers.

Keeps one JSON line per move. `run` times a helper command (such as the
compiled precise_drag), `add` records a move made another way, `summary`
reports the timings and `estimate` projects a number of remaining moves.

Two timings are kept apart. drag_seconds is how long the move itself took.
The gap between consecutive moves also includes screenshots and checking,
so it is the better guide to how long a whole job takes. Long gaps (a break,
a stop to fix something) are counted separately, not averaged in.
"""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time

PAUSE_SECONDS = 300


def now():
    return datetime.now(timezone.utc)


def load(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def add_entry(path, seconds, ok=True, page=None, label=None, at=None):
    entry = {"at": (at or now()).isoformat(timespec="seconds"), "drag_seconds": round(seconds, 2),
             "ok": bool(ok), "page": page, "label": label}
    with Path(path).open("a") as handle:
        handle.write(json.dumps(entry) + "\n")
    return entry


def percentile(values, share):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(share * len(ordered)) - 1)]


def spread(values):
    if not values:
        return None
    return {"median": round(statistics.median(values), 2), "mean": round(statistics.mean(values), 2),
            "p90": round(percentile(values, 0.9), 2), "min": round(min(values), 2), "max": round(max(values), 2),
            "total": round(sum(values), 2), "samples": len(values)}


def summarize(entries, pause=PAUSE_SECONDS):
    times = sorted(datetime.fromisoformat(e["at"]) for e in entries)
    gaps = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
    active = [g for g in gaps if g <= pause]
    return {"moves": len(entries), "failed_moves": sum(not e["ok"] for e in entries),
            "drag_seconds": spread([e["drag_seconds"] for e in entries if e["ok"]]),
            "seconds_between_moves": spread(active),
            "pauses_over_threshold": len(gaps) - len(active), "pause_threshold_seconds": pause,
            "caveat": "Measured on this Mac, phone and cable only. Breaks longer than the threshold are not averaged in."}


def estimate(summary, moves):
    between = summary.get("seconds_between_moves")
    drag = summary.get("drag_seconds")
    if between and between["samples"] >= 3:
        basis, stat = "seconds between moves, which include checking", between
    elif drag:
        basis, stat = "drag time alone, so checking time is missing and the real figure is higher", drag
    else:
        return {"moves": moves, "estimate": "unmeasured", "reason": "No timed moves yet"}
    return {"moves": moves, "basis": basis, "minutes_median": round(moves * stat["median"] / 60, 1),
            "minutes_slow_case": round(moves * stat["p90"] / 60, 1)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    go = subs.add_parser("run", help="Run a helper command and log how long it took")
    go.add_argument("--log", required=True)
    go.add_argument("--page", type=int)
    go.add_argument("--label", help="Short note; do not put personal details in it")
    go.add_argument("helper", nargs=argparse.REMAINDER, help="-- then the command and its arguments")
    add = subs.add_parser("add", help="Record a move that was made another way")
    add.add_argument("--log", required=True)
    add.add_argument("--seconds", type=float, required=True)
    add.add_argument("--failed", action="store_true")
    add.add_argument("--page", type=int)
    add.add_argument("--label")
    total = subs.add_parser("summary", help="Report timings from a log")
    total.add_argument("--log", required=True)
    total.add_argument("--pause-threshold", type=int, default=PAUSE_SECONDS)
    plan = subs.add_parser("estimate", help="Project the time for a number of moves")
    plan.add_argument("--log", required=True)
    plan.add_argument("--moves", type=int, required=True)
    plan.add_argument("--pause-threshold", type=int, default=PAUSE_SECONDS)
    args = parser.parse_args()
    if args.command == "run":
        command = args.helper[1:] if args.helper[:1] == ["--"] else args.helper
        if not command:
            parser.error("Give the helper command after --")
        started = time.monotonic()
        code = subprocess.run(command).returncode
        print(json.dumps(add_entry(args.log, time.monotonic() - started, code == 0, args.page, args.label)))
        sys.exit(code)
    if args.command == "add":
        print(json.dumps(add_entry(args.log, args.seconds, not args.failed, args.page, args.label)))
        return
    summary = summarize(load(args.log), args.pause_threshold)
    print(json.dumps(summary if args.command == "summary" else estimate(summary, args.moves), indent=2))


if __name__ == "__main__":
    main()
