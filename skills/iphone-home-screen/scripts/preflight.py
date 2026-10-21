#!/usr/bin/env python3
"""Check this Mac and a connected iPhone against the skill's requirements.

Changes nothing. It reads system information, lists USB phones and looks for
tools. It never pairs, installs, requests permissions or writes to the phone.
Run it with the Python that will run the other scripts, so the check sees the
same pymobiledevice3.
"""
import argparse
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from importlib import metadata

MIN_MACOS = (15, 0)         # iPhone Mirroring: Apple's published minimum (macOS Sequoia)
MIN_IOS_MIRRORING = (18, 0)  # iPhone Mirroring: Apple's published minimum
MIN_IOS_TOUCH = (27, 0)     # HID touch route: research report, untested for Home Screen drags
TESTED_PMD3 = "11.36.0"
VENV = "~/.iphone-home-screen"  # suggested private environment; installing still needs the owner's yes
INSTALL = f"python3 -m venv {VENV} && {VENV}/bin/pip install pymobiledevice3=={TESTED_PMD3} Pillow numpy"
MIRRORING_APP = Path("/System/Applications/iPhone Mirroring.app")


def parse_version(text):
    parts = re.findall(r"\d+", str(text or ""))
    return tuple(int(p) for p in parts[:3]) if parts else None


def meets(have, minimum):
    return have is not None and tuple(have) + (0,) * 3 >= tuple(minimum) + (0,) * (3 - len(minimum))


def run(command, timeout=20):
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def usb_speed():
    """Link speed of the iPhone's USB connection, or None when not shown."""
    text = run(["system_profiler", "SPUSBHostDataType"], 30)
    if not text:
        return None
    block = text.split("iPhone:", 1)
    match = re.search(r"Link Speed:\s*([^\n]+)", block[1]) if len(block) == 2 else None
    return match.group(1).strip() if match else None


def phones():
    """USB iPhones as dicts without serials or UDIDs, or None if the tool is missing."""
    text = run([sys.executable, "-m", "pymobiledevice3", "usbmux", "list"])
    if text is None:
        return None
    try:
        found = json.loads(text)
    except ValueError:
        return None
    return [{"ProductType": d.get("ProductType"), "ProductVersion": d.get("ProductVersion"),
             "BuildVersion": d.get("BuildVersion")}
            for d in found if d.get("ConnectionType") == "USB"]


def gather(drag_helper=None):
    facts = {"macos": platform.mac_ver()[0], "arch": platform.machine(),
             "python": sys.version_info[:3], "mirroring_app": MIRRORING_APP.exists(),
             "swiftc": bool(shutil.which("swiftc") or run(["xcrun", "--find", "swiftc"])),
             "ffmpeg": bool(shutil.which("ffmpeg")),
             "free_gb": round(shutil.disk_usage(Path.home()).free / 1e9, 1)}
    facts["t2"] = None
    if facts["arch"] != "arm64":
        bridge = run(["system_profiler", "SPiBridgeDataType"], 30)
        facts["t2"] = None if bridge is None else "T2" in bridge
    try:
        facts["pmd3"] = metadata.version("pymobiledevice3")
        facts["pmd3_requires_python"] = metadata.metadata("pymobiledevice3")["Requires-Python"]
    except metadata.PackageNotFoundError:
        facts["pmd3"] = facts["pmd3_requires_python"] = None
    facts["phones"] = phones() if facts["pmd3"] else None
    facts["usb_speed"] = usb_speed() if facts["phones"] else None
    facts["accessibility"] = None
    if drag_helper:
        out = run([drag_helper, "--check"])
        facts["accessibility"] = None if out is None else "True" in out
    return facts


def check(name, level, status, detail):
    return {"name": name, "level": level, "status": status, "detail": detail}


def python_ok(facts):
    wanted = re.match(r">=\s*(\d+)\.(\d+)", facts.get("pmd3_requires_python") or "")
    if not wanted:
        return None
    return tuple(facts["python"][:2]) >= (int(wanted.group(1)), int(wanted.group(2)))


def evaluate(facts):
    """Turn gathered facts into checks. Pure, so tests can feed made-up facts."""
    out = []
    mac = parse_version(facts.get("macos"))
    ok = meets(mac, MIN_MACOS)
    out.append(check("macOS", "required for Mirroring", "pass" if ok else "fail",
                     f"macOS {facts.get('macos') or 'unknown'}; iPhone Mirroring needs 15 or later"))
    if facts.get("arch") == "arm64" or facts.get("t2"):
        out.append(check("Mac chip", "required for Mirroring", "pass", "Apple silicon or T2"))
    elif facts.get("t2") is False:
        out.append(check("Mac chip", "required for Mirroring", "fail", "Intel Mac without a T2 chip cannot use iPhone Mirroring"))
    else:
        out.append(check("Mac chip", "required for Mirroring", "warn", "Could not tell whether this Mac has a T2 chip"))
    out.append(check("iPhone Mirroring app", "required for Mirroring", "pass" if facts.get("mirroring_app") else "fail",
                     "Found" if facts.get("mirroring_app") else "Not found; it ships with macOS 15 and later"))
    version = facts.get("pmd3")
    if not version:
        out.append(check("pymobiledevice3", "required for reading the phone", "fail",
                         "Not installed in this Python. Installing needs the owner's agreement. Offline planning from a saved snapshot still works. "
                         f"Suggested install, after which every script runs with {VENV}/bin/python: {INSTALL}"))
    else:
        note = "" if version == TESTED_PMD3 else f"; the skill was tested with {TESTED_PMD3}"
        out.append(check("pymobiledevice3", "required for reading the phone", "pass" if version == TESTED_PMD3 else "warn",
                         f"Version {version}{note}"))
        if python_ok(facts) is False:
            out.append(check("Python", "required for reading the phone", "fail",
                             f"Python {'.'.join(map(str, facts['python']))} is older than pymobiledevice3 needs ({facts['pmd3_requires_python']})"))
    out.append(check("Swift compiler", "optional (drag helper)", "pass" if facts.get("swiftc") else "warn",
                     "Found" if facts.get("swiftc") else "Missing. The drag helper needs Xcode Command Line Tools, which needs the owner's agreement."))
    access = facts.get("accessibility")
    out.append(check("Accessibility for drag helper", "optional (drag helper)",
                     "skip" if access is None else "pass" if access else "warn",
                     "Compile the helper, then run this check again with --drag-helper" if access is None
                     else "Granted" if access else "Not granted. Only the owner can grant it, in System Settings."))
    out.append(check("ffmpeg", "optional (before/after media)", "pass" if facts.get("ffmpeg") else "skip",
                     "Found" if facts.get("ffmpeg") else "Not found; only needed for images and video"))
    found = facts.get("phones")
    if found is None:
        out.append(check("iPhone", "required for reading the phone", "skip", "Cannot list phones without pymobiledevice3"))
    elif len(found) != 1:
        out.append(check("iPhone", "required for reading the phone", "fail",
                         "No USB iPhone found. Plug it in, unlock it and tap Trust." if not found
                         else f"{len(found)} USB phones found. Unplug all but the one to work on."))
    else:
        phone = found[0]
        out.append(check("iPhone", "required for reading the phone", "pass",
                         f"{phone['ProductType']}, iOS {phone['ProductVersion']} (build {phone['BuildVersion']})"))
        ios = parse_version(phone["ProductVersion"])
        out.append(check("iOS for Mirroring", "required for Mirroring", "pass" if meets(ios, MIN_IOS_MIRRORING) else "fail",
                         "iPhone Mirroring needs iOS 18 or later"))
        touch = meets(ios, MIN_IOS_TOUCH)
        out.append(check("Touch over USB (experimental)", "optional", "info",
                         "iOS 27 or later: possible, untested for icon moves, needs Developer Mode (restarts the phone and lowers its security)"
                         if touch else "Needs iOS 27 or later; not available on this phone"))
        speed = facts.get("usb_speed")
        if speed:
            slow = speed.startswith("480")
            out.append(check("USB speed", "optional", "warn" if slow else "pass",
                             f"{speed}. " + ("USB 2 speed: fine for page moves, very slow for backups and video" if slow else "Fast enough for backups")))
    out.append(check("Free disk space", "info", "info", f"{facts.get('free_gb')} GB free in the home folder (matters only for backups)"))
    out.append(check("Check yourself", "required for Mirroring", "info",
                     "Same Apple Account with two-factor on both devices; passcode set on the iPhone; Bluetooth and Wi-Fi on for both; "
                     "iPhone locked and near the Mac, Mac unlocked; no AirPlay, Sidecar or Internet Sharing; "
                     "iPhone Mirroring is unavailable in the European Union per Apple (if the app says it is unavailable, that route cannot be used)"))
    return out


def readiness(checks):
    by = {c["name"]: c["status"] for c in checks}
    reading = all(by.get(n) == "pass" or by.get(n) == "warn" for n in ("pymobiledevice3", "iPhone"))
    mirror = all(by.get(n) == "pass" for n in ("macOS", "Mac chip", "iPhone Mirroring app", "iOS for Mirroring"))
    return {"can_read_and_plan": reading, "can_apply_with_mirroring": mirror and reading,
            "changes_made": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drag-helper", help="Path to the compiled precise_drag binary, to check Accessibility")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    checks = evaluate(gather(args.drag_helper))
    ready = readiness(checks)
    if args.json:
        print(json.dumps({"checks": checks, "readiness": ready}, indent=2))
    else:
        for c in checks:
            print(f"{c['status'].upper():5} {c['name']} ({c['level']}): {c['detail']}")
        print()
        print("Can read the phone and plan:", "yes" if ready["can_read_and_plan"] else "no")
        print("Can apply with Mirroring:   ", "yes" if ready["can_apply_with_mirroring"] else "no")
        print("No changes were made to the Mac or the phone.")
    sys.exit(1 if any(c["status"] == "fail" and c["level"].startswith("required") for c in checks) else 0)


if __name__ == "__main__":
    main()
