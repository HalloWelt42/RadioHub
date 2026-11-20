<script lang="ts">
  // Kanzel: die Abspielleiste am Rechner nach dem abgenommenen Entwurf (mockups/radio-filter/rechner.html, RAD-3; Bau
  // RAD-8), Nachfolgerin von HiFiPlayer. Module Anzeige, Quelle und Zeit, Lautstärke und Steuerung; den Hausempfang
  // zeigt sie erst mit der Übergabe (Etappe 4). Sie liest den Zustand aus appState und dem Tonausgang, die Zuordnung zur
  // Anzeige steht in kanzel.ts, die Aktionen in aktionen.ts; die Wiedergabe selbst bleibt in lib/playerEngine.js.
  import { app } from "./app";
  import { t } from "../lib/i18n.svelte.js";
  import Tonausgang from "./Tonausgang.svelte";
  import Anzeige from "./Anzeige.svelte";
  import QuelleZeit from "./QuelleZeit.svelte";
  import Lautstaerke from "./Lautstaerke.svelte";
  import Steuerung from "./Steuerung.svelte";
  import { Wiedergabe } from "./wiedergabe.svelte";
  import { Bitrate } from "./bitrate.svelte";
  import { bitrateLage, bitrateText, kanzelAnzeige, kanzelTasten, type Stand } from "./kanzel";
  import { modusWechseln } from "./aktionen";
  import { faehigkeiten } from "../lib/playerEngine.js";

  /** was der Weg der Wiedergabe kann (fest für die Sitzung: volle App oder Webversion) */
  const weg = faehigkeiten();

  /** so lange bleibt die Taste Original oder Zeitversatz höchstens gedrückt, falls der Wechsel nie ankommt */
  const MODUS_FRIST_MS = 20000;

  const wiedergabe = new Wiedergabe();

  const stand = $derived<Stand>({
    isPlaying: app.isPlaying,
    isPaused: app.isPaused,
    isRecording: app.isRecording,
    playerMode: app.playerMode,
    isLive: app.isLive ?? true,
    currentStation: app.currentStation,
    currentEpisode: app.currentEpisode,
    currentRecording: app.currentRecording,
    streamTitle: app.streamTitle,
    streamQuality: app.streamQuality,
    hlsStatus: app.hlsStatus,
    hlsActive: app.hlsActive,
    currentSegment: app.currentSegment,
    recordingElapsed: app.recordingElapsed,
    recordingIcyCount: app.recordingIcyCount,
    canPlayDirect: app.canPlayDirect,
    canPlayHLS: app.canPlayHLS,
    playMode: app.playMode,
    stations: app.stations ?? [],
    podcastPlaylist: app.podcastPlaylist ?? [],
    currentEpisodeIndex: app.currentEpisodeIndex ?? -1,
    recordingPlaylist: app.recordingPlaylist ?? [],
    medium: wiedergabe.medium,
    fehlerCode: wiedergabe.fehlerCode,
    zeit: wiedergabe.zeit,
    dauer: wiedergabe.dauer,
    lage: wiedergabe.lage,
    hoerdauer: wiedergabe.hoerdauer,
    weg,
  });

  // Original oder Zeitversatz: Taste bleibt gedrückt, bis der neue Modus gilt
  let modusVon = $state<string | null>(null);
  $effect(() => {
    if (modusVon !== null && app.playerMode !== modusVon) modusVon = null;
  });
  $effect(() => {
    if (modusVon === null) return;
    const frist = setTimeout(() => (modusVon = null), MODUS_FRIST_MS);
    return () => clearTimeout(frist);
  });

  const anzeige = $derived(kanzelAnzeige(stand, t));
  const tasten = $derived(kanzelTasten(stand, t, modusVon !== null));
  // Bitrate des Zeitversatzes: Drehwahl in der Steuerung, im Glas nur als Leuchtschrift
  const bitrate = new Bitrate();
  const bitrateHinweis = $derived(bitrateText(stand, bitrate.vorgabe, bitrate.wechselt, t));
  const hoerbar = $derived(app.isPlaying && !app.isPaused && (anzeige.zustand !== "laedt" && anzeige.zustand !== "fehler"));
</script>

<footer class="rh-kanzel" data-zustand={anzeige.zustand} aria-label={t("kanzel.abspielleiste")}>
  <Tonausgang {wiedergabe} />
  <div class="rh-kanzel-voll">
    <Anzeige {anzeige} hinweis={bitrateHinweis} aufnahme={app.isRecording} />
    <QuelleZeit {anzeige} {stand} {wiedergabe} />
    <Lautstaerke {hoerbar} />
    <Steuerung {tasten} onmodus={() => (modusVon = modusWechseln())} {bitrate} lage={bitrateLage(stand)} />
  </div>
</footer>
