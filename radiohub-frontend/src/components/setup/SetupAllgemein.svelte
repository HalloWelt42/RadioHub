<script>
  import HiFiKnob from '../hifi/HiFiKnob.svelte';
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import SetupSpende from './SetupSpende.svelte';
  import { api } from '../../lib/api.js';
  import { appState, actions } from '../../lib/store.svelte.js';
  import * as router from '../../lib/router.js';
  import * as sfx from '../../lib/uiSounds.js';
  import { t, currentLanguage, setLanguage, availableLanguages } from '../../lib/i18n.svelte.js';
  import { parseMarkdown } from '../../lib/markdown.js';

  let config = $state({});
  let isLoading = $state(true);
  let clickSoundsEnabled = $state(true);
  let activeLang = $state(currentLanguage());

  // Sub-Tab aus Route-Segmenten ableiten
  let activeSubTab = $derived.by(() => {
    if (appState.activeTab !== 'settings') return 'einstellungen';
    const seg = appState.routeSegments;
    if (seg?.[0] !== 'allgemein') return 'einstellungen';
    const subId = seg[1] || 'einstellungen';
    return subTabs.some(t => t.id === subId) ? subId : 'einstellungen';
  });

  // Redirect wenn nur /setup/allgemein ohne Sub-Tab
  $effect(() => {
    if (appState.activeTab === 'settings'
        && appState.routeSegments?.[0] === 'allgemein'
        && !appState.routeSegments[1]) {
      router.navigate('/setup/allgemein/einstellungen', { replace: true });
      appState.routeSegments = ['allgemein', 'einstellungen'];
    }
  });

  // Markdown-Inhalte für Lizenz / Recht
  let lizenzContent = $state('');
  let rechtContent = $state('');

  const subTabs = [
    { id: 'einstellungen', label: 'EINSTELLUNGEN', icon: 'fa-gear', special: null },
    { id: 'tastatur', label: 'TASTATUR', icon: 'fa-keyboard', special: null },
    { id: 'bedanken', label: 'BEDANKEN', icon: 'fa-heart', special: 'bedanken' },
    { id: 'lizenz', label: 'LIZENZ', icon: 'fa-scale-balanced', special: null },
    { id: 'recht', label: 'RECHT', icon: 'fa-shield-halved', special: null }
  ];

  const hotkeys = [
    { group: 'keyPlayback', keys: [
      { key: 'Space', label: 'keySpace' },
      { key: 'S', label: 'keyStop' },
      { key: 'M', label: 'keyMute' }
    ]},
    { group: 'keyNavigation', keys: [
      { key: '\u2191', label: 'keyUp' },
      { key: '\u2193', label: 'keyDown' },
      { key: '\u2190', label: 'keyLeft' },
      { key: '\u2192', label: 'keyRight' }
    ]},
    { group: 'keyTabs', keys: [
      { key: '1', label: 'keyTab1' },
      { key: '2', label: 'keyTab2' },
      { key: '3', label: 'keyTab3' },
      { key: '4', label: 'keyTab4' }
    ]}
  ];

  $effect(() => {
    loadConfig();
  });

  async function loadConfig() {
    try {
      config = await api.getConfig();
      if (config.hls_rec_lookback_minutes) {
        appState.hlsRecLookbackMinutes = config.hls_rec_lookback_minutes;
      }
      clickSoundsEnabled = config.ui_click_sounds !== false;
      if (config.language) {
        activeLang = config.language;
      }
    } catch (e) {
      // Netzwerkfehler ignorieren
    }
    isLoading = false;
  }

  async function saveConfig(key, value) {
    try {
      await api.updateConfig({ [key]: value });
      config[key] = value;
    } catch (e) {
      actions.showToast(t('toast.speichernFehler'), 'error');
    }
  }

  function toggleClickSounds() {
    clickSoundsEnabled = !clickSoundsEnabled;
    sfx.setEnabled(clickSoundsEnabled);
    saveConfig('ui_click_sounds', clickSoundsEnabled);
    if (clickSoundsEnabled) sfx.click();
  }

  function switchLanguage(code) {
    activeLang = code;
    setLanguage(code);
    saveConfig('language', code);
  }

  // Markdown lazy-loading
  $effect(() => {
    if (activeSubTab === 'lizenz') loadLizenz();
    if (activeSubTab === 'recht') loadRecht();
  });

  async function loadLizenz() {
    if (lizenzContent) return;
    try {
      const res = await fetch('/legal/lizenz.md');
      if (res.ok) lizenzContent = parseMarkdown(await res.text());
    } catch (e) { /* ignorieren */ }
  }

  async function loadRecht() {
    if (rechtContent) return;
    try {
      const [dsRes, agbRes] = await Promise.all([
        fetch('/legal/datenschutz.md'),
        fetch('/legal/agb.md')
      ]);
      let md = '';
      if (dsRes.ok) md += await dsRes.text();
      if (agbRes.ok) md += '\n\n---\n\n' + await agbRes.text();
      rechtContent = parseMarkdown(md);
    } catch (e) { /* ignorieren */ }
  }
</script>

{#if isLoading}
  <div class="hifi-flex" style="justify-content:center; padding:60px;">
    <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
  </div>
{:else}
  <!-- Sub-Tab Navigation -->
  <div class="sub-tab-bar">
    {#each subTabs as tab}
      <button
        class="pill-btn"
        class:active={activeSubTab === tab.id}
        class:bedanken={tab.special === 'bedanken'}
        onclick={() => actions.navigateTo('/setup/allgemein/' + tab.id)}
      >
        <HiFiLed color={activeSubTab === tab.id ? (tab.special === 'bedanken' ? 'amber' : 'green') : 'off'} size="small" />
        <i class="fa-solid {tab.icon}" class:heart-icon={tab.special === 'bedanken'}></i>
        <span>{t('setup.' + tab.id)}</span>
      </button>
    {/each}
  </div>

  <!-- === EINSTELLUNGEN === -->
  {#if activeSubTab === 'einstellungen'}
    <div class="allgemein-grid">
      <!-- Theme -->
      <div class="hifi-panel">
        <div class="hifi-panel-header">
          <i class="fa-solid fa-palette header-icon"></i>
          <span class="hifi-font-label">{t('allgemein.displayTheme')}</span>
        </div>
        <div class="hifi-flex hifi-gap-md" style="padding:16px; align-items:center;">
          <button class="pill-btn" class:active={appState.theme === 'dark'} onclick={() => actions.setTheme('dark')}>
            <HiFiLed color={appState.theme === 'dark' ? 'green' : 'off'} />
            <span>{t('allgemein.dark')}</span>
          </button>
          <button class="pill-btn" class:active={appState.theme === 'light'} onclick={() => actions.setTheme('light')}>
            <HiFiLed color={appState.theme === 'light' ? 'green' : 'off'} />
            <span>{t('allgemein.light')}</span>
          </button>
        </div>
      </div>

      <!-- UI Sounds -->
      <div class="hifi-panel">
        <div class="hifi-panel-header">
          <i class="fa-solid fa-volume-high header-icon"></i>
          <span class="hifi-font-label">{t('allgemein.uiSounds')}</span>
        </div>
        <div class="hifi-flex hifi-gap-md" style="padding:16px; align-items:center;">
          <button class="pill-btn" class:active={clickSoundsEnabled} onclick={toggleClickSounds}>
            <HiFiLed color={clickSoundsEnabled ? 'green' : 'off'} />
            <span>{t('allgemein.clickSounds')}</span>
          </button>
        </div>
      </div>

      <!-- Sprache (volle Breite) -->
      <div class="hifi-panel span-full">
        <div class="hifi-panel-header">
          <i class="fa-solid fa-globe header-icon"></i>
          <span class="hifi-font-label">{t('allgemein.language')}</span>
          <span class="hifi-font-small" style="color:var(--hifi-text-muted); margin-left:8px;">
            {availableLanguages.find(l => l.code === activeLang)?.label || ''}
          </span>
        </div>
        <div class="lang-grid">
          {#each availableLanguages as lang}
            <button
              class="lang-btn"
              class:active={activeLang === lang.code}
              onclick={() => switchLanguage(lang.code)}
              title={lang.label}
            >
              <span class="lang-flag">{lang.flag}</span>
              <span class="lang-code">{lang.code.toUpperCase()}</span>
            </button>
          {/each}
        </div>
      </div>

      <!-- Timeshift Buffer (volle Breite) -->
      <div class="hifi-panel span-full">
        <div class="hifi-panel-header">
          <i class="fa-solid fa-clock-rotate-left header-icon"></i>
          <span class="hifi-font-label">{t('allgemein.timeshiftBuffer')}</span>
        </div>
        <div class="hifi-flex hifi-gap-xl" style="padding:24px; justify-content:center;">
          <HiFiKnob
            bind:value={config.hls_min_bitrate}
            min={32} max={128} step={16}
            unit="kbps" label={t('allgemein.minBitrate')}
            onchange={(e) => saveConfig('hls_min_bitrate', e.value)}
          />
          <HiFiKnob
            bind:value={config.hls_max_bitrate}
            min={64} max={320} step={32}
            unit="kbps" label={t('allgemein.maxBitrate')}
            onchange={(e) => saveConfig('hls_max_bitrate', e.value)}
          />
        </div>
        <div style="padding:0 16px 16px; text-align:center;">
          <span class="hifi-font-small" style="color:var(--hifi-text-muted);">
            {t('allgemein.timeshiftHint')}
          </span>
        </div>
      </div>

      <!-- HLS-REC (volle Breite) -->
      <div class="hifi-panel span-full">
        <div class="hifi-panel-header">
          <i class="fa-solid fa-backward header-icon"></i>
          <span class="hifi-font-label">{t('allgemein.hlsRec')}</span>
          <span class="hifi-font-small" style="color:var(--hifi-text-amber); margin-left:8px;">{t('allgemein.bufferAufnahme')}</span>
        </div>
        <div class="hifi-flex hifi-gap-xl" style="padding:24px; justify-content:center;">
          <HiFiKnob
            value={appState.hlsRecLookbackMinutes}
            min={1} max={120} step={1}
            unit="min" label={t('allgemein.lookback')}
            onchange={(e) => { appState.hlsRecLookbackMinutes = e.value; saveConfig('hls_rec_lookback_minutes', e.value); }}
          />
        </div>
        <div style="padding:0 16px 16px; text-align:center;">
          <span class="hifi-font-small" style="color:var(--hifi-text-muted);">
            {t('allgemein.lookbackHint')}
          </span>
        </div>
      </div>
    </div>

  <!-- === TASTATUR === -->
  {:else if activeSubTab === 'tastatur'}
    <div class="md-fill">
      <div class="hifi-panel md-panel">
        <div class="hifi-panel-header">
          <i class="fa-solid fa-keyboard header-icon"></i>
          <span class="hifi-font-label">{t('allgemein.tastaturTitle')}</span>
        </div>
        <div class="hotkey-hint">
          <i class="fa-solid fa-circle-info"></i>
          <span>{t('allgemein.tastaturHint')}</span>
        </div>
        <div class="hotkey-body">
          {#each hotkeys as group}
            <div class="hotkey-group">
              <div class="hotkey-group-title">{t('allgemein.' + group.group)}</div>
              {#each group.keys as hk}
                <div class="hotkey-row">
                  <kbd class="hotkey-badge">{hk.key}</kbd>
                  <span class="hotkey-label">{t('allgemein.' + hk.label)}</span>
                </div>
              {/each}
            </div>
          {/each}
        </div>
      </div>
    </div>

  <!-- === BEDANKEN === -->
  {:else if activeSubTab === 'bedanken'}
    <SetupSpende />

  <!-- === LIZENZ === -->
  {:else if activeSubTab === 'lizenz'}
    <div class="md-fill">
      <div class="hifi-panel md-panel">
        <div class="hifi-panel-header">
          <i class="fa-solid fa-scale-balanced header-icon"></i>
          <span class="hifi-font-label">{t('setup.lizenz')}</span>
        </div>
        <div class="md-body">
          {#if lizenzContent}
            {@html lizenzContent}
          {:else}
            <div class="hifi-flex" style="justify-content:center; padding:40px;">
              <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
            </div>
          {/if}
        </div>
      </div>
    </div>

  <!-- === RECHT === -->
  {:else if activeSubTab === 'recht'}
    <div class="md-fill">
      <div class="hifi-panel md-panel">
        <div class="hifi-panel-header">
          <i class="fa-solid fa-shield-halved header-icon"></i>
          <span class="hifi-font-label">{t('allgemein.datenschutzNutzung')}</span>
        </div>
        <div class="md-body">
          {#if rechtContent}
            {@html rechtContent}
          {:else}
            <div class="hifi-flex" style="justify-content:center; padding:40px;">
              <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
            </div>
          {/if}
        </div>
      </div>
    </div>
  {/if}
{/if}

<style>
  /* === Sub-Tab Bar === */
  .sub-tab-bar {
    display: flex;
    gap: 4px;
    margin-bottom: 16px;
    flex-shrink: 0;
  }

  /* === Pill Button (einheitliches Design wie obere Navigation) === */
  .pill-btn {
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

  .pill-btn:hover {
    background: var(--hifi-bg-secondary);
    color: var(--hifi-text-primary);
  }

  .pill-btn.active {
    background: var(--hifi-bg-panel);
    color: var(--hifi-accent);
    box-shadow: var(--hifi-shadow-inset);
  }

  /* === BEDANKEN: Orange statt Blau, rotes Herz === */
  .pill-btn.bedanken .heart-icon {
    color: var(--hifi-led-red);
  }

  .pill-btn.bedanken.active {
    color: var(--hifi-led-amber);
  }

  /* === Header Icon === */
  .header-icon {
    color: var(--hifi-accent);
    font-size: 12px;
    margin-right: 4px;
  }

  /* === Grid Layout === */
  .allgemein-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .span-full {
    grid-column: 1 / -1;
  }

  /* === Sprach-Grid === */
  .lang-grid {
    display: grid;
    grid-template-columns: repeat(10, 1fr);
    gap: 6px;
    padding: 12px;
  }

  .lang-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    padding: 8px 4px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
    cursor: pointer;
    transition: all 0.15s ease;
    box-shadow: var(--hifi-shadow-outset);
  }

  .lang-btn:hover {
    background: var(--hifi-bg-secondary);
    border-color: var(--hifi-border-light, rgba(255,255,255,0.1));
  }

  .lang-btn.active {
    background: var(--hifi-bg-panel);
    border-color: var(--hifi-accent);
    box-shadow: var(--hifi-shadow-inset);
  }

  .lang-flag {
    font-size: 18px;
    line-height: 1;
  }

  .lang-code {
    font-family: var(--hifi-font-display);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--hifi-text-secondary);
  }

  .lang-btn.active .lang-code {
    color: var(--hifi-accent);
  }

  /* === Hotkey-Ansicht === */
  .hotkey-hint {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    font-family: var(--hifi-font-body);
    font-size: 11px;
    color: var(--hifi-text-muted);
    border-bottom: 1px solid var(--hifi-border-dark);
    flex-shrink: 0;
  }

  .hotkey-hint i {
    color: var(--hifi-accent);
    font-size: 12px;
  }

  .hotkey-body {
    padding: 16px 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

  .hotkey-group-title {
    font-family: var(--hifi-font-display);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: var(--hifi-text-muted);
    margin-bottom: 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--hifi-border-dark);
  }

  .hotkey-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 5px 0;
  }

  .hotkey-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 36px;
    height: 28px;
    padding: 0 8px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-bottom-width: 2px;
    border-radius: 5px;
    font-family: var(--hifi-font-values);
    font-size: 11px;
    font-weight: 700;
    color: var(--hifi-text-primary);
    box-shadow: 0 1px 0 rgba(0,0,0,0.3);
  }

  .hotkey-label {
    font-family: var(--hifi-font-body);
    font-size: 13px;
    color: var(--hifi-text-secondary);
  }

  /* === Markdown Fill Container (füllt verfügbaren Platz) === */
  .md-fill {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .md-panel {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  /* === Markdown Viewer (Inner-Scroll) === */
  .md-body {
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

  .md-body :global(.md-h2) {
    font-family: var(--hifi-font-display);
    font-size: 18px;
    font-weight: 700;
    color: var(--hifi-text-primary);
    margin: 0 0 6px 0;
    letter-spacing: 0.5px;
  }

  .md-body :global(.md-h3) {
    font-family: var(--hifi-font-display);
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--hifi-text-primary);
    margin: 12px 0 4px 0;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--hifi-border-dark);
  }

  .md-body :global(.md-h4) {
    font-family: var(--hifi-font-display);
    font-size: 13px;
    font-weight: 600;
    color: var(--hifi-text-primary);
    margin: 8px 0 2px 0;
  }

  .md-body :global(.md-text) {
    font-family: var(--hifi-font-body);
    font-size: 13px;
    line-height: 1.7;
    color: var(--hifi-text-secondary);
    margin: 0;
  }

  .md-body :global(.md-list) {
    font-family: var(--hifi-font-body);
    font-size: 13px;
    line-height: 1.8;
    color: var(--hifi-text-secondary);
    margin: 0;
    padding-left: 24px;
  }

  .md-body :global(.md-list strong) {
    color: var(--hifi-text-primary);
    font-weight: 600;
  }

  .md-body :global(.md-link) {
    color: var(--hifi-accent);
    text-decoration: none;
  }

  .md-body :global(.md-link:hover) {
    text-decoration: underline;
  }

  .md-body :global(.md-code) {
    font-family: var(--hifi-font-values);
    font-size: 12px;
    padding: 2px 6px;
    background: var(--hifi-bg-tertiary);
    border-radius: 3px;
    color: var(--hifi-accent);
  }

  .md-body :global(.md-hr) {
    border: none;
    border-top: 1px solid var(--hifi-border-dark);
    margin: 12px 0;
  }
</style>
