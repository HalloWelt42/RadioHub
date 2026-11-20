<script lang="ts">
  // Tonausgang am Rechner: das eine Audio-Element (die Schnittansicht greift per document.querySelector("audio") darauf
  // zu), angebunden an die Engine (lib/playerEngine.js) wie bisher in HiFiPlayer. Dazu, was nur am Rechner läuft: beim
  // Start eine laufende Aufnahme wiederherstellen, Lautstärke angleichen, den Titel des Senders alle 15 Sekunden
  // abfragen und die Hördauer des Senders zählen. Was das Element meldet, landet in der Wiedergabe der Kanzel.
  import { app } from "./app";
  import { api } from "../lib/api.js";
  import * as engine from "../lib/playerEngine.js";
  import type { Wiedergabe } from "./wiedergabe.svelte";

  let { wiedergabe }: { wiedergabe: Wiedergabe } = $props();

  const TITEL_TAKT_MS = 15000;

  let audio = $state<HTMLAudioElement>();

  // Engine an das Element binden, eine beim Neuladen laufende Aufnahme wiederherstellen
  $effect(() => {
    if (!audio) return;
    engine.init(audio, app);
    engine.checkAndRecoverRecordingState();
  });

  // Lautstärke angleichen (auch wenn sie über die Tastatur kommt)
  $effect(() => {
    if (audio) audio.volume = app.volume / 100;
  });

  // Titel des Senders: sofort, dann alle 15 Sekunden, solange ein Sender mit Titelangabe (ICY) spielt
  $effect(() => {
    const sender = app.currentStation;
    if (!(app.isPlaying && sender?.icy && sender?.uuid)) {
      app.streamTitle = null;
      return;
    }
    const uuid = sender.uuid;
    titelHolen(uuid);
    const uhr = setInterval(() => titelHolen(uuid), TITEL_TAKT_MS);
    return () => clearInterval(uhr);
  });

  async function titelHolen(uuid: string) {
    try {
      const antwort = await api.getNowPlaying(uuid);
      if (antwort?.title) app.streamTitle = antwort.title;
    } catch {
      // kein Titel verfügbar
    }
  }

  // Hördauer: zählt je Sekunde, solange ein Sender spielt; neuer Sender oder Stopp fängt bei null an
  $effect(() => {
    void app.currentStation?.uuid;
    void app.isPlaying;
    wiedergabe.hoerdauerNull();
  });
  $effect(() => {
    if (!(app.currentStation && app.isPlaying && !app.isPaused)) return;
    const uhr = setInterval(() => wiedergabe.hoerdauerZaehlen(), 1000);
    return () => clearInterval(uhr);
  });
</script>

<!-- ohne crossorigin: Ströme kommen in Basic direkt vom Sender, und die meisten Sender schicken keine CORS-Kopfzeilen;
     mit dem Merkmal verweigerte der Browser sie ganz (RAD-10). Keine Auswertung braucht den Ton im Skript. -->
<audio
  bind:this={audio}
  ontimeupdate={() => wiedergabe.zeitAktualisieren()}
  onloadedmetadata={() => wiedergabe.zeitAktualisieren()}
  ondurationchange={() => wiedergabe.zeitAktualisieren()}
  onseeking={() => (wiedergabe.sucht = true)}
  onseeked={() => (wiedergabe.sucht = false)}
  onloadstart={() => wiedergabe.laden()}
  onwaiting={() => wiedergabe.warten()}
  onplaying={() => wiedergabe.spielen()}
  onended={() => engine.handleEnded()}
  onerror={(e) => { engine.handleError(e); wiedergabe.fehler(audio?.error?.code); }}
></audio>
