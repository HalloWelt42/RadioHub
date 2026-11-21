<script lang="ts">
  // Tonausgang am Rechner: hängt die Kanzel an das eine Tonelement der Seite (spieler/tonelement.ts, bleibt beim Wechsel
  // zwischen Rechner und Telefon bestehen, RAD-28). Dazu, was nur am Rechner läuft: beim
  // Start eine laufende Aufnahme wiederherstellen, Lautstärke angleichen, den Titel des Senders alle 15 Sekunden
  // abfragen und die Hördauer des Senders zählen. Was das Element meldet, landet in der Wiedergabe der Kanzel.
  import { app } from "./app";
  import { api } from "../lib/api.js";
  import * as engine from "../lib/playerEngine.js";
  import { anhaengen, tonelement } from "./tonelement";
  import type { Wiedergabe } from "./wiedergabe.svelte";

  let { wiedergabe }: { wiedergabe: Wiedergabe } = $props();

  const TITEL_TAKT_MS = 15000;

  const audio = tonelement();

  // eine beim Neuladen laufende Aufnahme wiederherstellen; die Meldungen des Elements in die Wiedergabe der Kanzel
  $effect(() => {
    engine.checkAndRecoverRecordingState();
    const zeit = () => wiedergabe.zeitAktualisieren();
    return anhaengen({
      timeupdate: zeit, loadedmetadata: zeit, durationchange: zeit,
      seeking: () => (wiedergabe.sucht = true), seeked: () => (wiedergabe.sucht = false),
      loadstart: () => wiedergabe.laden(), waiting: () => wiedergabe.warten(), playing: () => wiedergabe.spielen(),
      error: () => wiedergabe.fehler(audio.error?.code),
    });
  });

  // Lautstärke angleichen (auch wenn sie über die Tastatur kommt)
  $effect(() => {
    audio.volume = app.volume / 100;
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
