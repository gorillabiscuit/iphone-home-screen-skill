# Requirements

Run `scripts/preflight.py` first. It checks everything below that a script can check, changes nothing, and says which routes are open. Run it with the Python that has pymobiledevice3 installed.

## To read the phone and plan (no changes to the phone)

- A Mac and one iPhone joined by a USB data cable. A USB 2 cable is fine for this. The phone must be unlocked with "Trust This Computer" accepted.
- Python and pymobiledevice3. The skill was tested with 11.36.0; other versions are untested and the preflight warns about them. Installing software needs the owner's agreement.
- Nothing else. `scripts/dry_run.py` reads the layout and reports; it writes nothing to the phone.

## To apply changes with iPhone Mirroring (the demonstrated route)

Confirmed against Apple's "iPhone Mirroring: Use your iPhone from your Mac" support page (shown as published 14 October 2026; re-read it before relying on this):
- macOS 15 (Sequoia) or later on a Mac with Apple silicon or an Apple T2 chip. The preflight checks this.
- iOS 18 or later on an iPhone with a passcode set. The preflight checks the iOS version.
- The same Apple Account on both devices, with two-factor authentication.
- Bluetooth and Wi-Fi on for both devices.
- The iPhone locked and near the Mac. Unlocking it, or quitting the iPhone Mirroring app, stops mirroring. It pauses itself after a period of inactivity.
- The Mac not using AirPlay, Sidecar or Internet Sharing. VPNs, third-party security software and a firewall set to block all incoming connections can cause timeouts.
- Only one Mac and one iPhone at a time.
- **Not available in the European Union**, according to Apple's page. In the EU, only the read, plan and dry-run steps apply; the Mirroring route cannot be used.

Also needed for the drag helper: Xcode Command Line Tools (a Swift compiler) and Accessibility permission for the app that runs it. Only the owner can grant that permission, in System Settings.

## Optional

- ffmpeg, for before/after images and video.
- iOS 27 or later plus Developer Mode, for the experimental touch-over-USB route. Developer Mode restarts the phone and lowers its security, so it needs the owner's explicit yes. Untested for icon moves.

## What the cable changes

The USB link speed is read from the Mac. USB 2 (480 Mb/s) is fast enough for page moves and slow for backups, wallpaper-heavy reads and video. The preflight shows the speed it got. A USB-C plug does not guarantee a fast cable.

## Where this has been tested

One phone: iPhone 16 Pro Max, iOS 27.0.1, with macOS 26.6.2 on an Apple-silicon Mac and pymobiledevice3 11.36.0. The original reorganisation used the same phone; the iOS version it ran on was not recorded. Nothing else has been tested. Add rows as testers report back:

| macOS | Mac chip | iPhone model | iOS | pymobiledevice3 | Read and plan | Mirroring moves | Notes |
|---|---|---|---|---|---|---|---|
| 26.6.2 | Apple silicon | iPhone 16 Pro Max | 27.0.1 | 11.36.0 | worked (read-only checks) | worked in the original project; not re-run | USB 2 cable only |
