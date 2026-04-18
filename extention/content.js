// Generate a stable unique ID for this tab instance
const TAB_ID = Math.random().toString(36).slice(2);

// ========================
// HELPERS
// ========================

function getPlayer() {
    if (location.host.includes("spotify")) return "Spotify Web";
    if (location.host.includes("deezer")) return "Deezer";
    return "YouTube Music";
}

function buildPayload(mediaEl) {
    const metadata = navigator.mediaSession?.metadata;
    if (!metadata?.title) return null;

    const playbackState = navigator.mediaSession.playbackState;
    let isPlaying;
    if (playbackState === "playing") isPlaying = true;
    else if (playbackState === "paused") isPlaying = false;
    else isPlaying = mediaEl ? (!mediaEl.paused && !mediaEl.ended) : false;

    const positionState = navigator.mediaSession.positionState;
    let position = 0, duration = 0;
    if (positionState?.duration) {
        duration = positionState.duration;
        position = positionState.position ?? (mediaEl?.currentTime || 0);
    } else if (mediaEl) {
        duration = mediaEl.duration || 0;
        position = mediaEl.currentTime || 0;
    }

    return {
        tab_id: TAB_ID,
        player: getPlayer(),
        title: metadata.title ?? "",
        artist: metadata.artist ?? "",
        album: metadata.album ?? "",
        duration,
        position,
        position_percent: duration > 0 ? (position / duration) * 100 : 0,
        cover_url: metadata.artwork?.length
            ? metadata.artwork[metadata.artwork.length - 1].src
            : "",
        isPlaying,
        ts: Date.now() / 1000,
    };
}

function send(payload) {
    if (payload) chrome.runtime.sendMessage(payload);
}

// ========================
// EVENT-DRIVEN UPDATES
// Fires only when something actually changes (play, pause, track change)
// ========================

function attachMediaListeners(mediaEl) {
    const events = ["play", "pause", "ended", "seeked"];
    for (const ev of events) {
        mediaEl.addEventListener(ev, () => send(buildPayload(mediaEl)));
    }
}

// Watch for the media element appearing in the DOM
const observer = new MutationObserver(() => {
    const mediaEl = document.querySelector("audio, video");
    if (mediaEl && !mediaEl._karaokeListened) {
        mediaEl._karaokeListened = true;
        attachMediaListeners(mediaEl);
    }
});
observer.observe(document.body, { childList: true, subtree: true });

// Also attach immediately if already present
const existing = document.querySelector("audio, video");
if (existing && !existing._karaokeListened) {
    existing._karaokeListened = true;
    attachMediaListeners(existing);
}

// mediaSession metadata changes (track change) — no standard event,
// so we poll ONLY the metadata + playback state, not position, at 1s interval
// This is 50x fewer messages than before
let lastTrackId = "";
setInterval(() => {
    const metadata = navigator.mediaSession?.metadata;
    if (!metadata?.title) return;

    const trackId = `${metadata.artist}||${metadata.title}`;
    if (trackId !== lastTrackId) {
        lastTrackId = trackId;
        const mediaEl = document.querySelector("audio, video");
        send(buildPayload(mediaEl));
    }
}, 1000);

// ========================
// POSITION UPDATES
// Sent on a timer but only while playing, at 200ms (5x/s instead of 20x/s)
// Python only needs position to sync lyrics, not millisecond precision
// ========================
setInterval(() => {
    const playbackState = navigator.mediaSession.playbackState;
    const mediaEl = document.querySelector("audio, video");

    // Only send position while actually playing
    const isPlaying = playbackState === "playing"
        || (playbackState === "none" && mediaEl && !mediaEl.paused && !mediaEl.ended);

    if (!isPlaying) return;

    send(buildPayload(mediaEl));
}, 200);