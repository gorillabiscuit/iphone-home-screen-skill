// Prepared only. Do not run without the user's explicit approval for alternate UI input.
// Usage: precise_drag fromX fromY toX toY screenshotWidth screenshotHeight
import Foundation
import AppKit
import CoreGraphics

if CommandLine.arguments.dropFirst().first == "--check" {
    print("Accessibility available: \(AXIsProcessTrusted())")
    exit(0)
}

guard CommandLine.arguments.count == 7,
      let fx = Double(CommandLine.arguments[1]),
      let fy = Double(CommandLine.arguments[2]),
      let tx = Double(CommandLine.arguments[3]),
      let ty = Double(CommandLine.arguments[4]),
      let sw = Double(CommandLine.arguments[5]),
      let sh = Double(CommandLine.arguments[6]), sw > 0, sh > 0 else {
    fatalError("Expected six numeric arguments")
}
guard AXIsProcessTrusted() else {
    print("Accessibility access is unavailable. No input sent; no permission requested or changed.")
    exit(2)
}
guard let app = NSRunningApplication.runningApplications(withBundleIdentifier: "com.apple.ScreenContinuity").first else {
    print("iPhone Mirroring is not running. No input sent."); exit(3)
}
let info = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
let windows = info.filter { ($0[kCGWindowOwnerPID as String] as? Int32) == app.processIdentifier && ($0[kCGWindowLayer as String] as? Int) == 0 }
guard windows.count == 1, let b = windows[0][kCGWindowBounds as String] as? [String: Any],
      let bounds = CGRect(dictionaryRepresentation: b as CFDictionary), bounds.width > 200, bounds.height > 400 else {
    print("Expected one visible iPhone Mirroring window. No input sent."); exit(4)
}
let from = CGPoint(x: bounds.minX + fx / sw * bounds.width, y: bounds.minY + fy / sh * bounds.height)
let to = CGPoint(x: bounds.minX + tx / sw * bounds.width, y: bounds.minY + ty / sh * bounds.height)
guard bounds.contains(from), bounds.contains(to) else { exit(5) }
app.activate(options: [])
Thread.sleep(forTimeInterval: 0.3)
let source = CGEventSource(stateID: .hidSystemState)
func send(_ type: CGEventType, _ p: CGPoint) {
    guard let event = CGEvent(mouseEventSource: source, mouseType: type, mouseCursorPosition: p, mouseButton: .left) else { return }
    event.post(tap: .cghidEventTap)
}
send(.mouseMoved, from)
send(.leftMouseDown, from)
Thread.sleep(forTimeInterval: 0.85)
for step in 1...60 {
    let t = Double(step) / 60.0
    send(.leftMouseDragged, CGPoint(x: from.x+(to.x-from.x)*t, y: from.y+(to.y-from.y)*t))
    Thread.sleep(forTimeInterval: 0.018)
}
Thread.sleep(forTimeInterval: 0.4)
send(.leftMouseUp, to)
print("One held drag completed. Verify the result visually before any further movement.")
