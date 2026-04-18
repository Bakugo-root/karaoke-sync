console.log("🔥 BACKGROUND STARTED");

let socket = null;
let connected = false;

function connectWS() {
    if (connected) return;

    console.log("🔄 Tentative de connexion WS...");
    socket = new WebSocket("ws://127.0.0.1:8766");

    socket.onopen = () => {
        connected = true;
        console.log("✅ WS connecté à Python");
    };

    socket.onclose = () => {
        if (connected) {
            console.log("⚠️ WS fermé");
        }
        connected = false;
        socket = null;

        // Réessaye dans 2 secondes
        setTimeout(connectWS, 2000);
    };

    socket.onerror = () => {
        // erreur normale si Python n'est pas encore lancé
        connected = false;
        socket.close();
    };
}

// 🔁 Lancement immédiat + retry auto
connectWS();

// 📤 Réception des données du content script
chrome.runtime.onMessage.addListener((data) => {
    if (socket && connected) {
        socket.send(JSON.stringify(data));
    }
});
