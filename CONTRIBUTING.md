# Contributing to POTATO Community Edition

POTATO is built as a clean, zero-dependency Python 3 foundation for the community to use and extend.

## Ideas for Pull Requests
- **TV Remote Keymap Profiles:** Expanded keycode support for generic IR, Bluetooth, and Smart TV remotes.
- **UI Themes & Accessibility Skins:** High-contrast living-room themes and responsive layouts.
- **Optional Hardware Transcode Profiles:** Opt-in `config.json` flags while keeping 0%-VRAM CPU-only as the default.
- **Modular Plugin Hooks:** Clean JSON/Python plugin loaders for local metadata, subtitles, or custom views.

## Rules
1. Keep core `potato.py` **zero external Python dependencies** (Python 3 standard library only).
2. Never hardcode private IPs, personal paths, API keys, RF/network scanning code, or third-party piracy links into the repository.
3. All community contributions to POTATO Community Edition are licensed under **GPL-3.0-or-later**.
