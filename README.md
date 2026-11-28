<p align="center">
  <img src="assets/potato_icon.png" alt="POTATO Icon" width="165">
</p>

<h1 align="center">POTATO — Community Edition</h1>

<p align="center">
  <b>No subscriptions. No accounts. No cloud middlemen. No tracking. No bloat.</b><br>
  <b>A standalone, zero-dependency LAN media hub, TV-remote transmitter, public archive launcher, and offline Web Audio synthesizer built purely in the Python 3 standard library.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License: GPLv3">
  <img src="https://img.shields.io/badge/Author-Guffalo-d97706.svg" alt="Author: Guffalo">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/Dependencies-Zero-2ea043.svg" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/Idle%20VRAM-0%25-ea580c.svg" alt="0% VRAM Idle">
  <img src="https://img.shields.io/badge/Telemetry-Zero-10b981.svg" alt="Zero Telemetry">
  <img src="https://img.shields.io/badge/OS-Windows%20%7C%20Linux%20%7C%20macOS-5865F2.svg" alt="Cross Platform">
</p>

---

## Why POTATO Exists

Modern home media stacks routinely demand gigabytes of containers, background GPU polling, cloud accounts, and mandatory telemetry just to stream a local video across your living room.

**POTATO** proves you can deliver a fast, living-room-ready LAN media hub, TV-remote engine, Wi-Fi uploader, QR generator, and offline audio synthesizer in a **single pure-Python file** with **zero external packages** and **0% idle VRAM**.

---

## Quick Start (30 Seconds, Zero Dependencies)

1. **Clone or download POTATO:**
   ```bash
   git clone https://github.com/Guffalo/Potato.git
   cd Potato
   ```
2. **Launch POTATO:**
   - **Windows:** Double-click **`START_POTATO.bat`**
   - **macOS / Linux:** Run **`./start_potato.sh`** (or `python3 potato.py --open`)
3. **Open on any browser, phone, tablet, streaming stick, or Smart TV on your LAN:**
   - The **Live URL** button in the top bar auto-populates your active LAN address (`http://<YOUR-LAN-IP>:8789/` or `http://potato.local:8789/`).

---

## Key Engineering Highlights

- **Ultra-Lite Zero-JS Mode (`/lite` + `--lite`):** Serves `< 3 KB` pure semantic HTML with **zero JavaScript, zero images, and zero CSS Grid** — built to fly on 15-year-old Smart TVs, legacy streaming sticks, low-RAM single-board computers, and text browsers (`python3 potato.py --lite`).
- **Zero External Dependencies:** Pure Python 3 standard library — no `pip install`, no Docker, no cloud accounts, no external CDNs.
- **Deterministic Anti-Sweep TV-Remote D-Pad Engine:** Custom row/column grid navigation with debounce, repeat pacing, and hard row-edge clamping so TV remotes never overshoot tiles. See [docs/REMOTE_CONTROLS.md](docs/REMOTE_CONTROLS.md).
- **Remote-First `/watch` Player:** Instant focus on Play/Pause, `±15s` seek, Mute, Fullscreen, HTTP 206 byte-range seeking, and optional CPU-only `ffmpeg` MP4 relay (0% GPU/VRAM).
- **Zero-Code Setup & Wi-Fi Uploads (`/setup`):** Point at local media folders, upload videos/audio/`.m3u` playlists over Wi-Fi, add custom tiles, and export a LAN M3U feed (`/playlist.m3u`).
- **Offline Web Audio Tone Generator (`/freqs`):** Live browser synthesizer + oscilloscope (`20–1200 Hz` carrier, `0–40 Hz` binaural beat) with pure-Python `.WAV` export to your library.
- **Pure-Python SVG QR Codes & LAN Discovery:** Zero-dependency SVG QR generator (`/qr.svg`) plus LAN-only mDNS (`potato.local`) and UPnP/SSDP (`/device.xml`).
- **Hardened LAN Security:** SSRF private-IP/redirect guards on proxy routes, CSRF tokens + Same-Origin checks on POST endpoints, symlink-escape protection, and zero telemetry.

---

## Endpoints

- `/` — Home hub
- `/lite` — `< 3 KB` Zero-JS Ultra-Lite interface for low-power & legacy devices
- `/library` — Paginated & searchable local media library
- `/playlists` — Searchable built-in M3U stream index
- `/open` — Public archives, shortwave SDR, public-domain cinema & open-source tools
- `/freqs` — Offline Web Audio tone generator & `.WAV` exporter
- `/setup` — Browser setup, Wi-Fi upload & folder configuration
- `/watch` — TV-remote media player
- `/status` & `/health` — Server status, library rescan, and JSON health check
- `/manifest.json` — PWA home-screen manifest

---

## Third-Party Open-Source Credits

POTATO does **not** bundle or claim ownership of any third-party software, radio networks, or archives. External directory buttons credit their original creators:

- **TV Bro** — [truefedex (Fedir Tsapana)](https://github.com/truefedex/tv-bro) (GPL-3.0)
- **JS8Call** — [Jordan Sherer (KN4CRD)](http://js8call.com/) & contributors (GPL-3.0)
- **Kodi** — [XBMC Foundation](https://kodi.tv/) (GPL)
- **VLC Media Player** — [VideoLAN](https://www.videolan.org/vlc/) (GPL)
- **Jellyfin** — [Jellyfin Contributors](https://jellyfin.org/) (GPL)
- **NewPipe** — [Team NewPipe](https://newpipe.net/) (GPL)
- **FreeTube** — [FreeTube Contributors](https://freetubeapp.io/) (AGPL)
- **WikiFlix** — [Magnus Manske / Wikimedia](https://wikiflix.toolforge.org/)
- **WebSDR & Twente WebSDR** — [Pieter-Tjerk de Boer (PA3FWM)](http://www.websdr.org/)
- **PeerTube / SepiaSearch** — [Framasoft](https://sepiasearch.org/) (AGPL)
- **Blender Open Movies** — [Blender Foundation](https://video.blender.org/) (CC-BY)
- **SomaFM** — [SomaFM](https://somafm.com/) (listener-supported)

---

## Author, License & Commercial Inquiries

**Created by Christopher James Guffey ("Guffalo") — Independent Systems Architect, Colorado.**

- **Open-Source License (POTATO Community Edition):** Copyright (C) 2026 Christopher James Guffey ("Guffalo"). Released under the **GNU General Public License v3.0 or later** ([LICENSE](LICENSE)). Anyone is free to download, run, study, modify, and share POTATO Community Edition provided that author copyright notices, license terms (GPLv3 §§ 4, 5(a), 7(b)), and third-party credits remain intact.
- **Commercial / OEM Licensing & Technical Partnerships:** POTATO Community Edition is a standalone open-source public release. Proprietary commercial licenses, custom embedded/edge systems engineering, and strategic R&D partnerships are available separately under NDA — open a GitHub issue or reach out via [github.com/Guffalo](https://github.com/Guffalo).
