<script>
  import HiFiPlayer from './components/HiFiPlayer.svelte';
  import HiFiToast from './components/hifi/HiFiToast.svelte';
  import HiFiTour from './components/hifi/HiFiTour.svelte';
  import HiFiLed from './components/hifi/HiFiLed.svelte';
  import { tourState, toggleMenu } from './lib/tour/tourEngine.svelte.js';
  import StationsTab from './components/StationsTab.svelte';
  import RecordingsTab from './components/RecordingsTab.svelte';
  import PodcastsTab from './components/PodcastsTab.svelte';
  import SettingsTab from './components/SettingsTab.svelte';
  import { appState, actions } from './lib/store.svelte.js';
  import { t } from './lib/i18n.svelte.js';
  import { api } from './lib/api.js';
  import * as router from './lib/router.js';
  import * as sfx from './lib/uiSounds.js';

  let backendOnline = $state(false);

  // Logo Glow Animation (nur Dark Mode)
  $effect(() => {
    if (appState.theme !== 'dark') return;
    let forward = true;
    const letters = document.querySelectorAll('.logo-letter');
    if (!letters.length) return;

    function runSweep() {
      letters.forEach((sp, i) => {
        const delay = forward ? i * 0.15 : (letters.length - 1 - i) * 0.15;
        sp.style.animation = 'none';
        sp.offsetHeight;
        sp.style.animation = `letterGlow 0.6s ease-in-out ${delay}s both`;
      });
      forward = !forward;
    }

    runSweep();
    const iv = setInterval(runSweep, 7000);
    return () => clearInterval(iv);
  });

  // Theme init
  $effect(() => {
    actions.initTheme();
  });

  // Router init
  $effect(() => {
    const initial = router.init((info) => {
      // Hash -> State (Browser Back/Forward, manuelle URL-Eingabe)
      appState.activeTab = info.tab;
      appState.routeSegments = info.segments;
    });

    // Initialen Hash anwenden
    appState.activeTab = initial.tab;
    appState.routeSegments = initial.segments;

    // Default-Hash setzen wenn keiner vorhanden
    if (!location.hash || location.hash === '#' || location.hash === '#/') {
      router.navigate('/tuner', { replace: true });
    }
  });
  
  // Health Check + Config Init
  $effect(() => {
    api.health().then(() => {
      backendOnline = true;
      actions.initConfig();
    }).catch(() => {
      actions.showToast(t('toast.backendOffline'), 'error');
      backendOnline = false;
    });
  });
  
  const tabs = [
    { id: 'radio', key: 'nav.tuner' },
    { id: 'recordings', key: 'nav.recorder' },
    { id: 'podcasts', key: 'nav.podcast' },
    { id: 'settings', key: 'nav.setup' }
  ];

  // === Nav-LED Logik ===
  // Welcher Tab "besitzt" die aktuelle Wiedergabe?
  let playbackTab = $derived(
    !appState.isPlaying && !appState.isPaused ? null :
    appState.playerMode === 'podcast' ? 'podcasts' :
    appState.playerMode === 'recording' ? 'recordings' :
    appState.playerMode === 'hls' || appState.playerMode === 'direct' ? 'radio' :
    null
  );

  function navLedColor(tabId) {
    if (appState.activeTab === tabId) return 'green';
    // Aufnahme hat Vorrang: rot blinkend
    if (tabId === 'radio' && appState.isRecording) return 'red';
    // Wiedergabe-Herkunft: grün pulsierend
    if (playbackTab === tabId) return 'green';
    return 'off';
  }

  function navLedPulse(tabId) {
    if (appState.activeTab === tabId) return false;
    return playbackTab === tabId;
  }

  // === Globale Tastatursteuerung ===
  function handleGlobalKeydown(e) {
    // Nicht abfangen wenn in Input/Textarea
    const tag = e.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

    const rec = appState.isRecording;

    switch (e.key) {
      case ' ':  // Space = Play/Pause (Direct: Stop statt Pause)
        e.preventDefault();
        if (rec) break;  // Bei Aufnahme gesperrt
        if (appState.playerMode === 'direct') {
          actions.stop();
        } else if (appState.playerMode !== 'none') {
          actions.togglePause();
        }
        break;

      case 's':  // S = Stop
        if (rec) break;  // Bei Aufnahme gesperrt
        if (!e.ctrlKey && !e.metaKey) {
          actions.stop();
        }
        break;

      case 'ArrowUp':  // Pfeil hoch = Lauter
        e.preventDefault();
        actions.setVolume(Math.min(100, appState.volume + 5));
        break;

      case 'ArrowDown':  // Pfeil runter = Leiser
        e.preventDefault();
        actions.setVolume(Math.max(0, appState.volume - 5));
        break;

      case 'ArrowLeft':  // Pfeil links = Vorheriger Sender
        e.preventDefault();
        if (rec) break;  // Bei Aufnahme gesperrt
        actions.navigatePrev();
        break;

      case 'ArrowRight':  // Pfeil rechts = Nächster Sender
        e.preventDefault();
        if (rec) break;  // Bei Aufnahme gesperrt
        actions.navigateNext();
        break;

      case 'm':  // M = Mute toggle
        if (!e.ctrlKey && !e.metaKey) {
          actions.setVolume(appState.volume > 0 ? 0 : 70);
        }
        break;

      case '1':  // 1-4 = Tab wechseln
        actions.setTab('radio');
        break;
      case '2':
        actions.setTab('recordings');
        break;
      case '3':
        actions.setTab('podcasts');
        break;
      case '4':
        actions.setTab('settings');
        break;

      case 'Escape':  // Escape = Overlays schließen
        // Wird von Komponenten selbst behandelt
        break;
    }
  }
</script>

<svelte:window onkeydown={handleGlobalKeydown} />

<div class="hifi-app">
  <!-- Header -->
  <header class="hifi-header">
    <div class="hifi-logo">
      <div class="hifi-logo-row">
        <span class="hifi-logo-text">{#each 'RadioHub'.split('') as ch, i}<span class="logo-letter" style="--i:{i}">{ch}</span>{/each}</span>
        <button class="donate-heart" onclick={() => { actions.navigateTo('/setup/allgemein/bedanken'); sfx.select(); }} title={t('app.unterstuetzenTitle')}>
          <i class="fa-solid fa-heart"></i>
        </button>
      </div>
      <span class="hifi-logo-sub">{t('app.digitalAudioSystem')}</span>
    </div>
    
    <nav class="hifi-nav">
      {#each tabs as tab, i}
        <button
          class="hifi-nav-btn"
          class:active={appState.activeTab === tab.id}
          onclick={() => { actions.setTab(tab.id); sfx.select(); }}
          onmouseenter={sfx.hoverSoft}
          title={t(tab.key) + ' (' + (i + 1) + ')'}
        >
          <HiFiLed color={navLedColor(tab.id)} size="small" blink={tab.id === 'radio' && appState.isRecording && appState.activeTab !== 'radio'} pulse={navLedPulse(tab.id)} />
          {t(tab.key)}
        </button>
      {/each}
    </nav>
    
    <div class="hifi-header-right">
      <!-- Lernmodus -->
      <button class="tour-toggle-btn" class:active={tourState.active || tourState.menuOpen} onclick={() => { toggleMenu(); sfx.click(); }} onmouseenter={sfx.hoverSoft} title="Lernmodus">
        <i class="fa-solid fa-life-ring"></i>
      </button>

      <!-- Theme Switch -->
      <button class="hifi-nav-btn active" onclick={() => actions.toggleTheme()} onmouseenter={sfx.hoverSoft} title={appState.theme === 'dark' ? t('common.themeLight') : t('common.themeDark')}>
        <HiFiLed color={appState.theme === 'dark' ? 'off' : 'yellow'} size="small" />
        {appState.theme === 'dark' ? t('nav.dark') : t('nav.light')}
      </button>
      
      <!-- Status -->
      <div class="hifi-status">
        <HiFiLed color={backendOnline ? 'green' : 'red'} size="small" />
        <span class="hifi-font-label">{backendOnline ? t('nav.online') : t('nav.offline')}</span>
      </div>
    </div>
  </header>
  
  <!-- Main Content -->
  <main class="hifi-main">
    {#if appState.activeTab === 'radio'}
      <StationsTab />
    {:else if appState.activeTab === 'recordings'}
      <RecordingsTab />
    {:else if appState.activeTab === 'podcasts'}
      <PodcastsTab />
    {:else if appState.activeTab === 'settings'}
      <SettingsTab />
    {/if}
  </main>
  
  <!-- Player -->
  <HiFiPlayer />

  <!-- Footer -->
  <footer class="hifi-footer">
    <span>&copy; {new Date().getFullYear()} <a href="https://github.com/HalloWelt42/RadioHub" target="_blank" rel="noopener"><i class="fa-brands fa-github"></i> HalloWelt42</a> - RadioHub v{__APP_VERSION__}</span>
  </footer>
</div>

<!-- Toast außerhalb hifi-app für korrektes z-index Stacking -->
<HiFiToast />

<!-- Lernmodus Tour-Overlay -->
<HiFiTour />

<style>
  .hifi-app {
    position: relative;
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
    background: var(--hifi-bg-primary);
    color: var(--hifi-text-primary);
    font-family: var(--hifi-font-values);
  }
  
  .hifi-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 20px;
    background:
        linear-gradient(180deg, rgba(255,255,255,0.04) 0%, transparent 40%, rgba(0,0,0,0.03) 100%),
        var(--hifi-brushed-metal),
        var(--hifi-bg-panel);
    border-bottom: 1px solid var(--hifi-border-dark);
    border-radius: 0;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.1),
        inset 0 -1px 0 rgba(0,0,0,0.08),
        0 2px 4px rgba(0,0,0,0.15);
  }
  
  .hifi-logo {
    display: flex;
    flex-direction: column;
  }

  .hifi-logo-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  @keyframes -global-heartPulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.15); }
  }

  .donate-heart {
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    font-size: 16px;
    color: #cc2244;
    text-shadow:
        0 0 6px rgba(204, 34, 68, 0.6),
        0 0 12px rgba(204, 34, 68, 0.3),
        0 1px 1px rgba(0,0,0,0.4),
        0 -1px 0 rgba(255,255,255,0.15);
    filter: drop-shadow(0 2px 3px rgba(0,0,0,0.4));
    transition: all 0.2s ease;
    animation: heartPulse 2s ease-in-out infinite;
  }

  .donate-heart:hover {
    color: #ee3355;
    text-shadow:
        0 0 10px rgba(238, 51, 85, 0.8),
        0 0 20px rgba(238, 51, 85, 0.5),
        0 0 30px rgba(238, 51, 85, 0.3),
        0 1px 1px rgba(0,0,0,0.4);
    transform: scale(1.2);
    animation: none;
  }

  .donate-heart:active {
    transform: scale(0.95);
  }
  
  /* Logo bleibt bei separater Schrift */
  .hifi-logo-text {
    font-family: var(--hifi-font-segment);
    font-size: 26px;
    font-weight: 900;
    color: var(--hifi-accent);
    letter-spacing: 2px;
  }

  .logo-letter {
    display: inline-block;
  }

  @keyframes -global-letterGlow {
    0%   { text-shadow: none; }
    40%  { text-shadow: 0 0 8px rgba(74,144,217,0.9), 0 0 20px rgba(74,144,217,0.5), 0 0 40px rgba(74,144,217,0.3); }
    100% { text-shadow: none; }
  }
  
  .hifi-logo-sub {
    font-family: var(--hifi-font-values);
    font-size: 8px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #555;
  }

  :global([data-theme="dark"]) .hifi-logo-sub {
    color: transparent;
    text-shadow: none;
    background: linear-gradient(90deg,
        #dd3366, #dd6633, #ddaa33, #33dd77, #33bbdd, #5533dd, #cc33dd,
        #dd3366, #dd6633, #ddaa33, #33dd77, #33bbdd, #5533dd, #cc33dd, #dd3366
    );
    background-size: 200% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: specFlow 20s linear infinite;
  }

  @keyframes specFlow {
    0%   { background-position: 0% center; }
    100% { background-position: -200% center; }
  }
  
  .hifi-nav {
    display: flex;
    gap: 4px;
    background:
        linear-gradient(180deg, rgba(255,255,255,0.05) 0%, transparent 50%, rgba(0,0,0,0.04) 100%),
        var(--hifi-brushed-metal),
        var(--hifi-bg-panel);
    padding: 10px 16px;
    border-radius: var(--hifi-border-radius-pill);
    box-shadow:
        var(--hifi-shadow-button),
        inset 0 1px 0 rgba(255,255,255,0.1),
        inset 0 -1px 0 rgba(0,0,0,0.06);
    position: relative;
    z-index: 2;
    transform: translateY(20px);
  }

  .hifi-nav-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 18px;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-pill);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  
  .hifi-nav-btn:hover {
    background: var(--hifi-bg-secondary);
  }
  
  .hifi-nav-btn.active {
    background: var(--hifi-bg-panel);
    color: var(--hifi-accent);
    box-shadow: var(--hifi-shadow-inset);
  }
  
  .hifi-header-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  
  
  /* Lernmodus-Button (Rettungsring) */
  .tour-toggle-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    padding: 0;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: 50%;
    color: var(--hifi-text-secondary);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .tour-toggle-btn:hover {
    color: var(--hifi-accent);
    background: var(--hifi-bg-secondary);
  }
  .tour-toggle-btn.active {
    color: var(--hifi-led-amber);
    background: var(--hifi-bg-panel);
    box-shadow: var(--hifi-shadow-inset), 0 0 8px rgba(230, 162, 60, 0.3);
    text-shadow: 0 0 6px rgba(230, 162, 60, 0.6);
  }

  .hifi-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: var(--hifi-font-values);
    font-size: 10px;
  }
  
  .hifi-main {
    flex: 1;
    overflow: hidden;
    background: var(--hifi-bg-secondary);
  }

  .hifi-footer {
    position: absolute;
    bottom: 2px;
    left: 8px;
    font-family: var(--hifi-font-values);
    font-size: 8px;
    color: rgba(255, 255, 255, 0.35);
    letter-spacing: 0.5px;
    z-index: 100;
  }

  .hifi-footer a {
    color: inherit;
    text-decoration: none;
  }

  .hifi-footer a:hover {
    color: rgba(255, 255, 255, 0.6);
    text-decoration: underline;
  }
</style>
