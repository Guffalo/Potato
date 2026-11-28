# POTATO Remote & Keyboard Controls

POTATO uses a **deterministic, anti-sweep row/column D-pad grid engine** built from scratch in vanilla JavaScript — zero virtual mouse cursor, zero third-party focus libraries, and zero edge-to-edge jumping.

| Action | TV Remote / D-Pad | Keyboard |
| :--- | :--- | :--- |
| Move Selection (Single Tile) | Up / Down / Left / Right | Arrow Keys |
| Open / Play / Submit | OK / Select / Center | Enter |
| Go Back / Exit Fullscreen / Exit Input | Back | Escape |
| Play / Pause (Stream Player) | Media Play/Pause or Focus `Play / Pause` + OK | Space / Enter |
| Seek Back / Forward 15s | Media Rewind / Fast-Forward or Focus `⏪ -15s` / `⏩ +15s` | Media Keys / Buttons |
| Mute / Fullscreen | Focus `🔊 Mute` / `⛶ Fullscreen` + OK | `M` / `F` |
| Hidden POTATO Settings | Trace `↑ ↑ ↓ ↓ ← →` (or knock 5× on POTATO Emblem) | `↑ ↑ ↓ ↓ ← →` |

## Anti-Sweep Precision
- **Initializes on `DOMContentLoaded`** (never stalls waiting for video or live stream buffers).
- **Anti-sweep repeat throttle (`240ms` default, tunable in `/POTATO`):** holding a D-pad direction steps visibly one tile at a time so you can stop cleanly on any item between screen edges.
- **Hard row-edge clamping:** Left/Right stops cleanly at the row edges instead of jumping wildly across rows; use Up/Down to move between rows.
- **Triple-event capture (`keydown`, `keypress`, `keyup`):** prevents built-in TV browsers, TV Bro, and WebView spatial navigation from double-firing on a single remote press.
- **Form-safe typing:** Typing into `/setup` forms works naturally without D-pad interception.
- **Player-first focus:** `/watch` focuses **`⏯ Play / Pause`** by default (not `← Back`) and sets `tabindex="-1"` on `<video>` so native browser controls never trap your remote.
