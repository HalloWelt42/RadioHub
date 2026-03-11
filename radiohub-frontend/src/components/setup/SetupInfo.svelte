<script>
  import HiFiLed from '../hifi/HiFiLed.svelte';

  let activeSection = $state('spende');
  let content = $state('');
  let isLoading = $state(true);

  const sections = [
    { id: 'spende', label: 'SPENDE', file: '/legal/spende.md' },
    { id: 'lizenz', label: 'LIZENZ', file: '/legal/lizenz.md' },
    { id: 'datenschutz', label: 'DATENSCHUTZ', file: '/legal/datenschutz.md' },
    { id: 'agb', label: 'AGBs', file: '/legal/agb.md' }
  ];

  // Icons pro Sektion (SVG path data)
  const icons = {
    spende: 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z',
    lizenz: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8',
    datenschutz: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
    agb: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M9 15l2 2 4-4'
  };

  $effect(() => {
    loadContent(activeSection);
  });

  async function loadContent(sectionId) {
    isLoading = true;
    const sec = sections.find(s => s.id === sectionId);
    if (!sec) return;
    try {
      const res = await fetch(sec.file);
      if (res.ok) {
        const md = await res.text();
        content = parseMarkdown(md);
      } else {
        content = '<p class="info-empty">Datei nicht gefunden: <code>public' + sec.file + '</code></p>';
      }
    } catch (e) {
      content = '<p class="info-empty">Laden fehlgeschlagen</p>';
    }
    isLoading = false;
  }

  /**
   * Einfacher Markdown-Parser (h1-h3, Listen, Absätze, Bold, Links, Code)
   */
  function parseMarkdown(md) {
    const lines = md.split('\n');
    let html = '';
    let inList = false;

    for (let line of lines) {
      line = line.trimEnd();

      // Leere Zeile
      if (!line.trim()) {
        if (inList) { html += '</ul>'; inList = false; }
        continue;
      }

      // Horizontale Linie
      if (/^---+$/.test(line.trim())) {
        if (inList) { html += '</ul>'; inList = false; }
        html += '<hr class="info-hr"/>';
        continue;
      }

      // Überschriften
      if (line.startsWith('### ')) {
        if (inList) { html += '</ul>'; inList = false; }
        html += '<h4 class="legal-sub">' + inline(line.slice(4)) + '</h4>';
        continue;
      }
      if (line.startsWith('## ')) {
        if (inList) { html += '</ul>'; inList = false; }
        html += '<h3 class="legal-title">' + inline(line.slice(3)) + '</h3>';
        continue;
      }
      if (line.startsWith('# ')) {
        if (inList) { html += '</ul>'; inList = false; }
        html += '<h2 class="legal-heading">' + inline(line.slice(2)) + '</h2>';
        continue;
      }

      // Listen
      if (line.startsWith('- ') || line.startsWith('* ')) {
        if (!inList) { html += '<ul class="info-list">'; inList = true; }
        html += '<li>' + inline(line.slice(2)) + '</li>';
        continue;
      }

      // Absatz
      if (inList) { html += '</ul>'; inList = false; }
      html += '<p class="info-text">' + inline(line) + '</p>';
    }

    if (inList) html += '</ul>';
    return html;
  }

  function esc(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function inline(s) {
    s = esc(s);
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener" class="info-link">$1</a>');
    s = s.replace(/`(.+?)`/g, '<code class="info-code">$1</code>');
    return s;
  }
</script>

<div class="info-layout">
  <!-- Sub-Tab-Bar -->
  <div class="sub-tab-bar">
    {#each sections as sec}
      <button
        class="sub-tab-btn"
        class:active={activeSection === sec.id}
        onclick={() => activeSection = sec.id}
      >
        <HiFiLed color={activeSection === sec.id ? 'green' : 'off'} size="small" />
        <span>{sec.label}</span>
      </button>
    {/each}
  </div>

  <!-- Content -->
  <div class="info-content">
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d={icons[activeSection] || icons.lizenz}/>
        </svg>
        <span class="hifi-font-label">{sections.find(s => s.id === activeSection)?.label || ''}</span>
      </div>
      <div class="section-body">
        {#if isLoading}
          <div class="hifi-flex" style="justify-content:center; padding:40px;">
            <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
          </div>
        {:else}
          {@html content}
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .info-layout {
    display: flex;
    flex-direction: column;
    gap: 12px;
    height: 100%;
  }

  /* === Sub-Tabs === */
  .sub-tab-bar {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
  }

  .sub-tab-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .sub-tab-btn:hover {
    background: var(--hifi-bg-secondary);
    color: var(--hifi-text-primary);
  }

  .sub-tab-btn.active {
    background: var(--hifi-bg-panel);
    color: var(--hifi-accent);
    border-color: var(--hifi-accent);
  }

  /* === Content === */
  .info-content {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

  .section-icon {
    width: 16px;
    height: 16px;
    color: var(--hifi-accent);
    margin-right: 4px;
    flex-shrink: 0;
  }

  .section-body {
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* === Markdown-Rendering (global wegen @html) === */
  .section-body :global(.legal-heading) {
    font-family: var(--hifi-font-display);
    font-size: 16px;
    font-weight: 700;
    color: var(--hifi-text-primary);
    margin: 0 0 4px 0;
    letter-spacing: 0.5px;
  }

  .section-body :global(.legal-title) {
    font-family: var(--hifi-font-display);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--hifi-text-primary);
    margin: 8px 0 2px 0;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--hifi-border-dark);
  }

  .section-body :global(.legal-sub) {
    font-family: var(--hifi-font-display);
    font-size: 11px;
    font-weight: 600;
    color: var(--hifi-text-primary);
    margin: 4px 0 2px 0;
  }

  .section-body :global(.info-text) {
    font-family: var(--hifi-font-body);
    font-size: 12px;
    line-height: 1.7;
    color: var(--hifi-text-secondary);
    margin: 0;
  }

  .section-body :global(.info-empty) {
    font-family: var(--hifi-font-body);
    font-size: 12px;
    color: var(--hifi-text-muted);
    text-align: center;
    padding: 40px 0;
  }

  .section-body :global(.info-empty code) {
    color: var(--hifi-accent);
  }

  .section-body :global(.info-list) {
    font-family: var(--hifi-font-body);
    font-size: 12px;
    line-height: 1.8;
    color: var(--hifi-text-secondary);
    margin: 0;
    padding-left: 20px;
  }

  .section-body :global(.info-list strong) {
    color: var(--hifi-text-primary);
    font-weight: 600;
  }

  .section-body :global(.info-link) {
    color: var(--hifi-accent);
    text-decoration: none;
  }

  .section-body :global(.info-link:hover) {
    text-decoration: underline;
  }

  .section-body :global(.info-code) {
    font-family: var(--hifi-font-values);
    font-size: 11px;
    padding: 2px 6px;
    background: var(--hifi-bg-tertiary);
    border-radius: 3px;
    color: var(--hifi-accent);
  }

  .section-body :global(.info-hr) {
    border: none;
    border-top: 1px solid var(--hifi-border-dark);
    margin: 8px 0;
  }
</style>
