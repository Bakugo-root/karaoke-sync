# 🎤 Karaoke Sync

Real-time lyrics display system — a Chrome extension captures playback data from YouTube Music or Spotify, sends it via WebSocket to a Python backend, which fetches and syncs lyrics from the lrclib API in real time.

Built as a personal project to explore real-time communication, async Python, and browser extension development.

---

## Architecture

```
Chrome Extension (content.js)
        ↓  WebSocket (ws://127.0.0.1:8766)
Python Backend (websocket.py)
        ↓  shared state
Lyrics Engine (karaoke2.0.py)
        ↓  HTTP REST
lrclib.net API
```

---

## Features

- Detects the currently playing track automatically from YouTube Music or Spotify Web
- Fetches synced lyrics (LRC format) from [lrclib.net](https://lrclib.net)
- Displays lyrics in the terminal with a typewriter effect, synced to the song position
- Handles multi-tab conflicts — first active player gets the lock, releases it if paused or no lyrics found
- Configurable offset (ms) to adjust sync ahead or behind
- Fully async Python backend — HTTP fetches run in a thread so the event loop never blocks

---

## Tech Stack

| Layer | Technology |
|---|---|
| Browser Extension | JavaScript, Manifest V3, WebSocket |
| Backend | Python 3.11+, asyncio |
| Real-time comm | WebSocket (`websockets` library) |
| Lyrics API | [lrclib.net](https://lrclib.net) REST API |

---

## Installation

### 1. Python backend

```bash
pip install -r requirements.txt
```

### 2. Chrome Extension

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** → select the `extention/` folder

### 3. Run

```bash
python src/karaoke.py
```

Then open YouTube Music or Spotify Web in Chrome and play a song.

---

## Configuration

In `src/karaoke2.0.py`, at the top of the file:

```python
ANTICIPATION_MS = 150   # built-in anticipation, adjust if lyrics feel late
OFFSET_MS       = 0     # positive = lyrics appear earlier, negative = later
```

---

## Project Structure

```
karaoke-sync/
├── extention/
│   ├── manifest.json      # Chrome extension config
│   ├── background.js      # WebSocket client (service worker)
│   └── content.js         # Captures playback data from the page
├── src/
│   ├── karaoke.py      # Main loop — track detection, lyrics display
│   ├── music.py           # Shared state, lyrics fetching (lrclib API)
│   └── websocket.py       # WebSocket server — player lock management
└── requirements.txt
```

---

## Author

**Yasser** — Engineering student, seeking an apprenticeship starting September 2026 ideally based in Toulouse, in electronics, automation, robotics or software/embedded systems.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Yasser-blue)](https://www.linkedin.com/in/yasser-mha)
