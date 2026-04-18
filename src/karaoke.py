import time
import re
import asyncio
import music
import sys
from websocket import start_ws_server


# ========================
# CONFIG — tweak these
# ========================
ANTICIPATION_MS = 150  # ms d'anticipation built-in (ne pas toucher sauf si nécessaire)
OFFSET_MS = 200  # ⬅️ TON OFFSET : positif = paroles en avance, négatif = en retard
# exemple : OFFSET_MS = 500  → paroles 0.5s en avance
#           OFFSET_MS = -300 → paroles 0.3s en retard


# ========================
# GLOBAL STATE
# ========================
shutdown_event = asyncio.Event()
karaoke_stop_event = asyncio.Event()
karaoke_task = None


def parse_lrc(syncedLyrics: str):
    times = []
    texts = []

    for line in syncedLyrics.split("\n"):
        match = re.match(r"\[(\d+):(\d+\.\d+)\](.*)", line)
        if match:
            m = int(match.group(1))
            s = float(match.group(2))
            times.append(m * 60 + s)
            texts.append(match.group(3).strip())

    return times, texts


# ========================
# KARAOKE CORE
# ========================


def run_karaoke_synced(times, texts, stop_event, shutdown_event):
    last_index = -1
    displayed_chars = 0.0
    last_displayed_int = 0
    max_line_length = 150

    # Combine anticipation + user offset into one shift applied to the song position
    # current_time_shifted = current_time + total_shift
    # so lyrics appear (total_shift) seconds earlier than their timestamp
    total_shift = (ANTICIPATION_MS + OFFSET_MS) / 1000.0

    print("\033[2J\033[H", end="", flush=True)

    while not stop_event.is_set() and not shutdown_event.is_set():
        if not isinstance(music.msg, dict):
            time.sleep(0.001)
            continue
        pos = music.msg.get("position")
        if pos is None:
            time.sleep(0.001)
            continue

        # Shift the clock forward so lyrics are triggered earlier
        current_time = float(pos) + total_shift

        # Find active line index
        index = -1
        for i, t in enumerate(times):
            if t <= current_time:
                index = i
            else:
                break

        if index < 0 or index >= len(texts):
            time.sleep(0.001)
            continue

        text = texts[index]
        if len(text) == 0:
            time.sleep(0.001)
            continue

        # Line changed
        if index != last_index:
            if 0 <= last_index < len(texts):
                print(f"\r{texts[last_index].ljust(max_line_length)}", flush=True)
            last_index = index
            displayed_chars = 0.0
            last_displayed_int = 0

        # Time bounds for writing speed
        line_start = times[index]
        line_end = times[index + 1] if index + 1 < len(times) else times[index] + 5.0
        line_duration = max(0.5, line_end - line_start)

        chars_per_second = len(text) / line_duration
        frame_time = 0.01  # 100 FPS
        chars_to_add = chars_per_second * frame_time

        displayed_chars = min(displayed_chars + chars_to_add, float(len(text)))
        current_displayed_int = int(displayed_chars)

        if current_displayed_int != last_displayed_int:
            print(f"\r{text[:current_displayed_int]}", end="", flush=True)
            last_displayed_int = current_displayed_int

        time.sleep(frame_time)

    # Finalize last line on stop
    if 0 <= last_index < len(texts):
        print(f"\r{texts[last_index].ljust(max_line_length)}", flush=True)


# ========================
# STOP HELPER
# ========================


async def stop_karaoke():
    global karaoke_task

    if karaoke_task and not karaoke_task.done():
        karaoke_stop_event.set()
        try:
            await asyncio.wait_for(asyncio.shield(karaoke_task), timeout=0.5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        karaoke_task = None

    karaoke_stop_event.clear()
    print("\033[2J\033[H", end="", flush=True)


# ========================
# MAIN LOOP
# ========================


async def main():
    global karaoke_task

    print("✅ Karaoke script started")
    print(f"⚙️  Offset: {OFFSET_MS:+d}ms  |  Anticipation: {ANTICIPATION_MS}ms")

    asyncio.create_task(music.receive())

    while not isinstance(music.msg, dict) or not music.msg:
        print("⏳ Waiting for websocket data...")
        await asyncio.sleep(0.5)

    print("✅ Websocket connecté")

    try:
        while True:
            new_track = music.get_new_track()

            if new_track:
                print(
                    f"\n🎵 {new_track['artist']} - {new_track['title']} ({new_track['album']})"
                )

                await stop_karaoke()

                lyrics = await music.get_lyrics(
                    artist=music.clean_artist(new_track["artist"]),
                    title=music.clean_artist(new_track["title"]),
                    local_duration_mmss=new_track["duration"],
                )

                if lyrics:
                    print("🎤 Paroles trouvées")
                    times, texts = parse_lrc(lyrics)
                    karaoke_task = asyncio.create_task(
                        asyncio.to_thread(
                            run_karaoke_synced,
                            times,
                            texts,
                            karaoke_stop_event,
                            shutdown_event,
                        )
                    )
                else:
                    print("❌ Aucune parole trouvée — lock released, trying next tab")
                    music.active_player = None

            await asyncio.sleep(0.3)
    except asyncio.CancelledError:
        pass
    finally:
        await stop_karaoke()
        print("✅ Karaoke script stopped")


# ========================
# ENTRY POINT
# ========================
async def start():
    await asyncio.gather(
        start_ws_server(),
        main(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        print("🛑 Arrêt du programme")
        sys.exit(0)
