#!/usr/bin/env python3
"""
POTATO — Zero-Dependency LAN Media Hub & TV-Remote Transmitter
==============================================================================
Copyright (C) 2026 Christopher James Guffey ("Guffalo") <https://github.com/Guffalo/Potato>
License: GNU General Public License v3.0 or later (GPL-3.0-or-later)
Standalone Zero-Dependency LAN Media Hub

This program is free software: anyone may use, run, study, share, and modify
it freely under the terms of the GNU General Public License v3.0 or later,
provided credit to Guffalo and this license/build notice remain intact.

100% original Python 3 standard library implementation:
- Zero external Python dependencies, zero third-party JS frameworks, zero CDNs.
- Easy browser-based Setup & Upload (/setup) — no JSON editing required.
- Anti-sweep deterministic TV-remote D-pad engine (stops cleanly on every tile).
- Direct HTTP 206 byte-range seek + optional CPU-only ffmpeg MP4 relay (0% VRAM).
- Chunked streaming proxy (never buffers live streams or large files into RAM).
- Strict folder whitelist & path-traversal protection (HTTP 404 outside vault).
- Clean dark-mode TV-remote UI with zero external CDNs.
"""
import argparse
import array
import hashlib
import hmac
import html as html_lib
import http.server
import io
import ipaddress
import json
import math
import mimetypes
import os
import platform
import re
import secrets
import shutil
import socket
import socketserver
import ssl
import struct
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import wave
import webbrowser

CSRF_TOKEN = secrets.token_urlsafe(32)

POTATO_NAME = "POTATO"
POTATO_VERSION = "3.4"
POTATO_AUTHOR = "Christopher James Guffey (Guffalo)"
POTATO_LICENSE = "GPL-3.0-or-later"
POTATO_REPO = "https://github.com/Guffalo/Potato"
POTATO_TAG = "POTATO-LAN-HUB"
POTATO_BUILD_ID = hashlib.sha256(
    f"{POTATO_NAME}|{POTATO_AUTHOR}|{POTATO_LICENSE}|{POTATO_TAG}|{POTATO_REPO}".encode("utf-8")
).hexdigest()

MDNS_GROUP = "224.0.0.251"
MDNS_PORT = 5353
SSDP_GROUP = "239.255.255.250"
SSDP_PORT = 1900
MDNS_HOST = "potato.local"
POTATO_UUID = hashlib.sha256(f"{POTATO_TAG}|{socket.gethostname()}".encode("utf-8")).hexdigest()[:32]
POTATO_UDN = f"uuid:{POTATO_UUID[:8]}-{POTATO_UUID[8:12]}-{POTATO_UUID[12:16]}-{POTATO_UUID[16:20]}-{POTATO_UUID[20:32]}"

IS_WIN = platform.system().lower().startswith("win")
CREATE_NO_WINDOW = 0x08000000 if IS_WIN else 0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
POTATO_ICON_PATH = os.path.join(ASSETS_DIR, "potato_icon.png")
POTATO_ICON_192_PATH = os.path.join(ASSETS_DIR, "potato_icon_192.png")

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts", ".wmv", ".mpg", ".mpeg"}
AUDIO_EXTS = {".mp3", ".aac", ".ogg", ".flac", ".wav", ".m4a", ".opus"}
PLAYLIST_EXTS = {".m3u", ".m3u8"}
UPLOAD_ALLOWED_EXTS = VIDEO_EXTS | AUDIO_EXTS | PLAYLIST_EXTS
BROWSER_NATIVE_EXTS = {".mp4", ".m4v", ".webm", ".mp3", ".ogg", ".wav", ".m4a"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB safety cap

# Crisp fallback SVG raw potato icon (used if PNG asset is missing)
RAW_POTATO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
    '<rect width="128" height="128" rx="26" fill="#0d0c09"/>'
    '<defs><radialGradient id="p" cx="40%" cy="35%" r="65%">'
    '<stop offset="0%" stop-color="#e3b673"/>'
    '<stop offset="55%" stop-color="#b88142"/>'
    '<stop offset="100%" stop-color="#6b441f"/>'
    "</radialGradient></defs>"
    '<ellipse cx="64" cy="65" rx="44" ry="33" transform="rotate(-14 64 65)" fill="url(#p)" stroke="#4a2e14" stroke-width="2.5"/>'
    '<circle cx="46" cy="57" r="2.6" fill="#4a2e14" opacity="0.7"/>'
    '<circle cx="77" cy="51" r="2.2" fill="#4a2e14" opacity="0.65"/>'
    '<circle cx="67" cy="74" r="2.8" fill="#4a2e14" opacity="0.68"/>'
    '<circle cx="88" cy="67" r="2.0" fill="#4a2e14" opacity="0.6"/>'
    '<circle cx="42" cy="74" r="2.1" fill="#4a2e14" opacity="0.58"/>'
    "</svg>"
)

# ==============================================================================
# 100% LEGAL, PUBLIC-ARCHIVE, OPEN-RADIO & FOSS VERIFIED DIRECTORY
# Zero politics. Zero hate. Zero piracy. Every URL live-verified.
# Format: (Title, URL, AccentColor, Badge, Quick-Reference Summary)
# ==============================================================================
OPEN_WEIRD_RABBIT_HOLES = [
    ("Art Bell — Ultimate Coast Vault", "https://archive.org/details/the-ultimate-art-bell-collection_202201", "#a855f7", "WEIRD", "Late-night high-strangeness, UFOs & paranormal radio archive · archive.org"),
    ("UFO & Declassified Docs Vault", "https://archive.org/search?query=ufo+declassified&and%5B%5D=mediatype%3A%22movies%22", "#14b8a6", "UFO", "Declassified footage, UFO & unexplained phenomena documentaries · archive.org"),
    ("Tartaria & Lost Civilizations", "https://archive.org/search?query=tartaria+OR+mud+flood+OR+%22lost+civilization%22&and%5B%5D=mediatype%3A%22movies%22", "#f59e0b", "RABBIT", "Alternate history, Tartaria, mud-flood & ancient-mystery videos · archive.org"),
    ("Alternate Realities & High Strangeness", "https://archive.org/search?query=%22alternate+reality%22+OR+paranormal+documentary&and%5B%5D=mediatype%3A%22movies%22", "#ec4899", "STRANGE", "Reality glitches, simulation theory & paranormal documentaries · archive.org"),
    ("Mystery & Underground Docs", "https://archive.org/details/movies?tab=collection&query=conspiracy+OR+mystery+documentary", "#eab308", "DOCS", "Independent mystery, deep-dive & underground documentary vault · archive.org"),
    ("Internet Archive — VHS Vault", "https://archive.org/details/vhsvault", "#f97316", "VHS", "Weird forgotten late-night VHS tapes, oddities & bizarre broadcasts · archive.org"),
    ("Documentary Heaven (Free Docs)", "https://documentaryheaven.com/", "#10b981", "DOCS", "Curated free documentaries: mystery, mind, science & weird world · documentaryheaven.com"),
    ("Top Documentary Films", "https://topdocumentaryfilms.com/", "#22c55e", "DOCS", "Thousands of full free documentaries across mystery & unexplained · topdocumentaryfilms.com"),
    ("I Have No TV (Free Docs)", "https://ihavenotv.com/", "#06b6d4", "DOCS", "Hand-picked full-length independent & mind-bending documentaries · ihavenotv.com"),
    ("UbuWeb — Underground Avant-Garde", "https://ubu.com/film/", "#8b5cf6", "WEIRD", "Surreal, experimental & underground film archive since 1996 · ubu.com"),
    ("RareFilmm — Obscure Cinema Vault", "https://rarefilmm.com/", "#ef4444", "RARE", "Hard-to-find cult, surreal & forgotten international cinema · rarefilmm.com"),
    ("MyRetroTVs — Time Machine TV", "https://www.myretrotvs.com/", "#38bdf8", "RETRO", "Channel-surf 1950s–2000s nostalgic static, commercials & oddities · myretrotvs.com"),
]

OPEN_SHORTWAVE_RADIO = [
    ("Global WebSDR Directory", "http://www.websdr.org/", "#10b981", "SDR", "By PA3FWM (Pieter-Tjerk de Boer) · Live worldwide browser HF/WebSDR directory · websdr.org"),
    ("Global KiwiSDR Shortwave Map", "http://rx.linkfanel.net/", "#38bdf8", "SDR", "By Linkfanel & KiwiSDR community · Interactive live shortwave receiver map · rx.linkfanel.net"),
    ("Twente WebSDR (0–30 MHz Live)", "http://websdr.ewi.utwente.nl:8901/", "#3b82f6", "SDR", "By University of Twente / PA3FWM · Live wideband 0–30 MHz shortwave tuner · utwente.nl"),
    ("Priyom — Numbers Stations", "https://priyom.org/", "#ef4444", "SIGNAL", "By Priyom.org researchers · Shortwave numbers stations schedules & live logs · priyom.org"),
    ("HF Underground — Pirate & Oddball SW", "https://www.hfunderground.com/board/", "#f97316", "SIGNAL", "By HF Underground community · Shortwave pirate & mystery signal reports · hfunderground.com"),
    ("JS8Call — Off-Grid Digital HF", "http://js8call.com/", "#14b8a6", "RADIO", "By Jordan Sherer (KN4CRD) & JS8Call team (GPLv3) · Weak-signal HF digital mode · js8call.com"),
    ("SomaFM (Commercial-Free Radio)", "https://somafm.com/", "#10b981", "RADIO", "By SomaFM (listener-supported) · 30+ ambient, space, dark-zone & hacker feeds · somafm.com"),
    ("Radio Garden (Live World Radio)", "https://radio.garden/", "#22c55e", "RADIO", "By Radio Garden · Spin a 3D globe to tune thousands of live local stations · radio.garden"),
    ("Nightride FM (24/7 Synthwave)", "https://nightride.fm/", "#ec4899", "RADIO", "By Nightride FM · Commercial-free 24/7 synthwave, darksynth & cyberpunk radio · nightride.fm"),
    ("NTS Radio (24/7 Underground)", "https://www.nts.live/", "#a855f7", "RADIO", "By NTS Radio · Two 24/7 live underground music streams & weird late-night mixes · nts.live"),
    ("X Minus One — Classic Sci-Fi Radio", "https://archive.org/details/OTRR_X_Minus_One_Singles", "#eab308", "SCI-FI", "Preserved by OTRR / Internet Archive · 1950s sci-fi & alternate-reality radio · archive.org"),
    ("Internet Archive — Old Time Radio", "https://archive.org/details/oldtimeradio", "#ca8a04", "AUDIO", "Hosted by Internet Archive · Classic 1930s–1960s mystery, horror & noir radio · archive.org"),
    ("Internet Archive — Live Concerts", "https://archive.org/details/etree", "#8b5cf6", "MUSIC", "Hosted by Internet Archive / etree · 250,000+ free taper-friendly live concerts · archive.org"),
]

OPEN_CINEMA_VIDEO = [
    ("Internet Archive — Feature Films", "https://archive.org/details/feature_films", "#f59e0b", "CINEMA", "Hosted by Internet Archive · Thousands of free public-domain feature films · archive.org"),
    ("Internet Archive — Prelinger Archives", "https://archive.org/details/prelinger", "#d97706", "ARCHIVE", "By Rick Prelinger / Internet Archive · Vintage 1920s–1980s ephemeral films · archive.org"),
    ("Internet Archive — Sci-Fi & Horror", "https://archive.org/details/SciFi_Horror", "#14b8a6", "CINEMA", "Hosted by Internet Archive · Classic public-domain sci-fi & horror vault · archive.org"),
    ("WikiFlix (Wikimedia Public Domain)", "https://wikiflix.toolforge.org/", "#06b6d4", "CINEMA", "By Magnus Manske / Wikimedia Toolforge · Zero-ad public-domain cinema catalog · toolforge.org"),
    ("Public Domain Movie Vault", "https://publicdomainmovie.net/", "#0ea5e9", "CINEMA", "By PublicDomainMovie.net · Curated classic films with expired copyrights · publicdomainmovie.net"),
    ("Open Culture — Free Classics", "https://www.openculture.com/freemoviesonline", "#22c55e", "INDEX", "By Open Culture · 4,000+ indexed free classics, noir, westerns & indies · openculture.com"),
    ("NFB Canada — Free Films & Docs", "https://www.nfb.ca/", "#ef4444", "DOCS", "By National Film Board of Canada · Free documentaries & animation · nfb.ca"),
    ("NASA+ Live & Space Media", "https://plus.nasa.gov/", "#3b82f6", "SPACE", "By NASA · Official live launches, ISS Earth feeds & space docs · plus.nasa.gov"),
    ("Blender Open Movies (CC-BY)", "https://video.blender.org/", "#f97316", "CC-BY", "By Blender Foundation (CC-BY) · Free Creative Commons 3D animated films · video.blender.org"),
    ("SepiaSearch (PeerTube Index)", "https://sepiasearch.org/", "#eab308", "SEARCH", "By Framasoft / PeerTube (AGPL) · Search 1,000+ independent video servers · sepiasearch.org"),
    ("TILvids (PeerTube Curious Minds)", "https://tilvids.com/", "#f59e0b", "EDU", "By TILvids community · Ad-free curious-mind, science & history PeerTube · tilvids.com"),
    ("MakerTube (Shop, DIY & Welding)", "https://makertube.net/", "#ea580c", "MAKER", "By MakerTube community · Garage, fabrication, welding & off-grid DIY · makertube.net"),
    ("Diode.zone (Hardware & Radio Tech)", "https://diode.zone/", "#22c55e", "TECH", "By Diode.zone community · Electronics, Linux, ham radio & hardware builds · diode.zone"),
]

OPEN_FOSS_PLAYERS = [
    ("TV Bro — Open-Source TV Browser (GPL)", "https://github.com/truefedex/tv-bro/releases", "#ffd166", "TV APP", "By truefedex (Fedir Tsapana, GPLv3) · Android TV & TV Streaming Stick browser · github.com/truefedex/tv-bro"),
    ("Kodi Media Center (GPL)", "https://kodi.tv/", "#0284c7", "KODI", "By XBMC Foundation (GPL) · Living-room home theater (connects to /playlist.m3u) · kodi.tv"),
    ("Kodi Official Add-ons Catalog", "https://kodi.tv/addons/", "#38bdf8", "ADDONS", "By XBMC Foundation & Kodi devs · Official free Kodi add-on repository · kodi.tv/addons"),
    ("VLC Media Player (GPL)", "https://www.videolan.org/vlc/", "#f97316", "FOSS", "By VideoLAN (GPL) · Open-source player for LAN streams & M3U playlists · videolan.org"),
    ("Jellyfin Media Server (GPL)", "https://jellyfin.org/", "#7c3aed", "FOSS", "By Jellyfin Contributors (GPL) · 100% free self-hosted media server · jellyfin.org"),
    ("NewPipe Android Client (GPL)", "https://newpipe.net/", "#e11d48", "FOSS", "By Team NewPipe (GPL) · Lightweight open-source privacy media client · newpipe.net"),
    ("FreeTube Desktop Client (AGPL)", "https://freetubeapp.io/", "#be123c", "FOSS", "By FreeTube Contributors (AGPL) · Private open-source desktop video player · freetubeapp.io"),
]

OPEN_ALL = OPEN_WEIRD_RABBIT_HOLES + OPEN_SHORTWAVE_RADIO + OPEN_CINEMA_VIDEO + OPEN_FOSS_PLAYERS

# Meditation, Brainwave Entrainment & Pure Solfeggio Frequency Presets
# Format: (id, name, base_hz, beat_hz, wave_type, color, badge, best_for, directions)
FREQ_PRESETS = [
    ("delta_sleep", "Deep Sleep — Delta (2.5 Hz)", 174.0, 2.5, "sine", "#6366f1", "SLEEP",
     "Falling asleep, deep physical rest & nighttime recovery",
     "Use stereo headphones at low volume (15–25%) with a 30–60 min sleep timer."),
    ("theta_meditate", "Deep Meditation — Theta (6 Hz)", 216.0, 6.0, "sine", "#a855f7", "MEDITATE",
     "Quiet eyes-closed meditation, unwinding heavy stress & lucid dreaming",
     "Sit or lie comfortably with headphones, breathe slow (4s in / 6s out) for 20 min."),
    ("schumann_earth", "Schumann Earth Resonance (7.83 Hz)", 136.1, 7.83, "drone", "#10b981", "EARTH",
     "Grounding, nervous-system reset & calm centered presence",
     "Earth's natural electromagnetic pulse on a 136.1 Hz Om carrier — great on headphones or low speaker drone."),
    ("alpha_flow", "Relaxed Focus & Flow — Alpha (10 Hz)", 256.0, 10.0, "sine", "#14b8a6", "FLOW",
     "Calm reading, decompressing after work & creative flow without drowsiness",
     "Works great in the background at low volume while sketching, reading, or winding down."),
    ("beta_study", "Alert Focus — Low Beta (16 Hz)", 320.0, 16.0, "triangle", "#3b82f6", "FOCUS",
     "Tinkering, problem solving, studying & steady concentration without jitters",
     "Use for 20–40 min work sprints; switch back to Alpha or silence before bedtime."),
    ("gamma_clarity", "Peak Clarity — Gamma (40 Hz)", 432.0, 40.0, "sine", "#f59e0b", "CLARITY",
     "Short bursts of sharp mental clarity, insight & active recall",
     "Keep sessions brief (10–20 min) at comfortable low volume during daytime."),
    ("pure_174", "174 Hz — Grounding Foundation", 174.0, 0.0, "drone", "#8b5cf6", "174 HZ",
     "Physical tension release & deep body grounding (no headphones needed)",
     "Pure mono/room harmonic — plays cleanly on TV speakers, soundbars, or headphones."),
    ("pure_285", "285 Hz — Quiet Stillness", 285.0, 0.0, "sine", "#06b6d4", "285 HZ",
     "Calm recovery, quiet breathing & resetting a tired mind",
     "Smooth pure sine wave — ideal for 15–30 min quiet rest on speakers or headphones."),
    ("pure_396", "396 Hz — Release Mental Static", 396.0, 0.0, "sine", "#22c55e", "396 HZ",
     "Letting go of tension, overthinking & heavy stress",
     "Play softly in the room while stretching, breathing, or clearing your head."),
    ("pure_432", "432 Hz — Natural Harmonic Tuning", 432.0, 0.0, "drone", "#ffd166", "432 HZ",
     "Warm, mellow room drone for evening chill & peaceful atmosphere",
     "Classic warm harmonic resonance — sounds rich over living-room TV speakers."),
    ("pure_528", "528 Hz — Bright Centering Tone", 528.0, 0.0, "sine", "#eab308", "528 HZ",
     "Uplifting mental reset, clarity & calm positive focus",
     "Keep volume gentle — 15–20 min works great in the morning or midday reset."),
    ("pure_639", "639 Hz — Calm Balance", 639.0, 0.0, "sine", "#ec4899", "639 HZ",
     "Balanced mood, peaceful conversation & unwinding emotional noise",
     "Soft ambient background tone — works on speakers or headphones."),
    ("pure_741", "741 Hz — Clear Head & Reset", 741.0, 0.0, "sine", "#f97316", "741 HZ",
     "Cutting through brain fog & mental decluttering",
     "Higher pure tone — lower volume to 15–20% for a crisp, clean listening edge."),
    ("pure_852", "852 Hz — Deep Contemplation", 852.0, 0.0, "sine", "#38bdf8", "852 HZ",
     "Deep silent reflection, late-night thinking & stillness",
     "Keep volume soft and pair with slow steady breathing."),
    ("pure_963", "963 Hz — High Shimmering Stillness", 963.0, 0.0, "sine", "#e2e8f0", "963 HZ",
     "Ultra-still awareness & quiet meditative focus",
     "High-pitched pure tone — always start very low (10–15% volume)."),
]


def generate_tone_wav(base_hz: float, beat_hz: float = 0.0, wave_type: str = "sine", duration_sec: float = 15.0) -> bytes:
    """
    100% pure Python stdlib stereo 16-bit WAV generator for meditation/binaural tones.
    Clamped safely to prevent CPU/RAM abuse; smooth fade-in/out for click-free looping.
    """
    base_hz = max(20.0, min(2000.0, float(base_hz)))
    beat_hz = max(0.0, min(60.0, float(beat_hz)))
    duration_sec = max(5.0, min(60.0, float(duration_sec)))
    sr = 22050
    n_frames = int(sr * duration_sec)
    f_left = max(20.0, base_hz - beat_hz / 2.0)
    f_right = max(20.0, base_hz + beat_hz / 2.0)
    two_pi = 2.0 * math.pi
    w_l = two_pi * f_left / sr
    w_r = two_pi * f_right / sr
    fade_n = min(int(sr * 0.12), n_frames // 4)
    amp = 0.34 * 32767.0
    samples = array.array("h")
    is_tri = (wave_type == "triangle")
    is_drone = (wave_type == "drone")

    for i in range(n_frames):
        env = 1.0
        if i < fade_n:
            env = i / fade_n
        elif i > n_frames - fade_n:
            env = (n_frames - i) / fade_n
        pl = w_l * i
        pr = w_r * i
        if is_tri:
            sl = (2.0 / math.pi) * math.asin(math.sin(pl))
            sr_v = (2.0 / math.pi) * math.asin(math.sin(pr))
        elif is_drone:
            lfo = 0.85 + 0.15 * math.sin(two_pi * 0.15 * i / sr)
            sl = lfo * (0.72 * math.sin(pl) + 0.20 * math.sin(pl * 0.5) + 0.08 * math.sin(pl * 1.5))
            sr_v = lfo * (0.72 * math.sin(pr) + 0.20 * math.sin(pr * 0.5) + 0.08 * math.sin(pr * 1.5))
        else:
            sl = math.sin(pl)
            sr_v = math.sin(pr)
        samples.append(max(-32767, min(32767, int(sl * amp * env))))
        samples.append(max(-32767, min(32767, int(sr_v * amp * env))))

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())
    return buf.getvalue()


# ==============================================================================
# 100% PURE PYTHON STDLIB ISO/IEC 18004 QR CODE SVG ENCODER (VERSIONS 1–5, EC-L)
# Zero external dependencies. Zero external QR APIs. Scannable by every phone.
# ==============================================================================
_QR_VER_SPECS = [
    # (version, size, data_codewords, ec_codewords, align_centers)
    (1, 21, 19, 7, []),
    (2, 25, 34, 10, [6, 18]),
    (3, 29, 55, 15, [6, 22]),
    (4, 33, 80, 20, [6, 26]),
    (5, 37, 108, 26, [6, 30]),
]

_GF_EXP = [0] * 512
_GF_LOG = [0] * 256
_x = 1
for _i in range(255):
    _GF_EXP[_i] = _x
    _GF_LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _GF_EXP[_i] = _GF_EXP[_i - 255]


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def _rs_encode(data: list, ec_len: int) -> list:
    gen = [1]
    for i in range(ec_len):
        nxt = [0] * (len(gen) + 1)
        f = _GF_EXP[i]
        for j, c in enumerate(gen):
            nxt[j] ^= c
            nxt[j + 1] ^= _gf_mul(c, f)
        gen = nxt
    rem = list(data) + [0] * ec_len
    for i in range(len(data)):
        coef = rem[i]
        if coef != 0:
            for j in range(len(gen)):
                rem[i + j] ^= _gf_mul(gen[j], coef)
    return rem[len(data):]


def _qr_format_bits(mask_id: int) -> int:
    # EC Level L = 0b01; 5-bit data = (0b01 << 3) | mask_id
    data = (0b01 << 3) | (mask_id & 0x7)
    d = data << 10
    for i in range(4, -1, -1):
        if d & (1 << (i + 10)):
            d ^= 0x537 << i
    return ((data << 10) | d) ^ 0x5412


def make_qr_matrix(text: str) -> list:
    raw = text.encode("utf-8")
    spec = None
    for s in _QR_VER_SPECS:
        # Byte mode header = 4 bits mode (0100) + 8 bits len = 12 bits + 4 terminator = 2 bytes overhead
        if len(raw) + 2 <= s[2]:
            spec = s
            break
    if spec is None:
        raise ValueError("QR text exceeds 106-byte limit")
    ver, size, data_cw, ec_cw, align = spec

    # Build bit stream (Byte mode 0100)
    bits = []
    def push_bits(val, n):
        for k in range(n - 1, -1, -1):
            bits.append((val >> k) & 1)

    push_bits(0b0100, 4)
    push_bits(len(raw), 8)
    for b in raw:
        push_bits(b, 8)
    cap_bits = data_cw * 8
    push_bits(0, min(4, cap_bits - len(bits)))
    while len(bits) % 8 != 0:
        bits.append(0)
    codewords = []
    for i in range(0, len(bits), 8):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        codewords.append(v)
    pad_toggle = 0
    while len(codewords) < data_cw:
        codewords.append(0xEC if pad_toggle == 0 else 0x11)
        pad_toggle ^= 1
    full_cw = codewords + _rs_encode(codewords, ec_cw)
    all_bits = []
    for cw in full_cw:
        for k in range(7, -1, -1):
            all_bits.append((cw >> k) & 1)

    # Function pattern matrix (None = unassigned data cell, 0/1 = fixed module)
    base = [[None] * size for _ in range(size)]
    is_func = [[False] * size for _ in range(size)]

    def set_fn(r, c, val):
        if 0 <= r < size and 0 <= c < size:
            base[r][c] = 1 if val else 0
            is_func[r][c] = True

    def draw_finder(tr, tc):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = tr + dr, tc + dc
                if not (0 <= r < size and 0 <= c < size):
                    continue
                if 0 <= dr <= 6 and 0 <= dc <= 6:
                    dark = (dr in (0, 6) or dc in (0, 6) or (2 <= dr <= 4 and 2 <= dc <= 4))
                else:
                    dark = False
                set_fn(r, c, dark)

    draw_finder(0, 0)
    draw_finder(0, size - 7)
    draw_finder(size - 7, 0)

    # Timing patterns
    for i in range(8, size - 8):
        set_fn(6, i, i % 2 == 0)
        set_fn(i, 6, i % 2 == 0)

    # Alignment patterns
    for ar in align:
        for ac in align:
            if is_func[ar][ac]:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    dark = (max(abs(dr), abs(dc)) != 1)
                    set_fn(ar + dr, ac + dc, dark)

    # Reserve format info cells + dark module
    for c in range(9):
        if c != 6:
            is_func[8][c] = True
            base[8][c] = 0
    for r in range(8):
        if r != 6:
            is_func[r][8] = True
            base[r][8] = 0
    for c in range(size - 8, size):
        is_func[8][c] = True
        base[8][c] = 0
    for r in range(size - 7, size):
        is_func[r][8] = True
        base[r][8] = 0
    set_fn(size - 8, 8, True)  # Mandatory dark module

    # Place data bits in standard 2-column upward/downward zigzag
    bit_idx = 0
    col = size - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
        row_range = range(size - 1, -1, -1) if upward else range(size)
        for r in row_range:
            for dc in (0, -1):
                c = col + dc
                if not is_func[r][c]:
                    base[r][c] = all_bits[bit_idx] if bit_idx < len(all_bits) else 0
                    bit_idx += 1
        col -= 2
        upward = not upward

    # Evaluate all 8 standard masks and pick lowest penalty
    def mask_cond(m, r, c):
        if m == 0: return (r + c) % 2 == 0
        if m == 1: return r % 2 == 0
        if m == 2: return c % 3 == 0
        if m == 3: return (r + c) % 3 == 0
        if m == 4: return ((r // 2) + (c // 3)) % 2 == 0
        if m == 5: return ((r * c) % 2) + ((r * c) % 3) == 0
        if m == 6: return (((r * c) % 2) + ((r * c) % 3)) % 2 == 0
        return (((r + c) % 2) + ((r * c) % 3)) % 2 == 0

    def apply_format(mat, mask_id):
        fmt = _qr_format_bits(mask_id)
        fcoords1 = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
                    (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
        fcoords2 = [(size - 1, 8), (size - 2, 8), (size - 3, 8), (size - 4, 8), (size - 5, 8), (size - 6, 8), (size - 7, 8),
                    (8, size - 8), (8, size - 7), (8, size - 6), (8, size - 5), (8, size - 4), (8, size - 3), (8, size - 2), (8, size - 1)]
        for i in range(15):
            bit = (fmt >> (14 - i)) & 1
            r1, c1 = fcoords1[i]
            r2, c2 = fcoords2[i]
            mat[r1][c1] = bit
            mat[r2][c2] = bit

    def penalty(mat):
        score = 0
        for r in range(size):
            run = 1
            for c in range(1, size):
                if mat[r][c] == mat[r][c - 1]:
                    run += 1
                    if run == 5: score += 3
                    elif run > 5: score += 1
                else:
                    run = 1
        for c in range(size):
            run = 1
            for r in range(1, size):
                if mat[r][c] == mat[r - 1][c]:
                    run += 1
                    if run == 5: score += 3
                    elif run > 5: score += 1
                else:
                    run = 1
        for r in range(size - 1):
            for c in range(size - 1):
                v = mat[r][c]
                if v == mat[r][c + 1] == mat[r + 1][c] == mat[r + 1][c + 1]:
                    score += 3
        dark_cnt = sum(sum(row) for row in mat)
        pct = (dark_cnt * 100) // (size * size)
        score += (abs(pct - 50) // 5) * 10
        return score

    best_mat, best_score = None, 10**9
    for m in range(8):
        cand = [[(base[r][c] ^ (1 if (not is_func[r][c] and mask_cond(m, r, c)) else 0)) for c in range(size)] for r in range(size)]
        apply_format(cand, m)
        sc = penalty(cand)
        if sc < best_score:
            best_score = sc
            best_mat = cand
    return best_mat


def make_qr_svg(text: str) -> bytes:
    mat = make_qr_matrix(text)
    n = len(mat)
    quiet = 4
    dim = n + quiet * 2
    rects = []
    for r, row in enumerate(mat):
        c = 0
        while c < n:
            if row[c]:
                start = c
                while c < n and row[c]:
                    c += 1
                rects.append(f'<rect x="{start + quiet}" y="{r + quiet}" width="{c - start}" height="1"/>')
            else:
                c += 1
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {dim} {dim}" shape-rendering="crispEdges">'
        f'<rect width="{dim}" height="{dim}" fill="#ffffff"/>'
        f'<g fill="#090b10">{"".join(rects)}</g>'
        f"</svg>"
    )
    return svg.encode("utf-8")


# ==============================================================================
# ZERO-DEPENDENCY LAN-ONLY AUTO-DISCOVERY (mDNS potato.local + SSDP UPnP)
# Link-local multicast only (TTL 1–2, never leaves your router, private-IP gated)
# ==============================================================================
_DISCOVERY_STATE = {"mdns": False, "ssdp": False}


def _is_lan_peer(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return bool(ip.is_private or ip.is_loopback or ip.is_link_local)
    except Exception:
        return False


def _dns_encode_name(name: str) -> bytes:
    out = b""
    for lbl in name.strip(".").split("."):
        b = lbl.encode("ascii", errors="ignore")[:63]
        out += bytes([len(b)]) + b
    return out + b"\x00"


def _dns_parse_name(pkt: bytes, off: int):
    labels = []
    jumped = False
    orig_next = off
    for _ in range(32):
        if off >= len(pkt):
            break
        ln = pkt[off]
        if ln == 0:
            if not jumped:
                orig_next = off + 1
            break
        if (ln & 0xC0) == 0xC0:
            if off + 1 >= len(pkt):
                break
            ptr = ((ln & 0x3F) << 8) | pkt[off + 1]
            if not jumped:
                orig_next = off + 2
                jumped = True
            off = ptr
        else:
            off += 1
            labels.append(pkt[off:off + ln].decode("utf-8", errors="ignore"))
            off += ln
    return ".".join(labels).lower(), orig_next


def _build_mdns_a_response(ip_str: str) -> bytes:
    # Standard mDNS response: QR=1, AA=1 (0x8400), 1 Answer (potato.local -> A)
    hdr = struct.pack("!HHHHHH", 0, 0x8400, 0, 1, 0, 0)
    ip_bytes = socket.inet_aton(ip_str)
    ans = _dns_encode_name(MDNS_HOST) + struct.pack("!HHIH", 1, 0x8001, 120, 4) + ip_bytes
    return hdr + ans


def _build_mdns_http_response(ip_str: str, port: int) -> bytes:
    svc = "_http._tcp.local"
    inst = f"POTATO.{svc}"
    hdr = struct.pack("!HHHHHH", 0, 0x8400, 0, 4, 0, 0)
    # 1. PTR _http._tcp.local -> POTATO._http._tcp.local
    inst_wire = _dns_encode_name(inst)
    ptr_rr = _dns_encode_name(svc) + struct.pack("!HHIH", 12, 0x0001, 120, len(inst_wire)) + inst_wire
    # 2. SRV POTATO._http._tcp.local -> port, potato.local
    tgt_wire = _dns_encode_name(MDNS_HOST)
    srv_rdata = struct.pack("!HHH", 0, 0, port) + tgt_wire
    srv_rr = inst_wire + struct.pack("!HHIH", 33, 0x8001, 120, len(srv_rdata)) + srv_rdata
    # 3. TXT POTATO._http._tcp.local -> path=/
    txt_rdata = b"\x06path=/" + b"\x0eauthor=Guffalo"
    txt_rr = inst_wire + struct.pack("!HHIH", 16, 0x8001, 120, len(txt_rdata)) + txt_rdata
    # 4. A potato.local -> ip
    a_rr = tgt_wire + struct.pack("!HHIH", 1, 0x8001, 120, 4) + socket.inet_aton(ip_str)
    return hdr + ptr_rr + srv_rr + txt_rr + a_rr


def start_mdns_responder(port: int):
    def _run():
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except Exception:
                    pass
            sock.bind(("", MDNS_PORT))
            mreq = struct.pack("4s4s", socket.inet_aton(MDNS_GROUP), socket.inet_aton("0.0.0.0"))
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
            sock.settimeout(2.0)
            _DISCOVERY_STATE["mdns"] = True
            # Send one gentle LAN announcement on startup
            lan_ip = detect_lan_ip()
            if lan_ip != "127.0.0.1":
                try:
                    sock.sendto(_build_mdns_a_response(lan_ip), (MDNS_GROUP, MDNS_PORT))
                    sock.sendto(_build_mdns_http_response(lan_ip, port), (MDNS_GROUP, MDNS_PORT))
                except Exception:
                    pass
            last_reply = {}
            while True:
                try:
                    pkt, addr = sock.recvfrom(2048)
                except socket.timeout:
                    continue
                if len(pkt) < 12 or not _is_lan_peer(addr[0]):
                    continue
                flags, qdcount = struct.unpack("!HH", pkt[2:6])
                if (flags & 0x8000) != 0 or qdcount == 0 or qdcount > 16:
                    continue
                now = time.time()
                if now - last_reply.get(addr[0], 0.0) < 0.15:
                    continue
                off = 12
                want_a = False
                want_http = False
                for _ in range(qdcount):
                    qname, off = _dns_parse_name(pkt, off)
                    if off + 4 > len(pkt):
                        break
                    qtype, _qclass = struct.unpack("!HH", pkt[off:off + 4])
                    off += 4
                    if qname == MDNS_HOST and qtype in (1, 255):
                        want_a = True
                    elif qname in ("_http._tcp.local", "_services._dns-sd._udp.local") and qtype in (12, 255):
                        want_http = True
                if want_a or want_http:
                    lan_ip = detect_lan_ip()
                    if lan_ip != "127.0.0.1":
                        last_reply[addr[0]] = now
                        dest = (MDNS_GROUP, MDNS_PORT) if addr[1] == MDNS_PORT else addr
                        if want_http:
                            sock.sendto(_build_mdns_http_response(lan_ip, port), dest)
                        elif want_a:
                            sock.sendto(_build_mdns_a_response(lan_ip), dest)
        except Exception:
            _DISCOVERY_STATE["mdns"] = False
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass

    threading.Thread(target=_run, daemon=True, name="potato-mdns").start()


def start_ssdp_responder(port: int):
    def _run():
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except Exception:
                    pass
            sock.bind(("", SSDP_PORT))
            mreq = struct.pack("4s4s", socket.inet_aton(SSDP_GROUP), socket.inet_aton("0.0.0.0"))
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.settimeout(2.0)
            _DISCOVERY_STATE["ssdp"] = True
            last_reply = {}
            while True:
                try:
                    pkt, addr = sock.recvfrom(2048)
                except socket.timeout:
                    continue
                if not _is_lan_peer(addr[0]):
                    continue
                txt = pkt.decode("utf-8", errors="ignore")
                if not txt.upper().startswith("M-SEARCH"):
                    continue
                low = txt.lower()
                if not any(st in low for st in ("ssdp:all", "upnp:rootdevice", "urn:schemas-upnp-org:device:basic:1")):
                    continue
                now = time.time()
                if now - last_reply.get(addr[0], 0.0) < 0.25:
                    continue
                lan_ip = detect_lan_ip()
                if lan_ip == "127.0.0.1":
                    continue
                last_reply[addr[0]] = now
                resp = (
                    "HTTP/1.1 200 OK\r\n"
                    "CACHE-CONTROL: max-age=1800\r\n"
                    "EXT:\r\n"
                    f"LOCATION: http://{lan_ip}:{port}/device.xml\r\n"
                    f"SERVER: POTATO/{POTATO_VERSION} UPnP/1.1\r\n"
                    "ST: upnp:rootdevice\r\n"
                    f"USN: {POTATO_UDN}::upnp:rootdevice\r\n\r\n"
                ).encode("utf-8")
                try:
                    sock.sendto(resp, addr)
                except Exception:
                    pass
        except Exception:
            _DISCOVERY_STATE["ssdp"] = False
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass

    threading.Thread(target=_run, daemon=True, name="potato-ssdp").start()


def get_config_path() -> str:
    return os.environ.get("POTATO_CONFIG") or os.path.join(BASE_DIR, "config.json")


def load_config() -> dict:
    cfg_path = get_config_path()
    defaults = {
        "host": "0.0.0.0",
        "port": int(os.environ.get("POTATO_PORT", "8789")),
        "node_name": os.environ.get("POTATO_NODE_NAME") or socket.gethostname(),
        "media_root": os.environ.get("POTATO_MEDIA_DIR") or os.path.expanduser("~/potato_media"),
        "allowed_folders": [],
        "blocked_subfolders": ["pictures", "photos", "music", "personal", "private", "camera"],
        "m3u_playlists": [os.path.join(BASE_DIR, "playlists", "example.m3u")],
        "include_open_directory": True,
        "enable_auto_discovery": True,
        "custom_links": [],
        "ffmpeg_path": "",
    }
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            if isinstance(user_cfg, dict):
                defaults.update(user_cfg)
        except Exception as e:
            print(f"[POTATO] Warning: could not parse {cfg_path}: {e}", flush=True)
    return defaults


def save_config(cfg: dict) -> str:
    cfg_path = get_config_path()
    parent = os.path.dirname(os.path.abspath(cfg_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return cfg_path


CFG = {}
HOST = "0.0.0.0"
PORT = 8789
NODE_NAME = "potato"
MEDIA_ROOT = ""
ALLOWED_FOLDERS = set()
BLOCKED_SUBFOLDERS = set()
M3U_CANDIDATES = []
INCLUDE_OPEN_DIRECTORY = True
ENABLE_AUTO_DISCOVERY = True
CUSTOM_LINKS = []
FFMPEG = ""

_CFG_LOCK = threading.Lock()
_MEDIA_CACHE = {"ts": 0.0, "cats": {}}
_M3U_CACHE = {"ts": 0.0, "path": "", "items": []}


def apply_runtime_config(cfg: dict):
    global CFG, HOST, PORT, NODE_NAME, MEDIA_ROOT, ALLOWED_FOLDERS
    global BLOCKED_SUBFOLDERS, M3U_CANDIDATES, INCLUDE_OPEN_DIRECTORY, ENABLE_AUTO_DISCOVERY, CUSTOM_LINKS, FFMPEG
    with _CFG_LOCK:
        CFG = dict(cfg)
        HOST = str(CFG.get("host", "0.0.0.0"))
        PORT = int(os.environ.get("POTATO_PORT", CFG.get("port", 8789)))
        NODE_NAME = str(CFG.get("node_name") or socket.gethostname())
        mr = str(CFG.get("media_root") or "").strip()
        MEDIA_ROOT = os.path.expanduser(mr) if mr else os.path.expanduser("~/potato_media")
        ALLOWED_FOLDERS = {str(x).strip() for x in (CFG.get("allowed_folders") or []) if str(x).strip()}
        BLOCKED_SUBFOLDERS = {str(x).lower() for x in (CFG.get("blocked_subfolders") or [])}
        M3U_CANDIDATES = [os.path.expanduser(str(p)) for p in (CFG.get("m3u_playlists") or []) if str(p).strip()]
        INCLUDE_OPEN_DIRECTORY = bool(CFG.get("include_open_directory", True))
        ENABLE_AUTO_DISCOVERY = bool(CFG.get("enable_auto_discovery", True))
        CUSTOM_LINKS = list(CFG.get("custom_links") or [])
        FFMPEG = str(CFG.get("ffmpeg_path") or "") or shutil.which("ffmpeg") or ""
        _MEDIA_CACHE["ts"] = 0.0
        _M3U_CACHE["ts"] = 0.0


apply_runtime_config(load_config())


def detect_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "127.0.0.1"


def find_m3u_list() -> list:
    found = []
    seen = set()
    for p in M3U_CANDIDATES:
        if not p:
            continue
        cand = p if os.path.isabs(p) else os.path.join(BASE_DIR, p)
        ab = os.path.abspath(cand)
        if os.path.isfile(ab) and ab not in seen:
            seen.add(ab)
            found.append(ab)
    # Also pick up any uploaded .m3u/.m3u8 inside playlists/ automatically
    pl_dir = os.path.join(BASE_DIR, "playlists")
    if os.path.isdir(pl_dir):
        for fn in sorted(os.listdir(pl_dir)):
            if os.path.splitext(fn)[1].lower() in PLAYLIST_EXTS:
                ab = os.path.abspath(os.path.join(pl_dir, fn))
                if os.path.isfile(ab) and ab not in seen:
                    seen.add(ab)
                    found.append(ab)
    return found


_SCAN_LOCK = threading.Lock()
_SCAN_RUNNING = False


def _do_media_walk() -> dict:
    cats = {}
    try:
        if MEDIA_ROOT and os.path.isdir(MEDIA_ROOT):
            base_abs = os.path.abspath(MEDIA_ROOT)
            root_files = []
            for fn in sorted(os.listdir(base_abs)):
                full = os.path.join(base_abs, fn)
                if os.path.isfile(full):
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in VIDEO_EXTS or ext in AUDIO_EXTS:
                        root_files.append({"name": fn, "path": full, "ext": ext})
            if root_files and not ALLOWED_FOLDERS:
                cats["Vault"] = root_files

            top_dirs = (
                sorted(ALLOWED_FOLDERS)
                if ALLOWED_FOLDERS
                else sorted(
                    d
                    for d in os.listdir(base_abs)
                    if os.path.isdir(os.path.join(base_abs, d)) and d.lower() not in BLOCKED_SUBFOLDERS
                )
            )
            for genre in top_dirs:
                gdir = os.path.join(base_abs, genre)
                if not os.path.isdir(gdir):
                    continue
                for root, dirs, files in os.walk(gdir):
                    dirs.sort()
                    dirs[:] = [d for d in dirs if d.lower() not in BLOCKED_SUBFOLDERS]
                    rel = os.path.relpath(root, gdir)
                    sub = "" if rel == "." else rel.replace(os.sep, " / ")
                    for fn in sorted(files):
                        ext = os.path.splitext(fn)[1].lower()
                        if ext not in VIDEO_EXTS and ext not in AUDIO_EXTS:
                            continue
                        full = os.path.join(root, fn)
                        label = f"{sub} — {fn}" if sub else fn
                        cats.setdefault(genre, []).append({"name": label, "path": full, "ext": ext})
    except Exception:
        pass
    _MEDIA_CACHE.update({"ts": time.time(), "cats": cats})
    return cats


def _trigger_bg_scan():
    global _SCAN_RUNNING
    with _SCAN_LOCK:
        if _SCAN_RUNNING:
            return
        _SCAN_RUNNING = True

    def _worker():
        global _SCAN_RUNNING
        try:
            _do_media_walk()
        finally:
            with _SCAN_LOCK:
                _SCAN_RUNNING = False

    threading.Thread(target=_worker, daemon=True, name="potato-scan").start()


def scan_media(force: bool = False) -> dict:
    """
    Non-blocking media cache: NEVER stalls HTTP requests on large/sleeping HDDs.
    Refreshes silently in a single locked background thread (TTL 30 min).
    """
    now = time.time()
    if force or _MEDIA_CACHE["ts"] == 0.0 or (now - _MEDIA_CACHE["ts"] >= 1800):
        _trigger_bg_scan()
    return _MEDIA_CACHE["cats"]


def is_safe_public_url(url: str) -> bool:
    """
    SSRF protection: allow only http:// or https:// URLs whose resolved IPs are
    strictly public/global (blocks localhost, loopback, RFC1918 LAN, link-local,
    cloud metadata 169.254.169.254, CGNAT, IPv6 ULA/link-local, and IPv4-mapped loopback).
    """
    if not url or any(c in url for c in ("\r", "\n", "\x00")):
        return False
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    host = p.hostname.strip().lower()
    if host in ("localhost", "localhost.localdomain") or host.endswith(".local"):
        return False
    try:
        infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except Exception:
        return False
    if not infos:
        return False
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
            if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
                ip = ip.ipv4_mapped
            if not ip.is_global or ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
                return False
        except Exception:
            return False
    return True


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_safe_public_url(newurl):
            raise urllib.error.URLError("Blocked redirect to non-public address")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def is_filesystem_root(path_str: str) -> bool:
    if not path_str:
        return False
    ab = os.path.abspath(os.path.expanduser(path_str))
    drive, tail = os.path.splitdrive(ab)
    return tail in ("", "/", "\\") or os.path.dirname(ab) == ab


def is_allowed_path(fpath: str) -> bool:
    if not fpath or not MEDIA_ROOT or not os.path.isfile(fpath):
        return False
    ext = os.path.splitext(fpath)[1].lower()
    if ext not in VIDEO_EXTS and ext not in AUDIO_EXTS:
        return False
    # Resolve symlinks with realpath so symlink escapes outside MEDIA_ROOT are impossible
    real_ab = os.path.realpath(fpath)
    real_root = os.path.realpath(MEDIA_ROOT)
    try:
        if os.path.commonpath([os.path.normcase(real_root), os.path.normcase(real_ab)]) != os.path.normcase(real_root):
            return False
    except ValueError:
        return False
    if os.path.normcase(real_ab) == os.path.normcase(real_root):
        return False
    rel_parts = os.path.relpath(real_ab, real_root).split(os.sep)
    if any(p.lower() in BLOCKED_SUBFOLDERS for p in rel_parts[:-1]):
        return False
    if ALLOWED_FOLDERS and len(rel_parts) > 1 and rel_parts[0] not in ALLOWED_FOLDERS:
        return False
    if ALLOWED_FOLDERS and len(rel_parts) == 1:
        return False
    return True


def parse_m3u(force: bool = False) -> list:
    paths = find_m3u_list()
    key = "|".join(paths)
    now = time.time()
    if not force and _M3U_CACHE["items"] and _M3U_CACHE["path"] == key and (now - _M3U_CACHE["ts"] < 300):
        return _M3U_CACHE["items"]
    items = []
    seen_urls = set()
    for p in paths:
        if not os.path.isfile(p):
            continue
        title, group = "Stream", os.path.splitext(os.path.basename(p))[0]
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                if line.startswith("#EXTINF"):
                    if 'group-title="' in line:
                        group = line.split('group-title="', 1)[1].split('"', 1)[0]
                    if "," in line:
                        title = line.split(",", 1)[1].strip()
                elif not line.startswith("#"):
                    # Strictly allow only http:// or https:// stream URLs
                    if line.startswith(("http://", "https://")) and line not in seen_urls:
                        seen_urls.add(line)
                        items.append({"title": title, "group": group, "url": line})
                    title = "Stream"
    _M3U_CACHE.update({"ts": now, "path": key, "items": items})
    return items


def sanitize_filename(raw_name: str) -> str:
    base = os.path.basename(raw_name.replace("\\", "/")).strip()
    base = re.sub(r"[^A-Za-z0-9._ -]+", "_", base)
    base = re.sub(r"\s+", " ", base).strip(" .")
    if not base or base in (".", ".."):
        return ""
    return base[:160]


# ==============================================================================
# CLEAN DARK UI DESIGN SYSTEM (100% SELF-CONTAINED — ZERO EXTERNAL CDNS)
# ==============================================================================
CLEAN_BORDER_SVG = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24'%3E"
    "%3Crect width='24' height='24' fill='%23161b22'/%3E"
    "%3Crect x='2' y='2' width='20' height='20' fill='none' stroke='%23f59e0b' stroke-width='1.5' opacity='0.55'/%3E"
    "%3C/svg%3E"
)
CLEAN_FOCUS_SVG = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' width='11' height='11' viewBox='0 0 24 24'%3E"
    "%3Crect width='24' height='24' fill='%23451a03'/%3E"
    "%3Crect x='2' y='2' width='20' height='20' fill='none' stroke='%23fcd34d' stroke-width='2'/%3E"
    "%3C/svg%3E"
)

BASE_CSS = f"""
*{{box-sizing:border-box}}
:root{{
  --gold:#ffd166;
  --gold-bright:#fff2a6;
  --gold-glow:rgba(255,209,102,0.78);
  --glow-mult:1;
  --border-svg:url("{CLEAN_BORDER_SVG}");
  --ui-head:'Palatino Linotype','Book Antiqua','URW Palladio L',Georgia,serif;
  --ui-sub:'Palatino Linotype','Book Antiqua',Georgia,serif;
}}
body.theme-emerald{{--gold:#34d399;--gold-bright:#a7f3d0;--gold-glow:rgba(52,211,153,0.8)}}
body.theme-ember{{--gold:#fb923c;--gold-bright:#fed7aa;--gold-glow:rgba(251,146,60,0.82)}}
body{{
  background:#06080c #0d1117;
  color:#f8fafc;
  font:15.5px/1.38 system-ui,-apple-system,Segoe UI,sans-serif;
  margin:0;
  padding:20px 24px 52px;
  min-height:100vh;
  position:relative;
}}
body::before{{
  content:'';
  position:fixed;
  top:0;right:0;bottom:0;left:0;
  background:
        radial-gradient(circle at 50% 42%,rgba(255,209,102,0.06) 0%,rgba(6,8,12,0.50) 52%,rgba(4,6,10,0.82) 100%);
  z-index:-1;
  pointer-events:none;
}}
.hdr{{
  display:flex;
  align-items:center;
  gap:16px;
  margin:0 0 16px;
  padding:7px;
  border-radius:16px;
  background-image:var(--border-svg);
  background-repeat:repeat;
  border:2px solid var(--gold-bright);
  box-shadow:0 0 calc(24px * var(--glow-mult)) var(--gold-glow),0 10px 30px rgba(0,0,0,0.72),inset 0 0 12px rgba(255,232,140,0.5);
}}
.hdr-inner{{
  display:flex;
  align-items:center;
  gap:15px;
  width:100%;
  padding:11px 16px;
  border-radius:10px;
  background:linear-gradient(135deg,rgba(8,11,18,0.92),rgba(15,20,32,0.86));
  border:1.5px solid var(--gold);
}}
.hdr img{{
  width:58px;
  height:58px;
  border-radius:11px;
  border:2px solid var(--gold-bright);
  box-shadow:0 0 18px var(--gold-glow);
  flex-shrink:0;
  background:#05070b;
  cursor:pointer;
  transition:transform .15s ease;
}}
.hdr img:active{{transform:scale(0.94)}}
.hdr-t{{min-width:0;flex:1}}
.title-row{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.hdr-icon{{flex-shrink:0;}}
.hdr h1{{
  font-family:var(--ui-head);
  font-variant:small-caps;
  font-size:28px;
  font-weight:900;
  margin:0;
  color:var(--gold-bright);
  letter-spacing:3.4px;
  text-shadow:0 0 16px var(--gold-glow),0 2px 10px #000,1px 1px 0 #78350f;
}}
.hdr .sub-band{{
  font-size:11.5px;
  color:var(--gold);
  letter-spacing:3.4px;
  opacity:0.94;
  margin-top:3px;
}}
.hdr .sub{{
  font-size:12.5px;
  color:#e2e8f0;
  margin-top:3px;
  letter-spacing:.3px;
}}

h2{{
  font-family:var(--ui-sub);
  font-variant:small-caps;
  font-size:15.5px;
  font-weight:800;
  margin:22px 0 11px;
  color:var(--gold-bright);
  letter-spacing:1.8px;
  padding:7px 14px;
  border-radius:10px;
  background:linear-gradient(90deg,rgba(12,16,26,0.92),rgba(28,22,10,0.74),rgba(12,16,26,0.42));
  border:1.5px solid var(--gold);
  border-left:5px solid var(--gold-bright);
  box-shadow:0 0 calc(16px * var(--glow-mult)) rgba(255,209,102,0.28);
  text-shadow:0 1px 10px #000;
}}
h2 .r-dec{{color:var(--gold);margin-right:8px;letter-spacing:2px;font-family:system-ui,sans-serif}}

.nav{{display:grid;grid-template-columns:repeat(7,1fr);gap:9px;margin-bottom:16px}}
.nav.cols-6{{grid-template-columns:repeat(6,1fr)}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.grid-2{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}
@media(max-width:1180px){{.nav,.nav.cols-6{{grid-template-columns:repeat(4,1fr)}}.grid{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:720px){{.grid-2{{grid-template-columns:1fr}}}}
@media(max-width:560px){{.nav,.nav.cols-6{{grid-template-columns:repeat(2,1fr)}}.grid{{grid-template-columns:1fr}}}}

a.tile{{display:flex;text-decoration:none;color:inherit}}
.tile{{
  display:block;
  width:100%;
  padding:6px;
  border:2px solid var(--gold-bright);
  border-radius:13px;
  background-image:var(--border-svg);
  background-repeat:repeat;
  box-shadow:0 0 calc(14px * var(--glow-mult)) rgba(255,209,102,0.34),0 6px 18px rgba(0,0,0,0.62);
  cursor:pointer;
  text-align:left;
  color:#f8fafc;
  transition:box-shadow .12s ease,border-color .12s ease;
  text-decoration:none;
}}
.tile > .t-in{{
  display:flex;
  flex-direction:column;
  align-items:flex-start;
  justify-content:center;
  gap:4px;
  width:100%;
  padding:10px 12px;
  border-radius:8px;
  background:linear-gradient(135deg,rgba(10,14,24,0.92),rgba(17,24,39,0.88));
  border:1px solid var(--gold);
  border-left:4px solid var(--acc,#ffd166);
  color:#f8fafc;
  min-width:0;
}}
.t-top{{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:8px;
  width:100%;
  min-width:0;
}}
.t-lbl{{
  font-size:14px;
  font-weight:700;
  color:#f8fafc;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
  min-width:0;
  flex:1;
}}
.t-tag{{
  flex-shrink:0;
  font-size:10px;
  font-weight:800;
  letter-spacing:.9px;
  padding:2px 6px;
  border-radius:5px;
  background:rgba(255,209,102,0.16);
  border:1px solid var(--acc,var(--gold));
  color:var(--gold-bright);
  text-transform:uppercase;
}}
.t-desc{{
  font-size:11.5px;
  font-weight:500;
  color:#cbd5e1;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
  width:100%;
  opacity:0.92;
}}
.nav .tile > .t-in{{align-items:center;padding:9px 8px}}
.nav .t-top{{justify-content:center}}
.nav .t-lbl{{
  text-align:center;
  font-family:var(--ui-sub);
  font-variant:small-caps;
  font-size:14px;
  letter-spacing:1px;
  color:var(--gold-bright);
  flex:0 1 auto;
}}
.nav .t-desc{{text-align:center;font-size:10.5px;color:#fde68a;opacity:0.84}}

.qref{{
  padding:5px;
  border-radius:13px;
  border:2px solid var(--gold-bright);
  background-image:var(--border-svg);
  background-repeat:repeat;
  margin:0 0 16px;
  box-shadow:0 0 calc(16px * var(--glow-mult)) rgba(255,209,102,0.34);
}}
.qref-in{{
  display:flex;
  align-items:center;
  gap:12px;
  flex-wrap:wrap;
  background:linear-gradient(90deg,rgba(8,11,18,0.96),rgba(24,19,9,0.93));
  border:1px solid var(--gold);
  border-radius:8px;
  padding:9px 14px;
}}
.qref-badge{{
  font-size:11px;
  font-weight:800;
  letter-spacing:1.1px;
  padding:3px 8px;
  border-radius:6px;
  background:rgba(255,209,102,0.2);
  border:1.5px solid var(--gold-bright);
  color:var(--gold-bright);
  text-transform:uppercase;
}}
.qref-title{{
  font-family:var(--ui-sub);
  font-variant:small-caps;
  font-size:14.5px;
  font-weight:800;
  color:#fffbeb;
}}
.qref-desc{{font-size:13px;color:#e2e8f0;flex:1;min-width:190px}}
.qref-dest{{font-family:ui-monospace,Consolas,monospace;font-size:11.5px;color:var(--gold);opacity:0.95}}

.tile:hover{{
  border-color:#ffffff;
  box-shadow:0 0 calc(20px * var(--glow-mult)) var(--gold-glow),0 6px 20px rgba(0,0,0,0.68);
}}
.tile.active{{border-color:#fff6c2;box-shadow:0 0 calc(22px * var(--glow-mult)) var(--gold-glow)}}
.tile.active > .t-in{{background:linear-gradient(135deg,rgba(38,29,11,0.95),rgba(20,28,46,0.92));border-color:var(--gold-bright)}}
.tile.tv-sel,.tile:focus{{
  outline:none!important;
  border-color:#ffffff!important;
  background-image:url("{CLEAN_FOCUS_SVG}")!important;
  box-shadow:0 0 0 3px var(--gold),0 0 30px rgba(255,224,102,0.98),0 0 50px rgba(255,190,60,0.58)!important;
  position:relative;
  z-index:6;
}}
.tile.tv-sel > .t-in,.tile:focus > .t-in{{
  background:linear-gradient(135deg,rgba(52,38,10,0.96),rgba(24,33,54,0.95))!important;
  border-color:#fff6c2!important;
  color:#fffbeb!important;
}}

.bar{{display:flex;gap:10px;margin:10px 0 16px;align-items:stretch}}
input[type=text],input[type=url],input[type=file],select{{
  width:100%;
  padding:11px 14px;
  border-radius:11px;
  border:2px solid var(--gold);
  background:rgba(8,12,20,0.94);
  color:#fff;
  font-size:14.5px;
  box-shadow:0 0 10px rgba(255,209,102,0.22);
}}
.bar input[type=text]{{flex:1;width:auto}}
input:focus,input.tv-sel,select:focus{{
  outline:none!important;
  border-color:#fff6c2!important;
  box-shadow:0 0 0 3px var(--gold),0 0 22px var(--gold-glow)!important;
}}
.status{{
  padding:6px;
  border-radius:13px;
  border:2px solid var(--gold-bright);
  background-image:var(--border-svg);
  background-repeat:repeat;
  margin:10px 0 14px;
  box-shadow:0 0 18px rgba(255,209,102,0.32);
}}
.status-in{{
  background:rgba(8,11,18,0.94);
  border:1px solid var(--gold);
  border-radius:8px;
  padding:12px 16px;
  font-family:ui-monospace,Consolas,monospace;
  font-size:13.5px;
  color:#fde68a;
  line-height:1.5;
}}
.bp-card{{
  padding:6px;
  border-radius:14px;
  border:2px solid var(--gold-bright);
  background-image:var(--border-svg);
  box-shadow:0 0 18px rgba(255,209,102,0.34);
}}
.bp-in{{
  background:linear-gradient(145deg,rgba(8,11,18,0.96),rgba(20,17,10,0.93));
  border:1px solid var(--gold);
  border-radius:9px;
  padding:15px 17px;
  height:100%;
}}
.bp-tag{{font-size:11px;letter-spacing:2px;color:var(--gold);text-transform:uppercase;margin-bottom:4px;font-weight:800}}
.bp-name{{font-family:var(--ui-head);font-variant:small-caps;font-size:18px;font-weight:900;color:var(--gold-bright);margin-bottom:8px}}
.bp-desc{{font-size:13.5px;color:#e2e8f0;line-height:1.5}}
.big-url{{
  font-family:ui-monospace,Consolas,monospace;
  font-size:18px;
  font-weight:800;
  color:#fffbeb;
  background:rgba(255,209,102,0.12);
  border:1.5px solid var(--gold-bright);
  border-radius:10px;
  padding:10px 14px;
  margin:10px 0;
  word-break:break-all;
  text-align:center;
  text-shadow:0 0 10px var(--gold-glow);
}}
.fld{{margin:10px 0}}
.fld label{{display:block;font-size:12.5px;font-weight:700;color:var(--gold-bright);margin-bottom:5px;letter-spacing:.4px}}
.chk{{display:flex;align-items:center;gap:9px;margin:10px 0;font-size:13.5px;color:#fde68a;cursor:pointer}}
.chk input{{width:18px;height:18px;accent-color:#ffd166}}
.steps{{margin:8px 0 12px 18px;padding:0;color:#e2e8f0;font-size:13.5px;line-height:1.6}}
.steps li{{margin-bottom:4px}}
.steps b{{color:var(--gold-bright)}}
.notice{{
  padding:6px;border-radius:13px;border:2px solid #34d399;background-image:var(--border-svg);margin:0 0 16px;
  box-shadow:0 0 22px rgba(52,211,153,0.45);
}}
.notice-in{{background:rgba(6,24,18,0.95);border:1px solid #34d399;border-radius:8px;padding:11px 15px;color:#a7f3d0;font-weight:700;font-size:14px}}
.notice.err{{border-color:#f87171;box-shadow:0 0 22px rgba(248,113,113,0.45)}}
.notice.err .notice-in{{background:rgba(34,10,12,0.95);border-color:#f87171;color:#fecaca}}

.foot{{
  margin-top:28px;
  text-align:center;
  font-size:12px;
  color:#cbd5e1;
  opacity:0.92;
  letter-spacing:1.1px;
}}
.foot b{{font-family:var(--ui-sub);font-variant:small-caps;color:var(--gold-bright)}}
.whisper-mark{{
  display:inline-block;
  margin-left:8px;
  color:var(--gold);
  cursor:pointer;
  padding:2px 6px;
  border-radius:6px;
  border:1px solid rgba(255,209,102,0.35);
}}
.whisper-mark:hover{{color:#fff;border-color:var(--gold-bright);box-shadow:0 0 10px var(--gold-glow)}}
#whisperToast{{
  position:fixed;
  bottom:22px;
  left:50%;
  transform:translateX(-50%);
  background:rgba(8,11,18,0.96);
  border:2px solid var(--gold-bright);
  border-radius:12px;
  padding:10px 20px;
  color:var(--gold-bright);
  font-family:var(--ui-sub);
  font-size:14px;
  letter-spacing:1px;
  box-shadow:0 0 28px var(--gold-glow);
  opacity:0;
  pointer-events:none;
  transition:opacity .25s;
  z-index:999;
}}
#whisperToast.show{{opacity:1}}
"""

GRID_NAV_JS = """
<script>
function openExternal(u){
  if(!u) return;
  location.href = u;
}
function copyText(txt, label){
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(txt).then(function(){
      if(window.uiToast) window.uiToast('Copied: ' + (label || txt));
    }).catch(function(){
      prompt('Copy this address:', txt);
    });
  } else {
    prompt('Copy this address:', txt);
  }
}
(function(){
  var rows = [], rIdx = 0, cIdx = 0, lastStepTs = 0;
  var TAP_DEBOUNCE_MS = 120;
  var REPEAT_STEP_MS = Number(localStorage.getItem('potato_repeat_ms') || 240);

  function isFormField(el){
    if(!el) return false;
    var tag = el.tagName;
    if(tag === 'TEXTAREA' || tag === 'SELECT') return true;
    if(tag === 'INPUT'){
      var t = (el.type || '').toLowerCase();
      return t !== 'button' && t !== 'submit' && t !== 'reset';
    }
    return false;
  }

  function buildGrid(){
    rows = [];
    var sy = window.scrollY || document.documentElement.scrollTop || 0;
    var sx = window.scrollX || document.documentElement.scrollLeft || 0;
    var els = document.querySelectorAll('.tile, .bar input[type=text]');
    var buckets = [];
    for(var i = 0; i < els.length; i++){
      var el = els[i];
      var rect = el.getBoundingClientRect();
      if(rect.width < 4 || rect.height < 4) continue;
      var top = Math.round(rect.top + sy);
      var left = Math.round(rect.left + sx);
      var placed = false;
      for(var b = 0; b < buckets.length; b++){
        if(Math.abs(buckets[b].top - top) < 28){
          buckets[b].items.push({el: el, left: left});
          placed = true;
          break;
        }
      }
      if(!placed) buckets.push({top: top, items: [{el: el, left: left}]});
    }
    buckets.sort(function(a, b){ return a.top - b.top; });
    for(var j = 0; j < buckets.length; j++){
      buckets[j].items.sort(function(a, b){ return a.left - b.left; });
      rows.push(buckets[j].items.map(function(x){ return x.el; }));
    }
  }

  function findEl(target){
    for(var r = 0; r < rows.length; r++){
      for(var c = 0; c < rows[r].length; c++){
        if(rows[r][c] === target) return {r: r, c: c};
      }
    }
    return null;
  }

  function current(){
    if(!rows.length) buildGrid();
    if(!rows.length) return null;
    if(rIdx < 0) rIdx = 0;
    if(rIdx >= rows.length) rIdx = rows.length - 1;
    if(cIdx < 0) cIdx = 0;
    if(cIdx >= rows[rIdx].length) cIdx = rows[rIdx].length - 1;
    return rows[rIdx][cIdx];
  }

  function updateQref(el){
    var box = document.getElementById('qref');
    if(!box || !el) return;
    var b = el.getAttribute('data-qbadge') || (el.tagName === 'INPUT' ? 'SEARCH' : 'TILE');
    var t = el.getAttribute('data-qtitle') || (el.tagName === 'INPUT' ? 'Search / Filter' : (el.textContent || '').trim());
    var d = el.getAttribute('data-qdesc') || (el.tagName === 'INPUT' ? 'Type keywords and press Enter to filter' : 'Press OK / Enter to open');
    var u = el.getAttribute('data-qdest') || '';
    document.getElementById('qrefBadge').textContent = b;
    document.getElementById('qrefTitle').textContent = t;
    document.getElementById('qrefDesc').textContent = d;
    document.getElementById('qrefDest').textContent = u ? ('→ ' + u) : '';
  }

  function paint(doScroll){
    var all = document.querySelectorAll('.tv-sel');
    for(var i = 0; i < all.length; i++) all[i].classList.remove('tv-sel');
    var el = current();
    if(!el) return;
    el.classList.add('tv-sel');
    updateQref(el);
    try{ el.focus({preventScroll: true}); }catch(e){ try{ el.focus(); }catch(e2){} }
    if(doScroll !== false){
      try{ el.scrollIntoView({block: 'nearest', inline: 'nearest', behavior: 'auto'}); }catch(e){}
    }
  }

  function step(act){
    if(!rows.length) buildGrid();
    if(!rows.length) return;
    var el = current();
    if(act === 'R'){
      if(cIdx < rows[rIdx].length - 1){ cIdx++; paint(true); }
    } else if(act === 'L'){
      if(cIdx > 0){ cIdx--; paint(true); }
    } else if(act === 'D'){
      if(el && el.tagName === 'INPUT') el.blur();
      if(rIdx < rows.length - 1){
        rIdx++;
        if(cIdx >= rows[rIdx].length) cIdx = rows[rIdx].length - 1;
        paint(true);
      }
    } else if(act === 'U'){
      if(el && el.tagName === 'INPUT') el.blur();
      if(rIdx > 0){
        rIdx--;
        if(cIdx >= rows[rIdx].length) cIdx = rows[rIdx].length - 1;
        paint(true);
      }
    } else if(act === 'OK'){
      if(!el) return;
      if(el.tagName === 'INPUT'){
        if(document.activeElement === el && el.form) el.form.submit();
        else el.focus();
      } else {
        el.click();
      }
    } else if(act === 'BACK'){
      if(el && el.tagName === 'INPUT'){ el.blur(); return; }
      if(window.__potatoBack){ window.__potatoBack(); return; }
      if(location.pathname !== '/') history.back();
    }
  }

  window.__dpad = step;

  function decode(e){
    var k = e.key || '', kc = e.keyCode || e.which || 0;
    if(k === 'ArrowRight' || kc === 39 || kc === 22) return 'R';
    if(k === 'ArrowLeft'  || kc === 37 || kc === 21) return 'L';
    if(k === 'ArrowDown'  || kc === 40 || kc === 20) return 'D';
    if(k === 'ArrowUp'    || kc === 38 || kc === 19) return 'U';
    if(k === 'Enter' || k === 'Select' || k === 'DPadCenter' || kc === 13 || kc === 23 || kc === 66) return 'OK';
    if(k === 'Escape' || k === 'Back' || k === 'GoBack' || k === 'BrowserBack' || kc === 4 || kc === 27 || kc === 10009 || kc === 461) return 'BACK';
    return '';
  }

  window.addEventListener('keydown', function(e){
    if(window.__potatoMediaKey && window.__potatoMediaKey(e)) return;
    var ae = document.activeElement;
    var act = decode(e);
    if(!act) return;
    // Allow natural typing & form submission when user is focused inside a /setup form input
    if(isFormField(ae) && !ae.closest('.bar')){
      if(act === 'BACK'){ ae.blur(); e.preventDefault(); }
      return;
    }
    if(ae && ae.tagName === 'INPUT' && ae.value && (act === 'L' || act === 'R')) return;
    e.preventDefault();
    e.stopPropagation();
    if(e.stopImmediatePropagation) e.stopImmediatePropagation();
    var now = Date.now();
    var minGap = e.repeat ? REPEAT_STEP_MS : TAP_DEBOUNCE_MS;
    if(now - lastStepTs < minGap) return;
    lastStepTs = now;
    
    step(act);
  }, true);

  function swallow(e){
    var ae = document.activeElement;
    if(isFormField(ae) && !ae.closest('.bar')) return;
    var act = decode(e);
    if(!act) return;
    if(ae && ae.tagName === 'INPUT' && ae.value && (act === 'L' || act === 'R')) return;
    e.preventDefault();
    e.stopPropagation();
  }
  window.addEventListener('keypress', swallow, true);
  window.addEventListener('keyup', swallow, true);

  function initFocus(){
    
    buildGrid();
    var defEl = document.querySelector('[data-default-focus="1"]');
    if(defEl){
      var pos = findEl(defEl);
      if(pos){ rIdx = pos.r; cIdx = pos.c; paint(false); return; }
    }
    var actEl = document.querySelector('.nav .tile.active');
    if(actEl){
      var apos = findEl(actEl);
      if(apos){ rIdx = apos.r; cIdx = apos.c; paint(false); return; }
    }
    rIdx = 0; cIdx = 0;
    paint(false);
  }

  document.addEventListener('mouseover', function(e){
    var t = e.target && e.target.closest ? e.target.closest('.tile, .bar input[type=text]') : null;
    if(!t) return;
    if(!rows.length) buildGrid();
    var pos = findEl(t);
    if(pos){ rIdx = pos.r; cIdx = pos.c; }
    updateQref(t);
  });

  window.addEventListener('resize', function(){
    var prev = current();
    buildGrid();
    if(prev){
      var pos = findEl(prev);
      if(pos){ rIdx = pos.r; cIdx = pos.c; }
    }
    paint(false);
  });

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', initFocus);
  } else {
    initFocus();
  }
})();
</script>
"""


def tile_btn(
    label: str,
    onclick_js: str,
    acc: str = "#ffd166",
    extra_cls: str = "",
    extra_attrs: str = "",
    badge: str = "",
    desc: str = "",
    dest: str = "",
    btn_type: str = "button",
) -> str:
    cls = f"tile {extra_cls}".strip()
    q_attrs = (
        f' data-qtitle="{html_lib.escape(label, quote=True)}"'
        f' data-qbadge="{html_lib.escape(badge or "OPEN", quote=True)}"'
        f' data-qdesc="{html_lib.escape(desc or "Press OK / Enter to open", quote=True)}"'
        f' data-qdest="{html_lib.escape(dest, quote=True)}"'
    )
    badge_html = f'<span class="t-tag">{html_lib.escape(badge)}</span>' if badge else ""
    desc_html = f'<span class="t-desc">{html_lib.escape(desc)}</span>' if desc else ""
    m_loc = re.fullmatch(r"location\.href='([^']+)'", (onclick_js or "").strip())
    if m_loc and btn_type == "button":
        href = html_lib.escape(m_loc.group(1), quote=True)
        return (
            f'<a href="{href}" class="{cls}" style="--acc:{html_lib.escape(acc, quote=True)}" '
            f'{extra_attrs}{q_attrs}>'
            f'<span class="t-in"><span class="t-top"><span class="t-lbl">{html_lib.escape(label)}</span>{badge_html}</span>{desc_html}</span>'
            f"</a>"
        )
    oc = f' onclick="{onclick_js}"' if onclick_js else ""
    return (
        f'<button type="{btn_type}" class="{cls}" style="--acc:{html_lib.escape(acc, quote=True)}" '
        f'{extra_attrs}{q_attrs}{oc}>'
        f'<span class="t-in"><span class="t-top"><span class="t-lbl">{html_lib.escape(label)}</span>{badge_html}</span>{desc_html}</span>'
        f"</button>"
    )



def render_nav(active: str, total_media: int, total_streams: int) -> str:
    def btn(key, label, href, acc, desc):
        cls = "active" if key == active else ""
        return tile_btn(label, f"location.href='{href}'", acc=acc, extra_cls=cls, badge="", desc=desc, dest=href)

    items = [
        btn("home", "Home", "/", "#ffd166", "Hub & quick play"),
        btn("media", f"Library ({total_media:,})", "/library", "#3b82f6", "Local & Frequencies vault"),
        btn("streams", f"Playlists ({total_streams:,})", "/playlists", "#14b8a6", "Built-in M3U streams"),
    ]
    if INCLUDE_OPEN_DIRECTORY:
        items.append(btn("open", f"Rabbit Holes ({len(OPEN_ALL)})", "/open", "#a855f7", "Weird docs, & cinema"))
    items.append(btn("freqs", "Frequencies", "/freqs", "#10b981", "Adjustable Hz & meditation waves"))
    items.append(btn("setup", "Easy Setup", "/setup", "#22c55e", "Upload, TV link & Kodi"))
    items.append(btn("status", "Status", "/status", "#eab308", "Rescan, M3U & JSON"))
    nav_cls = "nav" if INCLUDE_OPEN_DIRECTORY else "nav cols-6"
    return f'<div class="{nav_cls}">{"".join(items)}</div>'



LEGACY_UA_RE = re.compile(
    r"Opera Mini|Lynx|w3m|Dillo|Links \(|NetFront|Android [2-6]\.|LegacyTV",
    re.I,
)

def is_legacy_client(ua: str) -> bool:
    return bool(ua and LEGACY_UA_RE.search(ua))

def render_lite_page(title: str, host_hdr: str, body_html: str) -> bytes:
    """
    Ultra-Lite Mode: 100% Zero-JS, Zero-Image, Zero-CSS-Grid/Flexbox, <4KB classic HTML.
    Designed to run effortlessly on 15-year-old Smart TVs, 1st-gen TV streaming sticks, e-readers, feature phones,
    Android 4.4, Opera Mini, Lynx/w3m, and 256MB-RAM single-board computers.
    """
    live_url = f"http://{host_hdr}/lite"
    doc = (
        f'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'
        f'<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>POTATO Lite - {html_lib.escape(title)}</title>'
        f'<style>body{{background:#111;color:#eee;font-family:sans-serif;margin:10px;line-height:1.45}}'
        f'a{{color:#fcd34d;text-decoration:underline}}h1,h2{{color:#f59e0b;margin:8px 0 6px}}'
        f'.nav a{{display:inline-block;padding:6px 10px;margin:3px;border:1px solid #555;background:#222;text-decoration:none}}'
        f'ul{{padding-left:18px}}li{{margin:5px 0}}.box{{border:1px solid #444;padding:8px;margin:8px 0;background:#1a1a1a}}'
        f'.foot{{margin-top:16px;font-size:12px;color:#999;border-top:1px solid #333;padding-top:8px}}</style>'
        f'</head><body>'
        f'<h1>POTATO <small>(Ultra-Lite · Zero JS)</small></h1>'
        f'<div class="box">Live URL: <a href="{html_lib.escape(live_url, quote=True)}">{html_lib.escape(live_url)}</a>'
        f' &nbsp;|&nbsp; <a href="/?full=1">Switch to Full UI</a></div>'
        f'<div class="nav">'
        f'<a href="/lite">Home</a>'
        f'<a href="/lite/library">Library</a>'
        f'<a href="/lite/playlists">Playlists</a>'
        f'<a href="/lite/open">Links</a>'
        f'<a href="/lite/status">Status</a>'
        f'</div><hr>'
        f'{body_html}'
        f'<div class="foot">POTATO &middot; Watermark &amp; Copyright &copy; 2026 {POTATO_AUTHOR} &middot; GNU {POTATO_LICENSE} '
        f'(free to modify &mdash; keep author watermark &amp; credits intact)</div>'
        f'</body></html>'
    )
    return doc.encode("utf-8")

def render_page(title: str, active: str, body: str, total_media: int, total_streams: int) -> bytes:
    page_title = POTATO_NAME if active == "home" else f"{POTATO_NAME} · {title}"
    doc = f"""<!doctype html><html lang="en"><!-- POTATO Open-Source LAN Media Hub (GPLv3) --><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html_lib.escape(page_title)}</title>
<meta name="theme-color" content="#0d0c09">
<meta name="application-name" content="POTATO">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="POTATO">
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/png" href="/assets/potato_icon.png">
<link rel="apple-touch-icon" href="/assets/potato_icon.png">
<style>{BASE_CSS}</style></head><body>
<div class="hdr">
  <div class="hdr-inner">
    <img src="/assets/potato_icon_192.png" alt="POTATO" style="width:54px;height:54px;border-radius:12px">
    <div class="hdr-t">
      <div class="title-row" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <h1>POTATO</h1>
        <button type="button" id="liveOriginBtn" class="tile" style="padding:5px 12px;min-height:auto;font-size:12px;border-radius:8px;cursor:pointer;background:#161b22;border:1px solid #f59e0b;color:#fcd34d" title="Auto-populated live URL — click to copy">Live URL: loading...</button><a href="/lite" class="tile" style="padding:5px 12px;min-height:auto;font-size:12px;border-radius:8px;background:#161b22;border:1px solid #22c55e;color:#86efac" title="Zero-JS ultra-lightweight mode for old TVs, Pi Zero &amp; tiny devices">Ultra-Lite (/lite)</a>
      </div>
      <div class="sub">{html_lib.escape(title)} · {total_media:,} Local Files · {total_streams:,} Streams · Created by {POTATO_AUTHOR} (GNU GPLv3) · 0% VRAM Idle</div>
    </div>
  </div>
</div>
{render_nav(active, total_media, total_streams)}
<div id="qref" class="qref" aria-live="polite">
  <div class="qref-in">
    <span id="qrefBadge" class="qref-badge">READY</span>
    <span id="qrefTitle" class="qref-title">Quick Reference</span>
    <span id="qrefDesc" class="qref-desc">Move your TV remote or hover any button to inspect what is behind it before opening.</span>
    <span id="qrefDest" class="qref-dest"></span>
  </div>
</div>
{body}
<div class="foot"><b>POTATO</b> · Watermark &amp; Copyright &copy; 2026 <b>{POTATO_AUTHOR}</b> · Open Source under GNU {POTATO_LICENSE} (free to modify — keep author watermark &amp; third-party credits intact)</div>
<script>
(function(){{
  function initOriginBtn(){{
    var b = document.getElementById('liveOriginBtn');
    if(!b) return;
    var u = window.location.origin + '/';
    b.textContent = 'URL: ' + u;
    b.dataset.url = u;
    b.onclick = function(){{
      if(navigator.clipboard && navigator.clipboard.writeText){{
        navigator.clipboard.writeText(u).then(function(){{ b.textContent = 'COPIED: ' + u; setTimeout(function(){{ b.textContent = 'URL: ' + u; }}, 1600); }}).catch(function(){{}});
      }} else {{
        try {{ window.prompt('Live POTATO URL:', u); }} catch(e){{}}
      }}
    }};
  }}
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initOriginBtn);
  else initOriginBtn();
}})();
</script>{GRID_NAV_JS}</body></html>"""
    return doc.encode("utf-8")


def parse_multipart_single_file(content_type: str, rfile, content_length: int):
    """
    100% pure Python stdlib streaming multipart/form-data file reader.
    Works across Python 3.8–3.14+ (zero dependency on deprecated `cgi`).
    Returns (filename, temp_file_path, total_written) or raises ValueError.
    """
    m = re.search(r'boundary=(?:"([^"]+)"|([^\s;]+))', content_type, re.IGNORECASE)
    if not m:
        raise ValueError("Missing multipart boundary")
    boundary = (m.group(1) or m.group(2)).encode("latin-1")
    delim = b"--" + boundary
    if content_length <= 0 or content_length > MAX_UPLOAD_BYTES:
        raise ValueError("Upload size out of allowed range")

    remaining = content_length
    buf = b""

    def read_more(n=65536):
        nonlocal remaining
        if remaining <= 0:
            return b""
        chunk = rfile.read(min(n, remaining))
        remaining -= len(chunk)
        return chunk

    # Read until we locate the file part header
    while b"\r\n\r\n" not in buf:
        chunk = read_more(65536)
        if not chunk:
            raise ValueError("Incomplete multipart headers")
        buf += chunk
        if len(buf) > 1024 * 1024:
            raise ValueError("Multipart headers too large")

    # Walk parts until we find one with filename="..."
    filename = ""
    while True:
        idx = buf.find(delim)
        if idx == -1:
            chunk = read_more(65536)
            if not chunk:
                raise ValueError("No file part found")
            buf += chunk
            continue
        buf = buf[idx + len(delim):]
        if buf.startswith(b"--"):
            raise ValueError("No file uploaded")
        if buf.startswith(b"\r\n"):
            buf = buf[2:]
        while b"\r\n\r\n" not in buf:
            chunk = read_more(65536)
            if not chunk:
                raise ValueError("Truncated part headers")
            buf += chunk
        hdr_raw, buf = buf.split(b"\r\n\r\n", 1)
        hdr_text = hdr_raw.decode("utf-8", errors="ignore")
        fn_match = re.search(r'filename="([^"]*)"', hdr_text)
        if fn_match and fn_match.group(1).strip():
            filename = fn_match.group(1).strip()
            break
        # Skip non-file form fields
        next_idx = buf.find(b"\r\n" + delim)
        while next_idx == -1:
            chunk = read_more(65536)
            if not chunk:
                raise ValueError("No file field found")
            buf += chunk
            next_idx = buf.find(b"\r\n" + delim)
        buf = buf[next_idx + 2:]

    safe_name = sanitize_filename(filename)
    if not safe_name:
        raise ValueError("Invalid filename")
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in UPLOAD_ALLOWED_EXTS:
        raise ValueError(f"Unsupported file type: {ext or '(none)'}")

    if ext in PLAYLIST_EXTS:
        dest_dir = os.path.join(BASE_DIR, "playlists")
    else:
        dest_dir = os.path.join(MEDIA_ROOT, "Uploads")
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, safe_name)
    tmp_path = dest_path + ".part"

    end_marker = b"\r\n" + delim
    keep_tail = len(end_marker) + 4
    written = 0
    try:
        with open(tmp_path, "wb") as out:
            while True:
                pos = buf.find(end_marker)
                if pos != -1:
                    out.write(buf[:pos])
                    written += pos
                    break
                if len(buf) > keep_tail:
                    flush_n = len(buf) - keep_tail
                    out.write(buf[:flush_n])
                    written += flush_n
                    buf = buf[flush_n:]
                chunk = read_more(65536)
                if not chunk:
                    raise ValueError("Unexpected end of upload stream")
                buf += chunk
        # Drain any small trailing multipart bytes cleanly
        while remaining > 0:
            if not read_more(65536):
                break
        os.replace(tmp_path, dest_path)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        raise
    return safe_name, dest_path, ext, written


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 64


class PotatoHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _add_security_headers(self):
        self.send_header("X-Potato-Author", POTATO_AUTHOR)
        self.send_header("X-Potato-License", POTATO_LICENSE)
        self.send_header("X-Potato-Origin", POTATO_REPO)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "no-referrer")

    def _send(self, code: int, ctype: str, data: bytes, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self._add_security_headers()
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, location: str):
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self._add_security_headers()
        self.end_headers()

    def _check_same_origin(self) -> bool:
        host = (self.headers.get("Host") or "").strip().lower()
        for hdr_name in ("Origin", "Referer"):
            val = (self.headers.get(hdr_name) or "").strip()
            if val:
                netloc = urllib.parse.urlparse(val).netloc.lower()
                if netloc and host and netloc != host:
                    return False
        return True

    def _valid_csrf(self, token: str) -> bool:
        return bool(token) and hmac.compare_digest(token, CSRF_TOKEN)

    def _parse_content_length(self) -> int:
        raw = (self.headers.get("Content-Length") or "0").strip()
        try:
            n = int(raw)
            return n if n >= 0 else -1
        except ValueError:
            return -1

    def _read_urlencoded_form(self) -> dict:
        clen = self._parse_content_length()
        if clen <= 0 or clen > 256 * 1024:
            return {}
        raw = self.rfile.read(clen).decode("utf-8", errors="ignore")
        return urllib.parse.parse_qs(raw, keep_blank_values=True)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if not self._check_same_origin():
            self._send(403, "text/plain", b"Cross-origin POST rejected")
            return

        if parsed.path == "/setup/folder":
            form = self._read_urlencoded_form()
            if not self._valid_csrf((form.get("csrf") or [""])[0]):
                self._send(403, "text/plain", b"Invalid or missing CSRF token")
                return
            new_root = (form.get("media_root") or [""])[0].strip()
            allowed_raw = (form.get("allowed_folders") or [""])[0].strip()
            inc_open = "include_open_directory" in form
            if new_root and is_filesystem_root(new_root):
                self._redirect("/setup?err=" + urllib.parse.quote("For safety, pick a specific media subfolder instead of the whole root drive."))
                return
            cfg = load_config()
            if new_root:
                cfg["media_root"] = new_root
            cfg["allowed_folders"] = [x.strip() for x in allowed_raw.split(",") if x.strip()]
            cfg["include_open_directory"] = inc_open
            save_config(cfg)
            apply_runtime_config(cfg)
            cats = scan_media(force=True)
            total_m = sum(len(v) for v in cats.values())
            msg = f"Saved folder settings. Indexed {total_m:,} media files."
            self._redirect(f"/setup?msg={urllib.parse.quote(msg)}")
            return

        if parsed.path == "/setup/upload":
            if not self._valid_csrf((qs.get("csrf") or [""])[0]):
                self._send(403, "text/plain", b"Invalid or missing CSRF token")
                return
            ctype = self.headers.get("Content-Type") or ""
            clen = self._parse_content_length()
            if clen <= 0:
                self._send(400, "text/plain", b"Invalid Content-Length")
                return
            try:
                safe_name, dest_path, ext, written = parse_multipart_single_file(ctype, self.rfile, clen)
                cfg = load_config()
                if ext in PLAYLIST_EXTS:
                    rel_pl = os.path.relpath(dest_path, BASE_DIR)
                    pls = list(cfg.get("m3u_playlists") or [])
                    if rel_pl not in pls and dest_path not in pls:
                        pls.append(rel_pl)
                        cfg["m3u_playlists"] = pls
                        save_config(cfg)
                        apply_runtime_config(cfg)
                    parse_m3u(force=True)
                    msg = f"Uploaded playlist '{safe_name}' ({written:,} bytes) — ready in Playlists!"
                else:
                    af = list(cfg.get("allowed_folders") or [])
                    if af and "Uploads" not in af:
                        af.append("Uploads")
                        cfg["allowed_folders"] = af
                        save_config(cfg)
                        apply_runtime_config(cfg)
                    scan_media(force=True)
                    msg = f"Uploaded '{safe_name}' ({written:,} bytes) to Uploads — ready in Library!"
                self._redirect(f"/setup?msg={urllib.parse.quote(msg)}")
            except Exception as e:
                self._redirect(f"/setup?err={urllib.parse.quote(f'Upload failed: {e}')}")
            return

        if parsed.path == "/setup/bookmark":
            form = self._read_urlencoded_form()
            if not self._valid_csrf((form.get("csrf") or [""])[0]):
                self._send(403, "text/plain", b"Invalid or missing CSRF token")
                return
            name = (form.get("name") or [""])[0].strip()[:80]
            url = (form.get("url") or [""])[0].strip()[:400]
            badge = ((form.get("badge") or ["LINK"])[0].strip().upper()[:10]) or "LINK"
            desc = (form.get("desc") or [""])[0].strip()[:140]
            if not name or not url.startswith(("http://", "https://")):
                self._redirect("/setup?err=" + urllib.parse.quote("Enter a button name and a valid http:// or https:// URL."))
                return
            cfg = load_config()
            links = list(cfg.get("custom_links") or [])
            links.append({"name": name, "url": url, "color": "#ffd166", "badge": badge, "desc": desc})
            cfg["custom_links"] = links
            save_config(cfg)
            apply_runtime_config(cfg)
            self._redirect("/setup?msg=" + urllib.parse.quote(f"Added bookmark button '{name}' to Home!"))
            return

        if parsed.path == "/setup/bookmark_del":
            form = self._read_urlencoded_form()
            if not self._valid_csrf((form.get("csrf") or [""])[0]):
                self._send(403, "text/plain", b"Invalid or missing CSRF token")
                return
            idx_s = (form.get("idx") or ["-1"])[0]
            if idx_s.isdigit():
                idx = int(idx_s)
                cfg = load_config()
                links = list(cfg.get("custom_links") or [])
                if 0 <= idx < len(links):
                    removed = links.pop(idx)
                    cfg["custom_links"] = links
                    save_config(cfg)
                    apply_runtime_config(cfg)
                    self._redirect("/setup?msg=" + urllib.parse.quote(f"Removed bookmark '{removed.get('name', '')}'."))
                    return
            self._redirect("/setup")
            return

        if parsed.path == "/freqs/save":
            form = self._read_urlencoded_form()
            if not self._valid_csrf((form.get("csrf") or [""])[0]):
                self._send(403, "text/plain", b"Invalid or missing CSRF token")
                return
            try:
                base_hz = float((form.get("base_hz") or ["432"])[0])
                beat_hz = float((form.get("beat_hz") or ["0"])[0])
                dur = float((form.get("dur") or ["20"])[0])
            except ValueError:
                self._redirect("/freqs?err=" + urllib.parse.quote("Invalid frequency numbers."))
                return
            wtype = (form.get("wave") or ["sine"])[0]
            if wtype not in ("sine", "triangle", "drone"):
                wtype = "sine"
            label = sanitize_filename((form.get("label") or [""])[0])
            if not label:
                label = f"POTATO_{base_hz:.1f}Hz" + (f"_{beat_hz:.2f}HzBeat" if beat_hz > 0 else "") + f"_{wtype}"
            fname = label if label.lower().endswith(".wav") else f"{label}.wav"
            dest_dir = os.path.join(MEDIA_ROOT, "Frequencies")
            os.makedirs(dest_dir, exist_ok=True)
            wav_bytes = generate_tone_wav(base_hz, beat_hz, wtype, dur)
            with open(os.path.join(dest_dir, fname), "wb") as f:
                f.write(wav_bytes)
            cfg = load_config()
            af = list(cfg.get("allowed_folders") or [])
            if af and "Frequencies" not in af:
                af.append("Frequencies")
                cfg["allowed_folders"] = af
                save_config(cfg)
                apply_runtime_config(cfg)
            scan_media(force=True)
            self._redirect("/freqs?msg=" + urllib.parse.quote(f"Saved '{fname}' to Library/Frequencies ({len(wav_bytes):,} bytes)!"))
            return

        if parsed.path == "/freqs/save_pack":
            form = self._read_urlencoded_form()
            if not self._valid_csrf((form.get("csrf") or [""])[0]):
                self._send(403, "text/plain", b"Invalid or missing CSRF token")
                return
            dest_dir = os.path.join(MEDIA_ROOT, "Frequencies")
            os.makedirs(dest_dir, exist_ok=True)
            count = 0
            for pid, name, bhz, beat, wtype, _, _, _, _ in FREQ_PRESETS:
                fname = sanitize_filename(f"{pid}_{int(bhz)}Hz.wav")
                wav_bytes = generate_tone_wav(bhz, beat, wtype, 15.0)
                with open(os.path.join(dest_dir, fname), "wb") as f:
                    f.write(wav_bytes)
                count += 1
            cfg = load_config()
            af = list(cfg.get("allowed_folders") or [])
            if af and "Frequencies" not in af:
                af.append("Frequencies")
                cfg["allowed_folders"] = af
                save_config(cfg)
                apply_runtime_config(cfg)
            scan_media(force=True)
            self._redirect("/freqs?msg=" + urllib.parse.quote(f"Attached all {count} meditation waveform .WAV files into Library/Frequencies!"))
            return

        self._send(404, "text/plain", b"Unknown POST route")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        host_hdr = self.headers.get("Host") or f"{detect_lan_ip()}:{PORT}"

        if parsed.path == "/manifest.json":
            manifest = {
                "name": POTATO_NAME,
                "short_name": POTATO_NAME,
                "description": f"LAN media hub & TV-remote transmitter by {POTATO_AUTHOR} ({POTATO_LICENSE})",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#06080c",
                "theme_color": "#0d0c09",
                "icons": [
                    {"src": "/assets/potato_icon_192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
                    {"src": "/assets/potato_icon.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
                    {"src": "/assets/potato_icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
                ],
            }
            self._send(200, "application/manifest+json; charset=utf-8", json.dumps(manifest, indent=2).encode("utf-8"))
            return
        if parsed.path == "/qr.svg":
            # Strict allowlist prevents open QR phishing abuse
            target = (qs.get("target") or ["home"])[0].strip().lower()
            lan_base = f"http://{detect_lan_ip()}:{PORT}"
            allowed_targets = {
                "home": f"{lan_base}/",
                "setup": f"{lan_base}/setup",
                "freqs": f"{lan_base}/freqs",
                "m3u": f"{lan_base}/playlist.m3u",
            }
            qr_url = allowed_targets.get(target)
            if not qr_url:
                self._send(400, "text/plain", b"Invalid QR target")
                return
            self._send(200, "image/svg+xml; charset=utf-8", make_qr_svg(qr_url))
            return
        if parsed.path == "/device.xml":
            lan_base = f"http://{detect_lan_ip()}:{PORT}"
            xml = (
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<root xmlns="urn:schemas-upnp-org:device-1-0">\n'
                '  <specVersion><major>1</major><minor>0</minor></specVersion>\n'
                '  <device>\n'
                '    <deviceType>urn:schemas-upnp-org:device:Basic:1</deviceType>\n'
                f'    <friendlyName>{POTATO_NAME} ({html_lib.escape(NODE_NAME)})</friendlyName>\n'
                f'    <manufacturer>{POTATO_AUTHOR}</manufacturer>\n'
                f'    <modelDescription>Zero-Dependency LAN Media Hub (GPLv3)</modelDescription>\n'
                f'    <modelName>{POTATO_NAME}</modelName>\n'
                f'    <modelNumber>{POTATO_VERSION}</modelNumber>\n'
                f'    <UDN>{POTATO_UDN}</UDN>\n'
                f'    <presentationURL>{html_lib.escape(lan_base)}/</presentationURL>\n'
                '  </device>\n'
                '</root>\n'
            ).encode("utf-8")
            self._send(200, "application/xml; charset=utf-8", xml)
            return
        if parsed.path == "/assets/potato_icon.svg":
            self._send(200, "image/svg+xml; charset=utf-8", RAW_POTATO_SVG.encode("utf-8"), {"Cache-Control": "public, max-age=86400"})
            return
        if parsed.path == "/assets/potato_icon.png":
            if os.path.isfile(POTATO_ICON_PATH):
                self._send(200, "image/png", open(POTATO_ICON_PATH, "rb").read(), {"Cache-Control": "public, max-age=86400"})
            else:
                self._send(200, "image/svg+xml; charset=utf-8", RAW_POTATO_SVG.encode("utf-8"))
            return
        if parsed.path == "/assets/potato_icon_192.png":
            p192 = POTATO_ICON_192_PATH if os.path.isfile(POTATO_ICON_192_PATH) else POTATO_ICON_PATH
            if os.path.isfile(p192):
                self._send(200, "image/png", open(p192, "rb").read(), {"Cache-Control": "public, max-age=86400"})
            else:
                self._send(200, "image/svg+xml; charset=utf-8", RAW_POTATO_SVG.encode("utf-8"))
            return
        if parsed.path.startswith("/assets/"):
            self._send(404, "text/plain", b"Not found")
            return
        if parsed.path == "/health":
            cats = scan_media()
            streams = parse_m3u()
            self._send(200, "application/json", json.dumps({
                "ok": True,
                "name": POTATO_NAME,
                "version": POTATO_VERSION,
                "author": POTATO_AUTHOR,
                "license": POTATO_LICENSE,
                "node": NODE_NAME,
                "ip": detect_lan_ip(),
                "transmit_url": f"http://{detect_lan_ip()}:{PORT}",
                "mdns_url": f"http://{MDNS_HOST}:{PORT}",
                "mdns_active": _DISCOVERY_STATE["mdns"],
                "ssdp_active": _DISCOVERY_STATE["ssdp"],
                "total_local_files": sum(len(v) for v in cats.values()),
                "total_m3u_channels": len(streams),
                "open_directory_enabled": INCLUDE_OPEN_DIRECTORY,
                "open_directory_count": len(OPEN_ALL) if INCLUDE_OPEN_DIRECTORY else 0,
                "ffmpeg_ready": bool(FFMPEG and os.path.isfile(FFMPEG)),
            }).encode("utf-8"))
            return
        if parsed.path == "/api/home":
            cats = scan_media()
            streams = parse_m3u()
            self._send(200, "application/json", json.dumps({
                "ok": True,
                "name": POTATO_NAME,
                "version": POTATO_VERSION,
                "author": POTATO_AUTHOR,
                "host": host_hdr,
                "total_local_files": sum(len(v) for v in cats.values()),
                "total_m3u_channels": len(streams),
                "folders": [{"name": g, "count": len(cats[g])} for g in sorted(cats.keys())],
                "custom_links": CUSTOM_LINKS,
            }).encode("utf-8"))
            return
        if parsed.path == "/api/library":
            cats = scan_media()
            names = sorted(cats.keys())
            cat = (qs.get("cat") or [names[0] if names else ""])[0]
            page = max(0, int((qs.get("p") or ["0"])[0])) if (qs.get("p") or ["0"])[0].isdigit() else 0
            per = 40
            items = cats.get(cat, [])
            chunk = items[page * per : (page + 1) * per]
            self._send(200, "application/json", json.dumps({
                "cat": cat, "page": page, "total": len(items),
                "has_next": (page + 1) * per < len(items),
                "items": [{"name": m["name"], "url": f"http://{host_hdr}/media?path={urllib.parse.quote(m['path'], safe='')}"} for m in chunk],
            }).encode("utf-8"))
            return
        if parsed.path == "/api/playlists":
            streams = parse_m3u()
            page = max(0, int((qs.get("p") or ["0"])[0])) if (qs.get("p") or ["0"])[0].isdigit() else 0
            per = 40
            chunk = streams[page * per : (page + 1) * per]
            self._send(200, "application/json", json.dumps({
                "page": page, "total": len(streams), "has_next": (page + 1) * per < len(streams),
                "items": [{"name": x["title"], "group": x["group"], "url": x["url"]} for x in chunk],
            }).encode("utf-8"))
            return
        if parsed.path == "/api/open":
            self._send(200, "application/json", json.dumps({
                "enabled": INCLUDE_OPEN_DIRECTORY,
                "weird_rabbit_holes": [{"name": n, "url": u, "color": c, "badge": b, "desc": d} for n, u, c, b, d in OPEN_WEIRD_RABBIT_HOLES],
                "shortwave_radio": [{"name": n, "url": u, "color": c, "badge": b, "desc": d} for n, u, c, b, d in OPEN_SHORTWAVE_RADIO],
                "cinema_video": [{"name": n, "url": u, "color": c, "badge": b, "desc": d} for n, u, c, b, d in OPEN_CINEMA_VIDEO],
                "foss_players": [{"name": n, "url": u, "color": c, "badge": b, "desc": d} for n, u, c, b, d in OPEN_FOSS_PLAYERS],
            }).encode("utf-8"))
            return
        if parsed.path == "/library":
            self._handle_library(qs)
            return
        if parsed.path == "/playlists":
            self._handle_playlists(qs)
            return
        if parsed.path == "/open":
            self._handle_open()
            return
        if parsed.path == "/freqs":
            self._handle_freqs(qs, host_hdr)
            return
        if parsed.path == "/freqs/wav":
            try:
                base_hz = float((qs.get("base") or ["432"])[0])
                beat_hz = float((qs.get("beat") or ["0"])[0])
                dur = float((qs.get("dur") or ["15"])[0])
            except ValueError:
                self._send(400, "text/plain", b"Invalid frequency parameter")
                return
            wtype = (qs.get("wave") or ["sine"])[0]
            if wtype not in ("sine", "triangle", "drone"):
                wtype = "sine"
            wav_bytes = generate_tone_wav(base_hz, beat_hz, wtype, dur)
            fname = sanitize_filename(f"POTATO_{base_hz:.1f}Hz_{beat_hz:.2f}Hz_{wtype}.wav")
            self._send(200, "audio/wav", wav_bytes, {"Content-Disposition": f'attachment; filename="{fname}"'})
            return
        if parsed.path == "/setup":
            self._handle_setup(qs, host_hdr)
            return
        if parsed.path == "/lite" or parsed.path.startswith("/lite/"):
            self._handle_lite(parsed.path, qs, host_hdr)
            return
        if parsed.path == "/status":
            self._handle_status(host_hdr)
            return
        if parsed.path == "/playlist.m3u":
            self._handle_export_m3u(host_hdr)
            return
        if parsed.path == "/media":
            self._handle_media(qs)
            return
        if parsed.path == "/stream":
            self._handle_ffmpeg_file(qs)
            return
        if parsed.path == "/live_mp4":
            self._handle_live_mp4(qs)
            return
        if parsed.path == "/proxy":
            self._handle_proxy(qs, host_hdr)
            return
        if parsed.path == "/watch":
            self._handle_watch(qs, host_hdr)
            return
        if (qs.get("lite") or [""])[0] == "1" or ((qs.get("full") or [""])[0] != "1" and is_legacy_client(self.headers.get("User-Agent", ""))):
            self._handle_lite("/lite", qs, host_hdr)
            return
        self._handle_home(host_hdr)

    def _ext_tile(self, name: str, url: str, color: str, badge: str = "WEB", desc: str = "") -> str:
        if not url.startswith(("http://", "https://")):
            url = "#"
        safe_url = html_lib.escape(url, quote=True)
        host = urllib.parse.urlparse(url).netloc or url
        return tile_btn(
            name,
            "openExternal(this.dataset.extUrl)",
            acc=color,
            extra_attrs=f'data-ext-url="{safe_url}"',
            badge=badge,
            desc=desc or f"Opens {host}",
            dest=host,
        )

    def _stream_tile(self, item: dict, back: str) -> str:
        u = item["url"]
        lo = u.lower()
        is_aud = any(x in lo for x in (".mp3", "-mp3", ".aac", ".ogg", ".opus", "somafm.com/"))
        badge = "RADIO" if is_aud else "PLAY"
        desc = f"{item['group']} · Plays inside POTATO"
        href = f"/watch?live={urllib.parse.quote(u, safe='')}&title={urllib.parse.quote(item['title'], safe='')}&back={back}"
        return tile_btn(item["title"], f"location.href='{href}'", acc="#14b8a6", badge=badge, desc=desc, dest="Built-in Player")

    def _handle_home(self, host_hdr: str):
        cats = scan_media()
        streams = parse_m3u()
        total_m = sum(len(v) for v in cats.values())
        lan_url = f"http://{detect_lan_ip()}:{PORT}"
        folder_cards = [
            tile_btn(
                f"{g} ({len(cats[g]):,})",
                f"location.href='/library?cat={urllib.parse.quote(g, safe='')}'",
                acc="#3b82f6",
                badge="LOCAL",
                desc=f"{len(cats[g]):,} local media files in {g}",
                dest=f"/library?cat={g}",
            )
            for g in sorted(cats.keys())
        ]
        stream_preview = [self._stream_tile(x, "/") for x in streams[:8]]
        custom_cards = [
            self._ext_tile(
                str(item.get("name", "Link")),
                str(item.get("url", "#")),
                str(item.get("color", "#ffd166")),
                badge=str(item.get("badge", "LINK")),
                desc=str(item.get("desc", "")),
            )
            for item in CUSTOM_LINKS
            if isinstance(item, dict) and str(item.get("url", "")).startswith(("http://", "https://"))
        ]
        parts = [
            f'<h2>Your Local Vault ({total_m:,} Files)</h2>'
            + (
                f'<div class="grid">{"".join(folder_cards)}</div>'
                if folder_cards
                else (
                    '<div class="grid">'
                    + tile_btn("Upload Videos or M3U Now", "location.href='/setup'", acc="#22c55e", badge="EASY", desc="Upload straight from your phone or PC browser — no coding!", dest="/setup")
                    + tile_btn("Point at Your Media Folder", "location.href='/setup'", acc="#3b82f6", badge="SETUP", desc="Pick your Movies or Docs folder in 1 click inside Easy Setup", dest="/setup")
                    + tile_btn(f"TV Transmit: {lan_url}", "copyText(this.dataset.copy,this.dataset.copyLabel)", acc="#ffd166", extra_attrs=f'data-copy="{html_lib.escape(lan_url, quote=True)}" data-copy-label="TV Transmit URL"', badge="TV", desc="Open this address in your Smart TV browser or TV Bro — tap to copy", dest=lan_url)
                    + tile_btn("Meditation Audio Tone Generator", "location.href='/freqs'", acc="#10b981", badge="HZ", desc="Adjustable 20–1200 Hz waveforms, binaural beats & WAV vault", dest="/freqs")
                    + "</div>"
                )
            )
        ]
        if stream_preview:
            parts.append(
                f'<h2>Instant Play — Built-In Player ({len(streams):,} Streams)</h2>'
                f'<div class="grid">{"".join(stream_preview)}</div>'
            )
        if custom_cards:
            parts.append(
                f'<h2>Your Custom Buttons ({len(custom_cards)})</h2>'
                f'<div class="grid">{"".join(custom_cards)}</div>'
            )
        if INCLUDE_OPEN_DIRECTORY:
            featured = OPEN_WEIRD_RABBIT_HOLES[:4] + OPEN_SHORTWAVE_RADIO[:4]
            feat_cards = [self._ext_tile(n, u, c, b, d) for n, u, c, b, d in featured]
            parts.append(
                f'<h2>Rabbit Holes &amp; Radio (See Rabbit Holes Tab for All {len(OPEN_ALL)})</h2>'
                f'<div class="grid">{"".join(feat_cards)}</div>'
            )
        self._send(200, "text/html; charset=utf-8", render_page(host_hdr, "home", "".join(parts), total_m, len(streams)))

    def _handle_open(self):
        cats = scan_media()
        streams = parse_m3u()
        total_m = sum(len(v) for v in cats.values())
        if not INCLUDE_OPEN_DIRECTORY:
            body = '<div class="status"><div class="status-in">Rabbit Holes &amp; Open Directory is turned OFF. Re-enable anytime on the Easy Setup tab.</div></div>'
            self._send(200, "text/html; charset=utf-8", render_page("Rabbit Holes", "open", body, total_m, len(streams)))
            return
        body = (
            '<div class="status"><div class="status-in">External Links &amp; Attribution: Every external site, archive, and GitHub repository below is an independent project owned by its respective creator — full credit belongs strictly to those authors.</div></div>'
            f'<h2>Weird, Underground &amp; Rabbit Hole Docs ({len(OPEN_WEIRD_RABBIT_HOLES)})</h2>'
            f'<div class="grid">{"".join(self._ext_tile(n, u, c, b, d) for n, u, c, b, d in OPEN_WEIRD_RABBIT_HOLES)}</div>'
            f'<h2>Shortwave SDR &amp; Underground Radio ({len(OPEN_SHORTWAVE_RADIO)})</h2>'
            f'<div class="grid">{"".join(self._ext_tile(n, u, c, b, d) for n, u, c, b, d in OPEN_SHORTWAVE_RADIO)}</div>'
            f'<h2>Public Domain Cinema &amp; Independent Video ({len(OPEN_CINEMA_VIDEO)})</h2>'
            f'<div class="grid">{"".join(self._ext_tile(n, u, c, b, d) for n, u, c, b, d in OPEN_CINEMA_VIDEO)}</div>'
            f'<h2>Open-Source TV Browsers, Kodi &amp; Players — GPL / FOSS ({len(OPEN_FOSS_PLAYERS)})</h2>'
            f'<div class="grid">{"".join(self._ext_tile(n, u, c, b, d) for n, u, c, b, d in OPEN_FOSS_PLAYERS)}</div>'
        )
        self._send(200, "text/html; charset=utf-8", render_page("Rabbit Holes & Open Media", "open", body, total_m, len(streams)))

    def _handle_freqs(self, qs, host_hdr: str):
        cats = scan_media()
        streams = parse_m3u()
        total_m = sum(len(v) for v in cats.values())
        msg = (qs.get("msg") or [""])[0]
        err = (qs.get("err") or [""])[0]
        notice = ""
        if msg:
            notice = f'<div class="notice"><div class="notice-in">✓ {html_lib.escape(msg)}</div></div>'
        elif err:
            notice = f'<div class="notice err"><div class="notice-in">! {html_lib.escape(err)}</div></div>'

        csrf_val = html_lib.escape(CSRF_TOKEN, quote=True)
        csrf_inp = f'<input type="hidden" name="csrf" value="{csrf_val}">'
        freq_files = cats.get("Frequencies", [])
        folder_cards = [
            tile_btn(
                m["name"],
                f"location.href='/watch?path={urllib.parse.quote(m['path'], safe='')}&back=/freqs'",
                acc="#10b981",
                badge="WAV",
                desc="Saved in your Frequencies folder · Plays in POTATO, VLC & Kodi",
                dest="/library?cat=Frequencies",
            )
            for m in freq_files[:40]
        ]

        brainwave_cards = []
        solfeggio_cards = []
        for pid, name, bhz, beat, wtype, color, badge, best_for, dirs in FREQ_PRESETS:
            attrs = (
                f'data-base="{bhz}" data-beat="{beat}" data-wave="{wtype}" '
                f'data-pname="{html_lib.escape(name, quote=True)}" '
                f'data-best="{html_lib.escape(best_for, quote=True)}" '
                f'data-dirs="{html_lib.escape(dirs, quote=True)}"'
            )
            card = tile_btn(
                name,
                "loadFreqPreset(this)",
                acc=color,
                extra_attrs=attrs,
                badge=badge,
                desc=best_for,
                dest=f"{bhz:g} Hz" + (f" + {beat:g} Hz beat" if beat > 0 else " pure tone"),
            )
            if beat > 0:
                brainwave_cards.append(card)
            else:
                solfeggio_cards.append(card)

        synth_js = """
<script>
(function(){
  var ac = null, oscL = null, oscR = null, subL = null, subR = null, fifthL = null, fifthR = null;
  var masterGain = null, analyser = null, playing = false, rafId = null, timerEnd = 0, timerInt = null;

  function el(id){ return document.getElementById(id); }

  function syncOutputs(){
    var b = parseFloat(el('fBase').value || '432');
    var bt = parseFloat(el('fBeat').value || '0');
    var v = parseFloat(el('fVol').value || '22');
    var w = el('fWave').value || 'sine';
    el('fBaseNum').value = b;
    el('fBeatNum').value = bt;
    el('fBaseVal').textContent = b.toFixed(1) + ' Hz';
    el('fBeatVal').textContent = bt > 0 ? (bt.toFixed(2) + ' Hz Binaural (' + (b - bt/2).toFixed(1) + ' L / ' + (b + bt/2).toFixed(1) + ' R)') : '0.00 Hz (Pure Room Tone)';
    el('fVolVal').textContent = Math.round(v) + '%';
    el('saveBase').value = b;
    el('saveBeat').value = bt;
    el('saveWave').value = w;
    if(playing && ac){
      var now = ac.currentTime;
      var fl = Math.max(20, b - bt/2), fr = Math.max(20, b + bt/2);
      if(oscL) oscL.frequency.setTargetAtTime(fl, now, 0.05);
      if(oscR) oscR.frequency.setTargetAtTime(fr, now, 0.05);
      if(subL) subL.frequency.setTargetAtTime(fl * 0.5, now, 0.05);
      if(subR) subR.frequency.setTargetAtTime(fr * 0.5, now, 0.05);
      if(fifthL) fifthL.frequency.setTargetAtTime(fl * 1.5, now, 0.05);
      if(fifthR) fifthR.frequency.setTargetAtTime(fr * 1.5, now, 0.05);
      if(masterGain) masterGain.gain.setTargetAtTime((v / 100) * 0.35, now, 0.06);
    }
  }

  function drawScope(){
    var cv = el('freqScope');
    if(!cv) return;
    var ctx = cv.getContext('2d');
    var w = cv.width = cv.clientWidth || 640;
    var h = cv.height = 110;
    ctx.fillStyle = 'rgba(6,9,15,0.92)';
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = 'rgba(255,209,102,0.18)';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, h/2); ctx.lineTo(w, h/2); ctx.stroke();

    if(playing && analyser){
      var buf = new Uint8Array(analyser.fftSize);
      analyser.getByteTimeDomainData(buf);
      ctx.strokeStyle = '#ffd166';
      ctx.shadowColor = 'rgba(255,209,102,0.85)';
      ctx.shadowBlur = 10;
      ctx.lineWidth = 2.4;
      ctx.beginPath();
      var slice = w / buf.length;
      for(var i = 0; i < buf.length; i++){
        var y = (buf[i] / 128.0) * (h / 2);
        if(i === 0) ctx.moveTo(0, y);
        else ctx.lineTo(i * slice, y);
      }
      ctx.stroke();
      ctx.shadowBlur = 0;
      rafId = requestAnimationFrame(drawScope);
    } else {
      var b = parseFloat(el('fBase').value || '432');
      var cycles = Math.max(2, Math.min(28, b / 38));
      ctx.strokeStyle = 'rgba(255,209,102,0.55)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      for(var x = 0; x < w; x++){
        var t = (x / w) * Math.PI * 2 * cycles;
        var y = h/2 + Math.sin(t) * (h * 0.28);
        if(x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
  }

  window.stopFreqTone = function(){
    if(timerInt){ clearInterval(timerInt); timerInt = null; }
    el('freqTimerBadge').textContent = 'IDLE';
    if(!playing){ drawScope(); return; }
    playing = false;
    if(rafId){ cancelAnimationFrame(rafId); rafId = null; }
    try{
      if(ac && masterGain){
        var now = ac.currentTime;
        masterGain.gain.cancelScheduledValues(now);
        masterGain.gain.setTargetAtTime(0.0001, now, 0.08);
        var oldAc = ac;
        setTimeout(function(){ try{ oldAc.close(); }catch(e){} }, 350);
      }
    }catch(e){}
    ac = oscL = oscR = subL = subR = fifthL = fifthR = masterGain = analyser = null;
    el('freqState').textContent = 'Stopped — adjust any Hz or click a preset below';
    drawScope();
  };

  window.startFreqTone = function(){
    if(playing) window.stopFreqTone();
    var AudioCtx = window.AudioContext || window.webkitAudioContext;
    if(!AudioCtx){ alert('Web Audio API is not supported in this browser.'); return; }
    ac = new AudioCtx();
    var b = parseFloat(el('fBase').value || '432');
    var bt = parseFloat(el('fBeat').value || '0');
    var v = parseFloat(el('fVol').value || '22');
    var w = el('fWave').value || 'sine';
    var fl = Math.max(20, b - bt/2), fr = Math.max(20, b + bt/2);

    masterGain = ac.createGain();
    masterGain.gain.setValueAtTime(0.0001, ac.currentTime);
    masterGain.gain.linearRampToValueAtTime((v / 100) * 0.35, ac.currentTime + 0.35);

    analyser = ac.createAnalyser();
    analyser.fftSize = 1024;

    var merger = ac.createChannelMerger(2);
    var gL = ac.createGain(), gR = ac.createGain();
    gL.gain.value = 1; gR.gain.value = 1;

    oscL = ac.createOscillator(); oscR = ac.createOscillator();
    oscL.type = (w === 'triangle') ? 'triangle' : 'sine';
    oscR.type = (w === 'triangle') ? 'triangle' : 'sine';
    oscL.frequency.value = fl;
    oscR.frequency.value = fr;
    oscL.connect(gL); oscR.connect(gR);

    if(w === 'drone'){
      subL = ac.createOscillator(); subR = ac.createOscillator();
      fifthL = ac.createOscillator(); fifthR = ac.createOscillator();
      subL.type = subR.type = fifthL.type = fifthR.type = 'sine';
      subL.frequency.value = fl * 0.5; subR.frequency.value = fr * 0.5;
      fifthL.frequency.value = fl * 1.5; fifthR.frequency.value = fr * 1.5;
      var sg = ac.createGain(); sg.gain.value = 0.28;
      var fg = ac.createGain(); fg.gain.value = 0.10;
      subL.connect(sg); sg.connect(gL);
      subR.connect(sg); sg.connect(gR);
      fifthL.connect(fg); fg.connect(gL);
      fifthR.connect(fg); fg.connect(gR);
      subL.start(); subR.start(); fifthL.start(); fifthR.start();
    }

    gL.connect(merger, 0, 0);
    gR.connect(merger, 0, 1);
    merger.connect(masterGain);
    masterGain.connect(analyser);
    analyser.connect(ac.destination);
    oscL.start(); oscR.start();
    playing = true;

    var mins = parseInt(el('fTimer').value || '0', 10);
    if(mins > 0){
      timerEnd = Date.now() + mins * 60000;
      timerInt = setInterval(function(){
        var rem = Math.max(0, Math.round((timerEnd - Date.now()) / 1000));
        var mm = Math.floor(rem / 60), ss = rem % 60;
        el('freqTimerBadge').textContent = mm + ':' + (ss < 10 ? '0' : '') + ss;
        if(rem <= 0){ window.stopFreqTone(); if(window.uiToast) window.uiToast('Session timer finished — faded out cleanly'); }
      }, 500);
    } else {
      el('freqTimerBadge').textContent = 'LIVE';
    }
    el('freqState').textContent = 'PLAYING · ' + b.toFixed(1) + ' Hz' + (bt > 0 ? (' + ' + bt.toFixed(2) + ' Hz binaural') : ' pure tone') + ' (' + w + ')';
    drawScope();
  };

  window.loadFreqPreset = function(btn){
    el('fBase').value = btn.dataset.base;
    el('fBeat').value = btn.dataset.beat;
    el('fWave').value = btn.dataset.wave || 'sine';
    el('presetTitle').textContent = btn.dataset.pname || 'Custom Frequency';
    el('presetBest').textContent = btn.dataset.best || '';
    el('presetDirs').textContent = btn.dataset.dirs || '';
    el('saveLabel').value = (btn.dataset.pname || 'Custom').replace(/[^A-Za-z0-9._ -]+/g, '').trim();
    syncOutputs();
    window.startFreqTone();
    if(window.uiToast) window.uiToast('Tuned: ' + (btn.dataset.pname || 'Custom Hz'));
  };

  window.downloadCurrentWav = function(){
    var b = encodeURIComponent(el('fBase').value || '432');
    var bt = encodeURIComponent(el('fBeat').value || '0');
    var w = encodeURIComponent(el('fWave').value || 'sine');
    location.href = '/freqs/wav?base=' + b + '&beat=' + bt + '&wave=' + w + '&dur=20';
  };

  document.addEventListener('DOMContentLoaded', function(){
    ['fBase','fBeat','fVol','fWave'].forEach(function(id){
      var x = el(id);
      if(x) x.addEventListener('input', function(){ syncOutputs(); if(!playing) drawScope(); });
    });
    el('fBaseNum').addEventListener('change', function(){ el('fBase').value = this.value; syncOutputs(); if(!playing) drawScope(); });
    el('fBeatNum').addEventListener('change', function(){ el('fBeat').value = this.value; syncOutputs(); if(!playing) drawScope(); });
    syncOutputs();
    drawScope();
  });
})();
</script>
"""

        body = (
            notice
            + '<h2>Adjustable Meditation &amp; Brainwave Audio Tone Generator</h2>'
            + '<div class="grid-2">'
            # Left card: Live Adjustable Synth + Oscilloscope
            + '<div class="bp-card"><div class="bp-in">'
            + '<div class="bp-tag">LIVE REAL-TIME TONE GENERATOR · 100% OFFLINE</div>'
            + '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px">'
            + '<div id="presetTitle" class="bp-name" style="margin:0">432 Hz — Natural Harmonic Tuning</div>'
            + '<span id="freqTimerBadge" class="qref-badge">IDLE</span>'
            + '</div>'
            + '<canvas id="freqScope" style="width:100%;height:110px;border-radius:9px;border:1.5px solid var(--gold);display:block;margin-bottom:10px"></canvas>'
            + '<div id="freqState" style="font-family:ui-monospace,Consolas,monospace;font-size:12.5px;color:#fde68a;margin-bottom:10px">Stopped — adjust any Hz or click a preset below</div>'
            + '<div class="grid-2" style="margin-bottom:10px">'
            + tile_btn("▶ Start / Apply Tone", "startFreqTone()", acc="#22c55e", badge="PLAY", desc="Begin smooth fade-in tone at selected Hz")
            + tile_btn("■ Stop Tone", "stopFreqTone()", acc="#ef4444", badge="STOP", desc="Smooth click-free fade out to silence")
            + '</div>'
            + '<div class="fld"><label>Base Frequency (20 – 1200 Hz): <span id="fBaseVal" style="color:#fff">432.0 Hz</span></label>'
            + '<div style="display:flex;gap:8px;align-items:center">'
            + '<input id="fBase" type="range" min="20" max="1200" step="0.5" value="432" style="flex:1;accent-color:#ffd166">'
            + '<input id="fBaseNum" type="number" min="20" max="1200" step="0.5" value="432" style="width:96px;padding:7px 9px;border-radius:9px;border:1.5px solid var(--gold);background:#080c14;color:#fff">'
            + '</div></div>'
            + '<div class="fld"><label>Binaural Beat Offset (0 – 40 Hz): <span id="fBeatVal" style="color:#fff">0.00 Hz</span></label>'
            + '<div style="display:flex;gap:8px;align-items:center">'
            + '<input id="fBeat" type="range" min="0" max="40" step="0.1" value="0" style="flex:1;accent-color:#10b981">'
            + '<input id="fBeatNum" type="number" min="0" max="40" step="0.1" value="0" style="width:96px;padding:7px 9px;border-radius:9px;border:1.5px solid var(--gold);background:#080c14;color:#fff">'
            + '</div></div>'
            + '<div class="grid-2">'
            + '<div class="fld"><label for="fWave">Waveform Shape</label><select id="fWave"><option value="sine">Pure Sine (Smooth Meditation)</option><option value="drone" selected>Soft Harmonic Drone (Warm Room)</option><option value="triangle">Warm Triangle (Focus)</option></select></div>'
            + '<div class="fld"><label for="fTimer">Auto Sleep Timer</label><select id="fTimer"><option value="0">Endless (Manual Stop)</option><option value="10">10 Minutes</option><option value="20" selected>20 Minutes</option><option value="30">30 Minutes</option><option value="60">60 Minutes</option></select></div>'
            + '</div>'
            + '<div class="fld"><label>Gentle Volume: <span id="fVolVal" style="color:#fff">22%</span></label>'
            + '<input id="fVol" type="range" min="1" max="100" step="1" value="22" style="width:100%;accent-color:#ffd166"></div>'
            + '</div></div>'
            # Right card: Situation Directions + Attach to Folder / Download WAV
            + '<div class="bp-card"><div class="bp-in">'
            + '<div class="bp-tag">DIRECTIONS &amp; SITUATION GUIDE</div>'
            + '<div class="bp-name">How to Get the Best Result</div>'
            + '<div class="status" style="margin:6px 0 12px"><div class="status-in">'
            + '<b>Best For:</b> <span id="presetBest">Warm, mellow room drone for evening chill &amp; peaceful atmosphere</span><br>'
            + '<b>Tip:</b> <span id="presetDirs">Classic warm harmonic resonance — sounds rich over living-room TV speakers.</span>'
            + '</div></div>'
            + '<ol class="steps">'
            + '<li><b>Pure Tones (0 Hz Beat):</b> Great over <b>TV speakers or soundbars</b> — fills the room with a calm harmonic anchor.</li>'
            + '<li><b>Binaural Beats (&gt; 0 Hz Beat):</b> Put on <b>stereo headphones</b> so your left and right ears receive slightly different frequencies; your brain naturally follows the difference (Delta = sleep, Theta = deep meditation, Alpha = relaxed flow, Beta = focus, Gamma = short clarity bursts).</li>'
            + '<li><b>Keep Volume Low (15–30%):</b> It should feel like a soft background breeze, never loud or fatiguing. Never use relaxation/sleep tones while driving.</li>'
            + '</ol>'
            + '<div style="border-top:1px solid rgba(255,209,102,0.3);padding-top:11px;margin-top:10px">'
            + '<div class="bp-tag">ATTACH WAVEFORMS TO YOUR LOCAL FOLDER (.WAV)</div>'
            + '<form method="post" action="/freqs/save" style="margin-bottom:10px">'
            + csrf_inp
            + '<input type="hidden" id="saveBase" name="base_hz" value="432">'
            + '<input type="hidden" id="saveBeat" name="beat_hz" value="0">'
            + '<input type="hidden" id="saveWave" name="wave" value="drone">'
            + '<input type="hidden" name="dur" value="20">'
            + '<div class="fld"><label for="saveLabel">Filename to Save in Library/Frequencies</label><input id="saveLabel" type="text" name="label" value="432Hz_Natural_Harmonic" placeholder="e.g. My_Sleep_Tone"></div>'
            + '<div class="grid-2">'
            + tile_btn("Save Current Hz to Folder", "", acc="#10b981", badge="FOLDER", desc="Writes .WAV into Library/Frequencies for TV & Kodi", btn_type="submit")
            + tile_btn("Download .WAV Now", "downloadCurrentWav()", acc="#3b82f6", badge="WAV", desc="Download a 20s stereo .WAV of your exact tuning")
            + '</div></form>'
            + '<form method="post" action="/freqs/save_pack">'
            + csrf_inp
            + tile_btn("Attach All 15 Preset .WAVs to Frequencies Folder", "", acc="#ffd166", badge="PACK", desc="1-click builds all 15 loopable .WAV files inside Library/Frequencies", btn_type="submit")
            + '</form>'
            + '</div></div></div>'
            + '</div>'
            + f'<h2>Brainwave &amp; Earth Resonance Presets (Best with Stereo Headphones · {len(brainwave_cards)})</h2>'
            + f'<div class="grid">{"".join(brainwave_cards)}</div>'
            + f'<h2>Pure Solfeggio &amp; Harmonic Room Tones (TV Speakers or Headphones · {len(solfeggio_cards)})</h2>'
            + f'<div class="grid">{"".join(solfeggio_cards)}</div>'
            + f'<h2>Your Attached Frequencies Folder ({len(freq_files)} Saved .WAV Files)</h2>'
            + (
                f'<div class="grid">{"".join(folder_cards)}</div>'
                if folder_cards
                else '<div class="status"><div class="status-in">No .WAV files attached yet — click <b>Attach All 15 Preset .WAVs to Frequencies Folder</b> above to populate your Frequencies folder in 1 click!</div></div>'
            )
            + synth_js
        )
        self._send(200, "text/html; charset=utf-8", render_page("Meditation Frequencies", "freqs", body, total_m, len(streams)))

    def _handle_setup(self, qs, host_hdr: str):
        cats = scan_media()
        streams = parse_m3u()
        total_m = sum(len(v) for v in cats.values())
        lan_url = f"http://{detect_lan_ip()}:{PORT}"
        m3u_url = f"{lan_url}/playlist.m3u"
        msg = (qs.get("msg") or [""])[0]
        err = (qs.get("err") or [""])[0]
        notice = ""
        if msg:
            notice = f'<div class="notice"><div class="notice-in">✓ {html_lib.escape(msg)}</div></div>'
        elif err:
            notice = f'<div class="notice err"><div class="notice-in">! {html_lib.escape(err)}</div></div>'

        allowed_str = ", ".join(sorted(ALLOWED_FOLDERS))
        checked = "checked" if INCLUDE_OPEN_DIRECTORY else ""

        del_rows = []
        csrf_val = html_lib.escape(CSRF_TOKEN, quote=True)
        csrf_inp = f'<input type="hidden" name="csrf" value="{csrf_val}">'
        for idx, item in enumerate(CUSTOM_LINKS):
            if not isinstance(item, dict):
                continue
            nm = html_lib.escape(str(item.get("name", "Link")))
            ur = html_lib.escape(str(item.get("url", "")))
            del_rows.append(
                f'<form method="post" action="/setup/bookmark_del" style="display:flex;align-items:center;gap:8px;margin-top:8px">'
                f'{csrf_inp}<input type="hidden" name="idx" value="{idx}">'
                f'<span style="flex:1;font-size:13px;color:#fde68a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"><b>{nm}</b> · {ur}</span>'
                f'<button type="submit" class="tile" style="width:auto;--acc:#ef4444"><span class="t-in" style="padding:6px 10px"><span class="t-lbl">Remove</span></span></button>'
                f"</form>"
            )
        bookmarks_list = "".join(del_rows) or '<div style="font-size:12.5px;color:#94a3b8;margin-top:8px">No custom buttons added yet.</div>'

        body = (
            notice
            + '<h2>Easy as Pie — Zero-Code Setup &amp; Upload</h2>'
            + '<div class="grid-2">'
            # Card 1: Smart TV / Streaming Stick Auto-Populated Transmit Card + Scannable QR Code
            + '<div class="bp-card"><div class="bp-in">'
            + '<div class="bp-tag">STEP 1 · SMART TV, STREAMING STICK &amp; PHONE QR</div>'
            + '<div class="bp-name">Scan or Type Your Live Transmit Address</div>'
            + '<div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin:8px 0 10px">'
            + '<div style="background:#fff;padding:6px;border-radius:10px;border:2px solid var(--gold-bright);box-shadow:0 0 18px var(--gold-glow);flex-shrink:0">'
            + '<img src="/qr.svg?target=setup" alt="Scan to open POTATO Setup on phone" width="132" height="132" style="display:block">'
            + '</div>'
            + '<div style="flex:1;min-width:200px">'
            + f'<div class="big-url" style="margin:0 0 8px">{html_lib.escape(lan_url)}</div>'
            + f'<div style="font-family:ui-monospace,Consolas,monospace;font-size:13px;color:#a7f3d0;text-align:center;margin-bottom:6px">Auto-Discovery: <b>http://{MDNS_HOST}:{PORT}</b> '
            + f'({"mDNS LIVE" if _DISCOVERY_STATE["mdns"] else "IP READY"} · {"SSDP LIVE" if _DISCOVERY_STATE["ssdp"] else "LAN"})</div>'
            + '<div style="font-size:12.5px;color:#cbd5e1;text-align:center">Point your phone camera at the QR code to jump straight here &amp; upload!</div>'
            + '</div></div>'
            + '<div class="grid-2" style="margin-bottom:10px">'
            + tile_btn("Copy TV Address", "copyText(this.dataset.copy,this.dataset.copyLabel)", acc="#ffd166", extra_attrs=f'data-copy="{html_lib.escape(lan_url, quote=True)}" data-copy-label="TV Address"', badge="COPY", desc="Copy your live POTATO address")
            + tile_btn("Get TV Bro (by truefedex · GPLv3)", "openExternal(this.dataset.extUrl)", acc="#22c55e", extra_attrs='data-ext-url="https://github.com/truefedex/tv-bro/releases"', badge="TV APP", desc="By truefedex (Fedir Tsapana, GPLv3) · Open-source TV browser")
            + "</div>"
            + '<ol class="steps">'
            + '<li><b>Smart TV / Streaming Stick:</b> Open your built-in TV browser or open-source <b>TV Bro</b> (GPLv3).</li>'
            + f'<li>Type <b>{html_lib.escape(lan_url)}</b> (or <b>http://{MDNS_HOST}:{PORT}</b>), hit <b>Go</b>, and bookmark it.</li>'
            + '<li><b>Raw Potato App Icon:</b> On mobile or desktop browsers, tap <b>Add to Home Screen / Install</b> to drop a raw potato icon labeled <b>POTATO</b> onto your screen!</li>'
            + "</ol>"
            + "</div></div>"
            # Card 2: Upload Videos / Audio / M3U
            + '<div class="bp-card"><div class="bp-in">'
            + '<div class="bp-tag">STEP 2 · UPLOAD FROM PHONE OR PC</div>'
            + '<div class="bp-name">Drop Videos, Audio or M3U Playlists</div>'
            + '<div class="bp-desc">Send any <b>.mp4, .mkv, .mov, .webm, .mp3</b> or <b>.m3u/.m3u8</b> playlist straight from your phone or computer over Wi-Fi. No USB sticks or config files needed.</div>'
            + f'<form method="post" action="/setup/upload?csrf={urllib.parse.quote(CSRF_TOKEN, safe="")}" enctype="multipart/form-data">'
            + '<div class="fld"><label for="upfile">Choose Video, Audio, or M3U File</label>'
            + '<input id="upfile" type="file" name="file" required accept=".mp4,.mkv,.avi,.mov,.webm,.m4v,.ts,.mp3,.aac,.ogg,.flac,.wav,.m4a,.m3u,.m3u8"></div>'
            + tile_btn("Upload to POTATO", "", acc="#22c55e", badge="UPLOAD", desc="Saves video/audio to Library/Uploads or playlists to Playlists", btn_type="submit")
            + "</form>"
            + "</div></div>"
            # Card 3: Local Media Folder
            + '<div class="bp-card"><div class="bp-in">'
            + '<div class="bp-tag">STEP 3 · LOCAL MEDIA FOLDER</div>'
            + '<div class="bp-name">Point POTATO at Your Files</div>'
            + '<div class="bp-desc">Tell POTATO which folder holds your movies, documentaries, or shows. Private folders (pictures, photos, personal, camera) are blocked automatically.</div>'
            + '<form method="post" action="/setup/folder">'
            + csrf_inp
            + f'<div class="fld"><label for="mroot">Media Folder Path</label><input id="mroot" type="text" name="media_root" value="{html_lib.escape(MEDIA_ROOT, quote=True)}" placeholder="e.g. C:\\Videos or /home/user/Videos"></div>'
            + f'<div class="fld"><label for="afold">Allowed Subfolders (comma-separated, leave blank for all non-private)</label><input id="afold" type="text" name="allowed_folders" value="{html_lib.escape(allowed_str, quote=True)}" placeholder="e.g. Movies, Documentaries, Uploads"></div>'
            + f'<label class="chk"><input type="checkbox" name="include_open_directory" value="1" {checked}> Show curated Rabbit Holes, &amp; Open Media tab</label>'
            + tile_btn("Save & Rescan Now", "", acc="#3b82f6", badge="SAVE", desc="Saves config.json and rescans your media immediately", btn_type="submit")
            + "</form>"
            + "</div></div>"
            # Card 4: Kodi Official Integration
            + '<div class="bp-card"><div class="bp-in">'
            + '<div class="bp-tag">STEP 4 · KODI OFFICIAL INTEGRATION</div>'
            + '<div class="bp-name">Connect Kodi (100% Official Add-ons)</div>'
            + '<div class="bp-desc">Turn Kodi into a full living-room receiver for every local file and playlist stream on POTATO:</div>'
            + f'<div class="big-url" style="font-size:15px">{html_lib.escape(m3u_url)}</div>'
            + '<div class="grid-2" style="margin-bottom:10px">'
            + tile_btn("Copy Kodi M3U URL", "copyText(this.dataset.copy,this.dataset.copyLabel)", acc="#0284c7", extra_attrs=f'data-copy="{html_lib.escape(m3u_url, quote=True)}" data-copy-label="Kodi M3U URL"', badge="COPY", desc="Paste into Kodi PVR IPTV Simple Client")
            + tile_btn("Kodi Official Add-ons", "openExternal(this.dataset.extUrl)", acc="#38bdf8", extra_attrs='data-ext-url="https://kodi.tv/addons/"', badge="KODI", desc="Browse official free Kodi repository")
            + "</div>"
            + '<ol class="steps">'
            + '<li>Open <b>Kodi</b> → <b>Add-ons</b> → <b>Install from repository</b> → <b>Kodi Add-on repository</b> → <b>PVR clients</b> → install <b>PVR IPTV Simple Client</b>.</li>'
            + '<li>Open its settings → <b>M3U Play List URL</b> → paste the feed URL above.</li>'
            + '<li>Bonus official Kodi add-ons to add from the same official repo: <b>Internet Archive</b>, <b>NASA</b>, <b>SomaFM</b>, and <b>Jellyfin</b>.</li>'
            + "</ol>"
            + "</div></div>"
            + "</div>"
            # Full-width Custom Bookmark Manager
            + '<h2>Add Your Own Custom Home Buttons</h2>'
            + '<div class="bp-card"><div class="bp-in">'
            + '<form method="post" action="/setup/bookmark">'
            + csrf_inp
            + '<div class="grid-2">'
            + '<div class="fld"><label for="bname">Button Name</label><input id="bname" type="text" name="name" required placeholder="e.g. My Favorite Radio or Docs"></div>'
            + '<div class="fld"><label for="burl">Website URL (http:// or https://)</label><input id="burl" type="url" name="url" required placeholder="https://..."></div>'
            + '<div class="fld"><label for="bbadge">Short Badge (1 word)</label><input id="bbadge" type="text" name="badge" value="LINK" placeholder="DOCS / RADIO / SITE"></div>'
            + '<div class="fld"><label for="bdesc">What is behind this button? (1-line quick reference)</label><input id="bdesc" type="text" name="desc" placeholder="Short description shown on the button"></div>'
            + "</div>"
            + tile_btn("Add Button to Home", "", acc="#ffd166", badge="ADD", desc="Saves directly to config.json and appears on Home", btn_type="submit")
            + "</form>"
            + '<div style="margin-top:14px;border-top:1px solid rgba(255,209,102,0.3);padding-top:10px">'
            + '<div class="bp-tag">CURRENT CUSTOM BUTTONS</div>'
            + bookmarks_list
            + "</div></div></div>"
        )
        self._send(200, "text/html; charset=utf-8", render_page("Easy Setup", "setup", body, total_m, len(streams)))

    def _handle_library(self, qs):
        cats = scan_media(force=("refresh" in qs))
        streams = parse_m3u()
        total_m = sum(len(v) for v in cats.values())
        names = sorted(cats.keys())
        q_str = (qs.get("q") or [""])[0].strip()
        active = (qs.get("cat") or [names[0] if names else ""])[0]
        if names and active not in names:
            active = names[0]
        page_num = max(0, int((qs.get("p") or ["0"])[0])) if (qs.get("p") or ["0"])[0].isdigit() else 0
        per_page = 60

        folder_btns = [
            tile_btn(
                f"{g} ({len(cats[g]):,})",
                f"location.href='/library?cat={urllib.parse.quote(g, safe='')}'",
                acc="#ffd166" if (g == active and not q_str) else "#64748b",
                extra_cls="active" if (g == active and not q_str) else "",
                badge="DIR",
                desc=f"Open {g} ({len(cats[g]):,} items)",
                dest=f"/library?cat={g}",
            )
            for g in names
        ]
        items = [m for v in cats.values() for m in v if q_str.lower() in m["name"].lower()] if q_str else cats.get(active, [])
        chunk = items[page_num * per_page : (page_num + 1) * per_page]
        cards = [
            tile_btn(
                m["name"],
                f"location.href='/watch?path={urllib.parse.quote(m['path'], safe='')}&back={urllib.parse.quote(self.path, safe='')}'",
                acc="#3b82f6",
                badge=m["ext"].lstrip(".").upper(),
                desc="Local file · Plays in built-in POTATO player (HTTP 206 seek)",
                dest="Built-in Player",
            )
            for m in chunk
        ]
        pager = []
        if page_num > 0:
            pager.append(tile_btn("← Previous Page", f"location.href='/library?cat={urllib.parse.quote(active, safe='')}&p={page_num-1}'", acc="#ffd166", badge="PAGE", desc=f"Go to page {page_num}"))
        if (page_num + 1) * per_page < len(items):
            pager.append(tile_btn("Next Page →", f"location.href='/library?cat={urllib.parse.quote(active, safe='')}&p={page_num+1}'", acc="#ffd166", badge="PAGE", desc=f"Go to page {page_num+2}"))

        body = (
            f'<form method="get" action="/library" class="bar">'
            f'<input type="text" name="q" value="{html_lib.escape(q_str, quote=True)}" placeholder="Search local library...">'
            f'<button type="submit" class="tile" style="width:auto;--acc:#ffd166"><span class="t-in"><span class="t-lbl">Search</span></span></button></form>'
            f'<h2>Folders</h2>'
            f'<div class="grid">{"".join(folder_btns) or tile_btn("Upload or Set Folder in Easy Setup", "location.href=\'/setup\'", acc="#22c55e", badge="EASY", desc="No local files indexed yet — click to add or upload")}</div>'
            f'<h2>{html_lib.escape(q_str or active or "Library")} ({len(items):,} items · Page {page_num+1})</h2>'
            f'<div class="grid">{"".join(cards) or "<div class=status><div class=status-in>No matching files yet. Use Easy Setup to upload videos or point at your media folder.</div></div>"}</div>'
            + (f'<h2>Pages</h2><div class="grid">{"".join(pager)}</div>' if pager else "")
        )
        self._send(200, "text/html; charset=utf-8", render_page("Library", "media", body, total_m, len(streams)))

    def _handle_playlists(self, qs):
        cats = scan_media()
        streams = parse_m3u()
        total_m = sum(len(v) for v in cats.values())
        q_str = (qs.get("q") or [""])[0].strip().lower()
        filtered = [x for x in streams if not q_str or q_str in x["title"].lower() or q_str in x["group"].lower()]
        cards = [self._stream_tile(x, "/playlists") for x in filtered[:120]]
        body = (
            f'<form method="get" action="/playlists" class="bar">'
            f'<input type="text" name="q" value="{html_lib.escape(q_str, quote=True)}" placeholder="Filter {len(streams):,} playlist streams...">'
            f'<button type="submit" class="tile" style="width:auto;--acc:#ffd166"><span class="t-in"><span class="t-lbl">Filter</span></span></button></form>'
            f'<h2>M3U Streams ({len(filtered):,})</h2>'
            f'<div class="grid">{"".join(cards) or "<div class=status><div class=status-in>Upload any .m3u playlist on the Easy Setup tab to add channels here.</div></div>"}</div>'
        )
        self._send(200, "text/html; charset=utf-8", render_page("Playlists", "streams", body, total_m, len(streams)))

    def _handle_lite(self, path: str, qs: dict, host_hdr: str):
        cats = scan_media()
        streams = parse_m3u()
        total_m = sum(len(v) for v in cats.values())

        if path == "/lite/library":
            names = sorted(cats.keys())
            active = (qs.get("cat") or [names[0] if names else ""])[0]
            page = max(0, int((qs.get("p") or ["0"])[0])) if (qs.get("p") or ["0"])[0].isdigit() else 0
            per = 30
            items = cats.get(active, [])
            chunk = items[page * per : (page + 1) * per]
            cat_links = " ".join(f'<a href="/lite/library?cat={urllib.parse.quote(n)}">{html_lib.escape(n)} ({len(cats[n])})</a>' for n in names)
            rows = "".join(
                f'<li><a href="/media?path={urllib.parse.quote(m["path"], safe="")}">{html_lib.escape(m["name"])}</a></li>'
                for m in chunk
            ) or "<li>No local media files indexed yet.</li>"
            nav_p = []
            if page > 0:
                nav_p.append(f'<a href="/lite/library?cat={urllib.parse.quote(active)}&p={page-1}">&laquo; Prev</a>')
            if (page + 1) * per < len(items):
                nav_p.append(f'<a href="/lite/library?cat={urllib.parse.quote(active)}&p={page+1}">Next &raquo;</a>')
            body = f'<h2>Local Library ({total_m:,} files)</h2><div class="nav">{cat_links}</div><h3>{html_lib.escape(active or "Files")} (Page {page+1})</h3><ul>{rows}</ul><div class="nav">{" ".join(nav_p)}</div>'
            self._send(200, "text/html; charset=utf-8", render_lite_page("Library", host_hdr, body))
            return

        if path == "/lite/playlists":
            rows = "".join(
                f'<li><b>[{html_lib.escape(x["group"])}]</b> <a href="{html_lib.escape(x["url"], quote=True)}">{html_lib.escape(x["title"])}</a></li>'
                for x in streams[:60]
            ) or "<li>No M3U streams loaded.</li>"
            body = f'<h2>Streams ({len(streams):,})</h2><ul>{rows}</ul><p><a href="/playlist.m3u">Download Full M3U Playlist</a></p>'
            self._send(200, "text/html; charset=utf-8", render_lite_page("Playlists", host_hdr, body))
            return

        if path == "/lite/open":
            rows = "".join(
                f'<li><a href="{html_lib.escape(u, quote=True)}">{html_lib.escape(n)}</a> &mdash; {html_lib.escape(d)}</li>'
                for n, u, _, _, d in OPEN_ALL
            )
            body = f'<h2>Public Archives &amp; Tools ({len(OPEN_ALL)})</h2><ul>{rows}</ul>'
            self._send(200, "text/html; charset=utf-8", render_lite_page("Links", host_hdr, body))
            return

        if path == "/lite/status":
            body = (
                f'<h2>Server Status</h2><ul>'
                f'<li>Version: POTATO v{POTATO_VERSION} ({POTATO_LICENSE})</li>'
                f'<li>Local Files: {total_m:,}</li>'
                f'<li>M3U Streams: {len(streams):,}</li>'
                f'<li>Live Origin: http://{html_lib.escape(host_hdr)}/</li>'
                f'<li><a href="/health">Raw JSON Health</a></li>'
                f'<li><a href="/playlist.m3u">Export M3U Feed</a></li>'
                f'</ul>'
            )
            self._send(200, "text/html; charset=utf-8", render_lite_page("Status", host_hdr, body))
            return

        # Default /lite Home
        f_list = "".join(f'<li><a href="/lite/library?cat={urllib.parse.quote(g)}">{html_lib.escape(g)} ({len(cats[g])})</a></li>' for g in sorted(cats.keys()))
        s_list = "".join(f'<li><a href="{html_lib.escape(x["url"], quote=True)}">{html_lib.escape(x["title"])}</a></li>' for x in streams[:12])
        body = (
            f'<h2>Local Library ({total_m:,} Files)</h2><ul>{f_list or "<li>No local media folders configured yet.</li>"}</ul>'
            f'<h2>Instant Streams ({len(streams):,})</h2><ul>{s_list or "<li>No streams yet.</li>"}</ul>'
            f'<p><a href="/lite/open">Browse All {len(OPEN_ALL)} Public Links &amp; Archives</a></p>'
        )
        self._send(200, "text/html; charset=utf-8", render_lite_page("Home", host_hdr, body))

    def _handle_status(self, host_hdr: str):
        cats = scan_media()
        streams = parse_m3u()
        total_m = sum(len(v) for v in cats.values())
        lan_url = f"http://{detect_lan_ip()}:{PORT}"
        body = (
            f'<div class="status"><div class="status-in">POTATO v{POTATO_VERSION} · Author: {POTATO_AUTHOR} ({POTATO_LICENSE}) · '
            f'Transmit: {html_lib.escape(lan_url)} · Auto-Discovery: http://{MDNS_HOST}:{PORT} '
            f'(mDNS: {"ON" if _DISCOVERY_STATE["mdns"] else "OFF"} · SSDP: {"ON" if _DISCOVERY_STATE["ssdp"] else "OFF"}) · '
            f'Local Files: {total_m:,} · M3U Streams: {len(streams):,} · '
            f'ffmpeg: {"READY" if (FFMPEG and os.path.isfile(FFMPEG)) else "OPTIONAL"} · 0% VRAM Idle<br>'
            '<div class="grid-2" style="margin-bottom:16px">'
            '<div class="bp-card"><div class="bp-in" style="display:flex;align-items:center;gap:14px">'
            '<div style="background:#fff;padding:6px;border-radius:10px;border:2px solid var(--gold-bright);flex-shrink:0">'
            '<img src="/qr.svg?target=home" alt="QR Code for POTATO Home" width="118" height="118" style="display:block"></div>'
            f'<div><div class="bp-tag">SCAN TO OPEN HOME</div><div class="bp-name" style="font-size:16px">{html_lib.escape(lan_url)}</div>'
            '<div class="bp-desc">Point any phone or tablet camera on your Wi-Fi to open POTATO instantly.</div></div>'
            '</div></div>'
            '<div class="bp-card"><div class="bp-in" style="display:flex;align-items:center;gap:14px">'
            '<div style="background:#fff;padding:6px;border-radius:10px;border:2px solid var(--gold-bright);flex-shrink:0">'
            '<img src="/qr.svg?target=freqs" alt="QR Code for Audio Tone Generator" width="118" height="118" style="display:block"></div>'
            '<div><div class="bp-tag">SCAN FOR AUDIO TONES</div><div class="bp-name" style="font-size:16px">/freqs Oscilloscope</div>'
            '<div class="bp-desc">Jump straight into the live offline meditation &amp; brainwave tone generator on your phone.</div></div>'
            '</div></div>'
            '</div>'
            f'<div class="grid">'
            + tile_btn("Rescan Local Library", "location.href='/library?refresh=1'", acc="#3b82f6", badge="SCAN", desc="Re-index your configured local media folders", dest="/library?refresh=1")
            + tile_btn("Export LAN M3U", "location.href='/playlist.m3u'", acc="#22c55e", badge="M3U", desc="Full M3U feed for Kodi, VLC, or TV apps", dest="/playlist.m3u")
            + tile_btn("View JSON Health", "location.href='/health'", acc="#ffd166", badge="API", desc="Inspect live server status & telemetry", dest="/health")
            + "</div>"
        )
        self._send(200, "text/html; charset=utf-8", render_page("Status", "status", body, total_m, len(streams)))

    def _handle_export_m3u(self, host_hdr: str):
        lines = [
            "#EXTM3U",
            f"# POTATO LAN Feed · Created by {POTATO_AUTHOR} ({POTATO_LICENSE}) · {POTATO_TAG}",
        ]
        for cat, items in sorted(scan_media().items()):
            for m in items:
                lines.append(f'#EXTINF:-1 group-title="Local - {cat}",{m["name"]}')
                lines.append(f"http://{host_hdr}/media?path={urllib.parse.quote(m['path'], safe='')}")
        for x in parse_m3u():
            lines.append(f'#EXTINF:-1 group-title="{x["group"]}",{x["title"]}')
            lines.append(x["url"])
        self._send(200, "audio/x-mpegurl; charset=utf-8", ("\n".join(lines) + "\n").encode("utf-8"))

    def _handle_media(self, qs):
        fpath = (qs.get("path") or [""])[0]
        if not is_allowed_path(fpath):
            self._send(404, "text/plain", b"Not found or restricted")
            return
        real_fpath = os.path.realpath(fpath)
        size = os.path.getsize(real_fpath)
        ctype = mimetypes.guess_type(real_fpath)[0] or "video/mp4"
        start, end, status = 0, max(0, size - 1), 200
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            try:
                spec = rng.replace("bytes=", "", 1).split(",", 1)[0].strip()
                parts = spec.split("-", 1)
                if parts[0]:
                    start = int(parts[0])
                    end = int(parts[1]) if (len(parts) > 1 and parts[1]) else size - 1
                elif len(parts) > 1 and parts[1]:
                    suffix = int(parts[1])
                    start = max(0, size - suffix)
                    end = size - 1
                else:
                    raise ValueError("Empty range")
                if size == 0 or start < 0 or start >= size or end < start:
                    self._send(416, "text/plain", b"Range Not Satisfiable", {"Content-Range": f"bytes */{size}"})
                    return
                end = min(end, size - 1)
                status = 206
            except ValueError:
                self._send(416, "text/plain", b"Invalid Range", {"Content-Range": f"bytes */{size}"})
                return
        length = 0 if size == 0 else max(0, end - start + 1)
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self._add_security_headers()
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        try:
            with open(real_fpath, "rb") as f:
                f.seek(start)
                rem = length
                while rem > 0:
                    buf = f.read(min(131072, rem))
                    if not buf:
                        break
                    self.wfile.write(buf)
                    rem -= len(buf)
        except Exception:
            pass

    def _pipe_ffmpeg(self, cmd):
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Cache-Control", "no-store")
        self._add_security_headers()
        self.end_headers()
        proc = None
        try:
            kw = {"stdout": subprocess.PIPE, "stderr": subprocess.DEVNULL}
            if IS_WIN:
                kw["creationflags"] = CREATE_NO_WINDOW
            proc = subprocess.Popen(cmd, **kw)
            while True:
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except Exception:
            pass
        finally:
            if proc is not None:
                try:
                    proc.kill()
                except Exception:
                    pass

    def _handle_ffmpeg_file(self, qs):
        fpath = (qs.get("path") or [""])[0]
        if not is_allowed_path(fpath):
            self._send(404, "text/plain", b"Not found or restricted")
            return
        if not FFMPEG or not os.path.isfile(FFMPEG):
            self._handle_media(qs)
            return
        real_fpath = os.path.realpath(fpath)
        self._pipe_ffmpeg([
            FFMPEG, "-hide_banner", "-loglevel", "error", "-i", real_fpath,
            "-c:v", "libx264", "-preset", "ultrafast", "-threads", "2", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ac", "2",
            "-movflags", "frag_keyframe+empty_moov+default_base_moof", "-f", "mp4", "pipe:1",
        ])

    def _handle_live_mp4(self, qs):
        target = (qs.get("url") or [""])[0]
        if not is_safe_public_url(target) or not FFMPEG or not os.path.isfile(FFMPEG):
            self._send(403, "text/plain", b"Blocked or unavailable stream")
            return
        self._pipe_ffmpeg([
            FFMPEG, "-hide_banner", "-loglevel", "error",
            "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5", "-i", target,
            "-c:v", "libx264", "-preset", "ultrafast", "-threads", "2", "-crf", "24", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ac", "2",
            "-movflags", "frag_keyframe+empty_moov+default_base_moof", "-f", "mp4", "pipe:1",
        ])

    def _handle_proxy(self, qs, host_hdr: str):
        target = (qs.get("url") or [""])[0]
        if not is_safe_public_url(target):
            self._send(403, "text/plain", b"Blocked non-public or invalid URL")
            return
        try:
            hdrs = {"User-Agent": f"POTATO/{POTATO_VERSION}"}
            if self.headers.get("Range"):
                hdrs["Range"] = self.headers["Range"]
            req = urllib.request.Request(target, headers=hdrs)
            ctx = ssl.create_default_context()
            opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=ctx),
                _SafeRedirectHandler(),
            )
            with opener.open(req, timeout=15) as resp:
                final_url = resp.geturl()
                if not is_safe_public_url(final_url):
                    self._send(403, "text/plain", b"Blocked redirect target")
                    return
                ctype = resp.headers.get("Content-Type", "")
                if ".m3u8" in final_url.lower() or "mpegurl" in ctype.lower():
                    txt = resp.read(2 * 1024 * 1024).decode("utf-8", errors="ignore")
                    out = [
                        ln if (not ln.strip() or ln.strip().startswith("#"))
                        else f"http://{host_hdr}/proxy?url={urllib.parse.quote(urllib.parse.urljoin(final_url, ln.strip()), safe='')}"
                        for ln in txt.splitlines()
                    ]
                    self._send(200, "application/vnd.apple.mpegurl; charset=utf-8", ("\n".join(out) + "\n").encode("utf-8"))
                    return
                self.send_response(resp.status)
                self.send_header("Content-Type", ctype or "application/octet-stream")
                if resp.headers.get("Content-Length"):
                    self.send_header("Content-Length", resp.headers["Content-Length"])
                if resp.headers.get("Content-Range"):
                    self.send_header("Content-Range", resp.headers["Content-Range"])
                if resp.headers.get("Accept-Ranges"):
                    self.send_header("Accept-Ranges", resp.headers["Accept-Ranges"])
                self.send_header("Cache-Control", "no-store")
                self._add_security_headers()
                self.end_headers()
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except Exception as e:
            try:
                self._send(502, "text/plain", f"Proxy error: {e}".encode("utf-8"))
            except Exception:
                pass

    def _handle_watch(self, qs, host_hdr: str):
        fpath = (qs.get("path") or [""])[0]
        live_u = (qs.get("live") or [""])[0]
        title = (qs.get("title") or [""])[0]
        back = (qs.get("back") or ["/"])[0]
        if not back.startswith("/") or back.startswith("//") or "\\" in back:
            back = "/"
        fallback_mp4 = ""
        is_audio = False

        if fpath and is_allowed_path(fpath):
            title = title or os.path.basename(fpath)
            ext = os.path.splitext(fpath)[1].lower()
            is_audio = ext in AUDIO_EXTS
            play_src = (
                f"http://{host_hdr}/media?path={urllib.parse.quote(fpath, safe='')}"
                if ext in BROWSER_NATIVE_EXTS
                else f"http://{host_hdr}/stream?path={urllib.parse.quote(fpath, safe='')}"
            )
        elif live_u and live_u.startswith(("http://", "https://")):
            title = title or "Live Stream"
            lo = live_u.lower()
            is_audio = any(x in lo for x in (".mp3", "-mp3", ".aac", ".ogg", ".opus", "somafm.com/"))
            if ".m3u8" in lo:
                play_src = f"http://{host_hdr}/proxy?url={urllib.parse.quote(live_u, safe='')}"
                fallback_mp4 = f"http://{host_hdr}/live_mp4?url={urllib.parse.quote(live_u, safe='')}"
            else:
                play_src = live_u
                if not is_audio and FFMPEG and os.path.isfile(FFMPEG):
                    fallback_mp4 = f"http://{host_hdr}/live_mp4?url={urllib.parse.quote(live_u, safe='')}"
        else:
            self._send(404, "text/plain", b"Nothing to play")
            return

        fb_js = json.dumps(fallback_mp4)
        back_js = json.dumps(back)
        relay_btn = (
            tile_btn("⚡ MP4 Relay", "useRelay()", acc="#a855f7")
            if fallback_mp4
            else ""
        )
        media_tag = (
            f'<div class="audio-stage"><img src="/assets/potato_icon.png" alt="POTATO Audio">'
            f'<div class="audio-title">{html_lib.escape(title)}</div>'
            f'<audio id="v" tabindex="-1" controls autoplay src="{html_lib.escape(play_src, quote=True)}"></audio></div>'
            if is_audio
            else f'<video id="v" tabindex="-1" controls autoplay playsinline src="{html_lib.escape(play_src, quote=True)}"></video>'
        )

        page = f"""<!doctype html><html lang="en"><!-- POTATO Open-Source LAN Media Hub (GPLv3) --><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html_lib.escape(title)} · POTATO</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/png" href="/assets/potato_icon.png">
<style>
*{{box-sizing:border-box}}
body{{background:#04060a;color:#fff;font:15px system-ui,sans-serif;margin:0;display:flex;flex-direction:column;height:100vh;overflow:hidden}}
.p-bar{{
  padding:6px;
  background-image:url("{CLEAN_BORDER_SVG}");
  background-repeat:repeat;
  border-bottom:2px solid #fff2a6;
  box-shadow:0 0 22px rgba(255,209,102,0.45);
}}
.p-bar-in{{
  background:rgba(7,10,16,0.95);
  border:1px solid rgba(255,209,102,0.55);
  border-radius:10px;
  padding:8px 10px;
  display:flex;
  gap:8px;
  align-items:center;
  flex-wrap:wrap;
}}
.tile{{
  display:inline-block;
  width:auto;
  padding:4px;
  border:2px solid rgba(255,222,115,0.8);
  border-radius:11px;
  background-image:url("{CLEAN_BORDER_SVG}");
  background-repeat:repeat;
  cursor:pointer;
  color:#fff;
  box-shadow:0 0 10px rgba(255,209,102,0.28);
}}
.tile > .t-in{{
  display:inline-flex;
  align-items:center;
  padding:8px 12px;
  border-radius:7px;
  background:rgba(12,17,28,0.94);
  border:1px solid rgba(255,209,102,0.5);
  border-left:4px solid var(--acc,#ffd166);
  font-size:13.5px;
  font-weight:700;
  color:#fff;
  white-space:nowrap;
}}
.t-top{{display:inline-flex;align-items:center;gap:6px}}
.t-lbl{{white-space:nowrap}}
.t-tag,.t-desc{{display:none}}
.tile.tv-sel,.tile:focus{{
  outline:none!important;
  border-color:#fff!important;
  background-image:url("{CLEAN_FOCUS_SVG}")!important;
  box-shadow:0 0 0 3px #ffd166,0 0 24px rgba(255,224,102,0.98)!important;
}}
.tile.tv-sel > .t-in,.tile:focus > .t-in{{
  background:rgba(48,36,10,0.96)!important;
  border-color:#fff6c2!important;
  color:#fffbeb!important;
}}
.p-title{{
  font-family:'Palatino Linotype','Book Antiqua',Georgia,serif;
  font-variant:small-caps;
  color:#fff2a6;
  font-size:15px;
  font-weight:800;
  margin-left:auto;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
  max-width:34vw;
  text-shadow:0 0 10px rgba(255,209,102,0.5);
}}
.stage{{position:relative;flex:1;display:flex;align-items:center;justify-content:center;background:#000 #0d1117 center/cover no-repeat;min-height:0}}
video{{width:100%;height:100%;background:#000;object-fit:contain}}
.audio-stage{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;padding:24px;width:100%;height:100%;background:rgba(5,7,12,0.72)}}
.audio-stage img{{width:160px;height:160px;border-radius:18px;border:3px solid #fff2a6;box-shadow:0 0 36px rgba(255,209,102,0.75)}}
.audio-title{{font-family:'Palatino Linotype','Book Antiqua',Georgia,serif;font-variant:small-caps;font-size:24px;color:#fff2a6;text-align:center;text-shadow:0 0 16px rgba(255,209,102,0.6),0 2px 10px #000}}
audio{{width:min(540px,90%)}}
#osd{{position:absolute;bottom:22px;left:50%;transform:translateX(-50%);background:rgba(8,11,18,0.92);border:2px solid #ffd166;border-radius:10px;padding:8px 18px;font-weight:700;color:#fff2a6;box-shadow:0 0 22px rgba(255,209,102,0.65);opacity:0;transition:opacity .2s;pointer-events:none;z-index:20}}
#osd.show{{opacity:1}}
</style></head><body>
<div class="p-bar">
  <div class="p-bar-in">
    {tile_btn("← Back", "goBack()", acc="#f97316")}
    {tile_btn("⏯ Play / Pause", "togglePlay()", acc="#22c55e", extra_attrs='data-default-focus="1"')}
    {tile_btn("⏪ -15s", "seekBy(-15)", acc="#3b82f6")}
    {tile_btn("⏩ +15s", "seekBy(15)", acc="#3b82f6")}
    {tile_btn("🔊 Mute", "toggleMute()", acc="#eab308")}
    {tile_btn("⛶ Fullscreen", "toggleFull()", acc="#14b8a6")}
    {relay_btn}
    <span class="p-title">{html_lib.escape(title)}</span>
  </div>
</div>
<div class="stage">
  {media_tag}
  <div id="osd"></div>
</div>
<script>
var v = document.getElementById('v'), fb = {fb_js}, backUrl = {back_js}, sw = false, osdT = null;
function showOsd(msg){{
  var o = document.getElementById('osd');
  o.textContent = msg;
  o.classList.add('show');
  if(osdT) clearTimeout(osdT);
  osdT = setTimeout(function(){{ o.classList.remove('show'); }}, 1600);
}}
function goBack(){{
  if(document.fullscreenElement){{ document.exitFullscreen().catch(function(){{}}); return; }}
  location.href = backUrl;
}}
function togglePlay(){{
  if(v.paused){{ v.play().then(function(){{ showOsd('▶ Playing'); }}).catch(function(){{}}); }}
  else{{ v.pause(); showOsd('⏸ Paused'); }}
}}
function seekBy(sec){{
  try{{
    if(isFinite(v.currentTime)){{
      v.currentTime = Math.max(0, v.currentTime + sec);
      showOsd((sec > 0 ? '⏩ +' : '⏪ ') + sec + 's');
    }}
  }}catch(e){{}}
}}
function toggleMute(){{
  v.muted = !v.muted;
  showOsd(v.muted ? '🔇 Muted' : '🔊 Unmuted');
}}
function toggleFull(){{
  var st = document.querySelector('.stage');
  if(!document.fullscreenElement){{
    (st.requestFullscreen || v.requestFullscreen || function(){{}}).call(st);
    showOsd('⛶ Fullscreen');
  }} else {{
    document.exitFullscreen().catch(function(){{}});
  }}
}}
function useRelay(){{
  if(!fb || sw) return;
  sw = true;
  v.src = fb;
  v.load();
  v.play().catch(function(){{}});
  showOsd('⚡ MP4 Relay Active');
}}
if(fb && v.src.toLowerCase().indexOf('.m3u8') !== -1 && !v.canPlayType('application/vnd.apple.mpegurl')) useRelay();
v.addEventListener('error', function(){{ if(fb && !sw) useRelay(); }});
window.__potatoBack = goBack;
window.__potatoMediaKey = function(e){{
  var k = e.key || '', kc = e.keyCode || e.which || 0;
  if(k === ' ' || k === 'MediaPlayPause' || kc === 179 || kc === 85){{ e.preventDefault(); togglePlay(); return true; }}
  if(k === 'MediaRewind' || kc === 89 || kc === 227){{ e.preventDefault(); seekBy(-15); return true; }}
  if(k === 'MediaFastForward' || kc === 90 || kc === 228){{ e.preventDefault(); seekBy(15); return true; }}
  if(k === 'm' || k === 'M' || k === 'AudioVolumeMute'){{ e.preventDefault(); toggleMute(); return true; }}
  if(k === 'f' || k === 'F'){{ e.preventDefault(); toggleFull(); return true; }}
  return false;
}};
</script>{GRID_NAV_JS}</body></html>"""
        self._send(200, "text/html; charset=utf-8", page.encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="POTATO — Zero-dependency LAN Media Hub & TV-Remote Transmitter by Guffalo (GPLv3)")
    global HOST, PORT
    parser.add_argument("--open", action="store_true", help="Automatically open POTATO in your default web browser on start")
    parser.add_argument("--no-discovery", action="store_true", help="Disable LAN-only mDNS (potato.local) and SSDP auto-discovery")
    parser.add_argument("--lite", action="store_true", help="Low-RAM mode for Raspberry Pi Zero, old phones & 256MB devices (disables mDNS/SSDP, caps sockets)")
    parser.add_argument("--host", default=None, help="Bind address override (e.g. 127.0.0.1 or 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Listen port override (default 8789)")
    args = parser.parse_args()

    if args.host:
        HOST = args.host
    if args.port:
        PORT = args.port
    if args.lite:
        ThreadedTCPServer.request_queue_size = 16

    lan_ip = detect_lan_ip()
    if ENABLE_AUTO_DISCOVERY and not args.no_discovery and not args.lite:
        start_mdns_responder(PORT)
        start_ssdp_responder(PORT)
    print(f"[POTATO v{POTATO_VERSION}] Created by {POTATO_AUTHOR} ({POTATO_LICENSE}) · {POTATO_TAG}", flush=True)
    print(f"[POTATO] Open on this device : http://127.0.0.1:{PORT}/", flush=True)
    print(f"[POTATO] Open on Smart TV / LAN Device: http://{lan_ip}:{PORT}/  (or http://{MDNS_HOST}:{PORT}/)", flush=True)
    threading.Thread(target=lambda: scan_media(force=True), daemon=True).start()

    if args.open or os.environ.get("POTATO_AUTO_OPEN") == "1":
        def _open_browser():
            time.sleep(0.6)
            try:
                webbrowser.open(f"http://127.0.0.1:{PORT}/")
            except Exception:
                pass
        threading.Thread(target=_open_browser, daemon=True).start()

    with ThreadedTCPServer((HOST, PORT), PotatoHandler) as srv:
        srv.serve_forever()


if __name__ == "__main__":
    main()
