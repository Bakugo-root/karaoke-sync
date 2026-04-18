import asyncio
import requests
import urllib.parse
import re

# https://lrclib.net/api/search?track_name=x&artist_name=y
msg = {}
current_track = None
active_player = None
active_player_ts = 0.0


# ========================
# ARTIST CLEANING
# ========================


def clean_artist(name: str) -> str:
    """Remove featuring, &, etc. so lrclib finds the main artist."""
    blacklist = ["&", "et", "feat", "featuring", "ft", "avec"]
    cleaned = name.lower()
    for word in blacklist:
        cleaned = re.sub(rf"\b{re.escape(word)}\b", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


# ========================
# TRACK DETECTION
# ========================


async def receive():
    """Passive loop — websocket.py writes music.msg directly."""
    while True:
        await asyncio.sleep(0.005)


def get_new_track() -> dict | None:
    """Returns msg only when the track has changed, else None."""
    global current_track

    if not msg:
        return None

    track_id = (
        msg.get("title"),
        msg.get("artist"),
        msg.get("album"),
        msg.get("duration"),
    )

    if track_id != current_track:
        current_track = track_id
        return msg

    return None


# ========================
# LYRICS FETCHING
# ========================


def select_best_track(api_results: list, local_duration_sec: float) -> dict | None:
    """
    Pick the result whose duration is closest to the local one.
    Prefers equal-or-above, falls back to closest below.
    """
    above, below = [], []

    for track in api_results:
        api_dur = float(track.get("duration", 0))
        (above if api_dur >= local_duration_sec else below).append(track)

    if above:
        return min(above, key=lambda t: float(t["duration"]))
    if below:
        return max(below, key=lambda t: float(t["duration"]))
    return None


def get_best_lyrics(track: dict) -> str:
    """Prefer synced lyrics, fall back to plain."""
    return track.get("syncedLyrics") or track.get("plainLyrics", "")


def _fetch_lyrics_sync(artist: str, title: str, local_duration_mmss: str) -> str:
    """
    Blocking HTTP call — always run via asyncio.to_thread(), never directly.
    """
    params = {"track_name": title, "artist_name": artist}
    url = f"https://lrclib.net/api/search?{urllib.parse.urlencode(params)}"

    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException:
        return ""

    if response.status_code != 200:
        return ""

    api_results = response.json()
    if not api_results:
        return ""

    best = select_best_track(api_results, float(local_duration_mmss))
    return get_best_lyrics(best) if best else ""


async def get_lyrics(
    artist: str = "", title: str = "", album: str = "", local_duration_mmss: str = "0"
) -> str:
    """
    Async wrapper — runs the blocking HTTP fetch in a thread so the
    event loop (websocket handler, karaoke task) is never frozen.
    """
    return await asyncio.to_thread(
        _fetch_lyrics_sync, artist, title, local_duration_mmss
    )
