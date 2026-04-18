# websocket.py
import websockets
import json
import time
import music


PLAYER_TIMEOUT = 3.0  # seconds without any message before releasing the lock
PAUSE_GRACE = 3.0  # seconds of continuous pause before releasing
# generous to survive Spotify buffering/crossfade gaps

# Per-tab pause tracking: { tab_id: timestamp_when_pause_started }
_pause_since: dict[str, float] = {}


async def handler(ws):
    print("✅ Extension connectée")
    async for raw in ws:
        data = json.loads(raw)
        now = time.time()

        tab_id = data.get("tab_id")
        is_playing = data.get("isPlaying", False)
        player = data.get("player", "")
        title = data.get("title", "")
        artist = data.get("artist", "")

        if not tab_id:
            continue

        label = (
            "Spotify"
            if "spotify" in player.lower()
            else "Deezer" if "deezer" in player.lower() else "YT Music"
        )

        # ⏱️ Hard timeout — tab stopped sending altogether
        if music.active_player is not None:
            if now - music.active_player_ts > PLAYER_TIMEOUT:
                print(f"⚠️ [{label}] timed out — releasing")
                music.active_player = None
                _pause_since.clear()

        # 🔓 No active player → take the first tab that is actually playing
        if music.active_player is None:
            if is_playing:
                print(f"▶️  [{label}] {artist} - {title}")
                music.active_player = tab_id
                music.active_player_ts = now
                music.msg = data
                _pause_since.pop(tab_id, None)
            continue

        # 🔐 Active player: only process messages from the locked tab
        if tab_id == music.active_player:
            music.active_player_ts = now
            music.msg = data

            if is_playing:
                # Back to playing — cancel any pending release
                _pause_since.pop(tab_id, None)
            else:
                if tab_id not in _pause_since:
                    # First paused frame — start the grace timer
                    _pause_since[tab_id] = now
                elif now - _pause_since[tab_id] >= PAUSE_GRACE:
                    # Sustained pause — this is a real stop
                    print(f"⏹️  [{label}] {artist} - {title} stopped — releasing")
                    music.active_player = None
                    _pause_since.pop(tab_id, None)


async def start_ws_server():
    server = await websockets.serve(handler, "127.0.0.1", 8766)
    print("🚀 WebSocket server started on ws://127.0.0.1:8766")
    return server
