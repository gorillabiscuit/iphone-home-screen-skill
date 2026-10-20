# Evidence and experiment status

Evidence reviewed 2026-10-20. This is a capability boundary, not a claim that every route was tested.

## Demonstrated in the original project

- USB compact layout reads/writes and within-page Mirroring drags achieved the requested arrangement.
- A subsequent consolidation reduced 15 Home Screen pages to 13 and preserved inventory.
- Restoring that full saved plan from compact order requires 103 last-to-first drags under our movement model.
- The Mac pointer/window were occupied during those drags. Unlocking the phone or locking the Mac interrupted work.

## Measured in the research follow-up

- Initial missing-tooling/device blocks were resolved with user-approved installation of pymobiledevice3 11.36.0 in a persistent project-local environment and one USB phone.
- iPhone17,2 (iPhone 16 Pro Max), iOS 27.0.1, build 24A446. Grid metrics: four columns, six rows, 440×956 points.
- 166 current icons fetched in 2.14 seconds with zero failures. Offline border/glyph OKLab classification processed all 166; 39 review flags, nine multicolour. These are heuristics, not accuracy scores.
- Two independent wallpaper-preview reads returned identical 1320×2868 PNGs. They contain icons, badges and a placeholder widget. Their dark icon appearance differed from the light/coloured icons visible in Mirroring. Repeatability does not prove live appearance or a clean wallpaper.
- A filtered backup acquisition failed after 229.53 seconds with NotEnoughDiskSpaceError. The device requested about 187 GB, despite filtering for the layout file. Only metadata arrived; IconState did not. The temporary files were deleted. Existing backups and encryption settings were untouched.
- Second filtered backup attempt (2026-10-20, after the user freed disk space to 189 GB truly free): the device space check passed and the passcode was accepted. The transfer reached 5.2% in about nine minutes with only metadata saved, projecting to roughly three hours for the full transfer. It was stopped by the user, who would not leave the phone tied up. The phone negotiated 480 Mb/s (USB 2) on the three cable connections tried, including one supplied with an Insta360 camera. The partial files were deleted; no IconState arrived.
- Experiment A (reading fixedLocations from a backup) is therefore SKIPPED by the user's decision, not failed. Still unconfirmed: whether the backup holds exact cells for this layout, whether cell numbering starts at 0 or 1, the grid dimensions stored, and the iOS 27 extra-large widget key.
- Parser validation remains synthetic: no real fixedLocations or index base was confirmed.
- Final new-connection layout read matched the baseline after volatile-field normalisation; 13 pages unchanged. No phone writes were performed in the follow-up.

Dictionary writes (Experiment B, which also replaces the whole layout and could compact every gappy page, about 103 corrective drags) must stay off while Experiment A is unconfirmed. HID icon dragging remains untested. iOS eligibility alone does not establish HID prerequisites or reliable dragging. Do not treat the failed backup as proof that the layout file cannot be extracted from an adequately provisioned backup.

## Source evidence rechecked

- pymobiledevice3 springboard.py:
  https://raw.githubusercontent.com/doronz88/pymobiledevice3/master/pymobiledevice3/services/springboard.py
  The viewed implementation exposes compact reads, wallpaper preview, and an empty-dictionary default when no state is passed. reload_icon_state performs a write.
- pymobiledevice3 hid_service.py:
  https://raw.githubusercontent.com/doronz88/pymobiledevice3/master/pymobiledevice3/remote/core_device/hid_service.py
  The viewed implementation includes touch_session and send_touchscreen. It requires an active media stream. This is source evidence, not a Home Screen drag test.
- IconState's own project report:
  https://github.com/Jubstaaa/iconstate#what-the-device-will-and-will-not-do
  The author reports several failed gap encodings. This corroborates observed compaction but does not settle full backup-dictionary writes.
- Phosphor parser:
  https://github.com/momenbasel/Phosphor/blob/main/Sources/Phosphor/Services/HomeScreenExtractor.swift
  Supplied research cites this for metadata. Reopening failed during follow-up, so it was not independently reconfirmed.

## Hypotheses to retain as optional

- Backup listMetadata.fixedLocations exposes exact cells on the current phone.
- A full backup root dictionary might retain those pins through setIconState.
- HID touch may avoid monopolising the Mac, with version/security prerequisites.
- USB-fetched icon artwork may differ from current dark/tinted/clear Home Screen appearance.
- Identical wallpaper preview hashes may still reflect a stale cached preview.

Update this evidence file only after the corresponding measurement. Keep actual device identifiers, inventories, backup contents and screenshots outside the shareable skill.
