<script>
  /**
   * HiFiTour v1.0 - Interaktiver Lernmodus Overlay
   * Spotlight + Tooltip + Fortschrittsanzeige.
   * Lose gekoppelt: liest nur tourState und appState.
   */
  import HiFiLed from './HiFiLed.svelte';
  import { tourState, currentStep, next, prev, skip, start, toggleMenu, closeMenu, getScenarioList } from '../../lib/tour/tourEngine.svelte.js';
  import { tt } from '../../lib/tour/tourLocales.js';
  import { t, currentLanguage } from '../../lib/i18n.svelte.js';
  import { appState } from '../../lib/store.svelte.js';
  import * as sfx from '../../lib/uiSounds.js';

  let lang = $derived(( void t(''), currentLanguage() ));

  // Ziel-Element Position
  let targetRect = $state(null);
  let tooltipStyle = $state('');

  // Ziel-Element tracken
  $effect(() => {
    const step = currentStep();
    if (!step?.target) { targetRect = null; return; }

    function updateRect() {
      const el = document.querySelector(step.target);
      if (el) {
        const r = el.getBoundingClientRect();
        targetRect = { top: r.top, left: r.left, width: r.width, height: r.height };
        computeTooltipPosition(r, step.position || 'bottom');
      } else {
        targetRect = null;
      }
    }

    // Initial + bei Scroll/Resize
    updateRect();
    const timer = setInterval(updateRect, 500);
    window.addEventListener('resize', updateRect);
    window.addEventListener('scroll', updateRect, true);

    return () => {
      clearInterval(timer);
      window.removeEventListener('resize', updateRect);
      window.removeEventListener('scroll', updateRect, true);
    };
  });

  function computeTooltipPosition(rect, position) {
    const pad = 16;
    const tooltipW = 320;
    const tooltipH = 180;

    let top, left;
    switch (position) {
      case 'top':
        top = rect.top - tooltipH - pad;
        left = rect.left + rect.width / 2 - tooltipW / 2;
        break;
      case 'bottom':
        top = rect.bottom + pad;
        left = rect.left + rect.width / 2 - tooltipW / 2;
        break;
      case 'left':
        top = rect.top + rect.height / 2 - tooltipH / 2;
        left = rect.left - tooltipW - pad;
        break;
      case 'right':
        top = rect.top + rect.height / 2 - tooltipH / 2;
        left = rect.right + pad;
        break;
      default:
        top = rect.bottom + pad;
        left = rect.left;
    }

    // Viewport-Begrenzung
    top = Math.max(8, Math.min(top, window.innerHeight - tooltipH - 8));
    left = Math.max(8, Math.min(left, window.innerWidth - tooltipW - 8));

    tooltipStyle = `top: ${top}px; left: ${left}px; width: ${tooltipW}px;`;
  }

  function handleBackdropClick() {
    const step = currentStep();
    if (!step?.waitFor) {
      next();
      sfx.click();
    }
  }

  function handleNext() { next(); sfx.click(); }
  function handlePrev() { prev(); sfx.click(); }
  function handleSkip() { skip(); sfx.click(); }

  function handleStartScenario(id) {
    start(id);
    sfx.click();
  }

  // Clip-Path für Spotlight-Loch berechnen
  let clipPath = $derived.by(() => {
    if (!targetRect) return 'none';
    const p = 6; // Padding um das Element
    const t = targetRect.top - p;
    const l = targetRect.left - p;
    const b = targetRect.top + targetRect.height + p;
    const r = targetRect.left + targetRect.width + p;
    const br = 8; // Border-Radius

    // Polygon mit Loch (äußerer Rahmen + inneres Rechteck invertiert)
    return `polygon(
      0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%,
      ${l + br}px ${t}px,
      ${r - br}px ${t}px,
      ${r}px ${t + br}px,
      ${r}px ${b - br}px,
      ${r - br}px ${b}px,
      ${l + br}px ${b}px,
      ${l}px ${b - br}px,
      ${l}px ${t + br}px,
      ${l + br}px ${t}px
    )`;
  });
</script>

<!-- Szenario-Menü (Dropdown) -->
{#if tourState.menuOpen && !tourState.active}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="tour-menu-backdrop" onclick={closeMenu}></div>
  <div class="tour-menu">
    <div class="tour-menu-header">{tt('tour.menuTitle', lang)}</div>
    {#each getScenarioList() as scenario}
      <button
        class="tour-menu-item"
        class:completed={scenario.completed}
        onclick={() => handleStartScenario(scenario.id)}
      >
        <HiFiLed color={scenario.completed ? 'green' : 'amber'} size="small" />
        <div class="tour-menu-info">
          <div class="tour-menu-title">{tt(scenario.title, lang)}</div>
          <div class="tour-menu-desc">{tt(scenario.description, lang)}</div>
        </div>
        <span class="tour-menu-steps">{scenario.stepCount}</span>
      </button>
    {/each}
  </div>
{/if}

<!-- Tour Overlay -->
{#if tourState.active && currentStep()}
  <!-- Backdrop mit Spotlight-Loch -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="tour-backdrop"
    style="clip-path: {clipPath};"
    onclick={handleBackdropClick}
  ></div>

  <!-- Highlight-Ring -->
  {#if targetRect}
    <div class="tour-highlight" style="
      top: {targetRect.top - 6}px;
      left: {targetRect.left - 6}px;
      width: {targetRect.width + 12}px;
      height: {targetRect.height + 12}px;
    "></div>
  {/if}

  <!-- Tooltip -->
  <div class="tour-tooltip" style={tooltipStyle}>
    <div class="tour-tooltip-header">
      <span class="tour-tooltip-title">{tt(currentStep().titleKey, lang)}</span>
      <button class="tour-tooltip-close" onclick={handleSkip} title={tt('tour.close', lang)}>
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>
    <div class="tour-tooltip-text">{tt(currentStep().textKey, lang)}</div>

    {#if currentStep().waitFor}
      <div class="tour-tooltip-hint">
        <HiFiLed color="amber" size="small" pulse={true} />
        <span class="tour-hint-text">{tt('tour.waitAction', lang)}</span>
      </div>
    {/if}

    <div class="tour-tooltip-footer">
      <div class="tour-progress">
        <span class="tour-step-info">{tt('tour.step', lang)} {tourState.stepIndex + 1} {tt('tour.of', lang)} {tourState.steps.length}</span>
        <div class="tour-dots">
          {#each tourState.steps as _, i}
            <span class="tour-dot" class:active={i === tourState.stepIndex} class:done={i < tourState.stepIndex}></span>
          {/each}
        </div>
      </div>
      <div class="tour-buttons">
        {#if tourState.stepIndex > 0}
          <button class="tour-btn tour-btn-secondary" onclick={handlePrev}>{tt('tour.prev', lang)}</button>
        {/if}
        {#if !currentStep().waitFor}
          <button class="tour-btn tour-btn-primary" onclick={handleNext}>
            {tourState.stepIndex < tourState.steps.length - 1 ? tt('tour.next', lang) : tt('tour.completed', lang)}
          </button>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  /* Backdrop */
  .tour-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 4500;
    cursor: pointer;
    transition: clip-path 0.3s ease;
  }

  /* Highlight-Ring um Ziel-Element */
  .tour-highlight {
    position: fixed;
    z-index: 4501;
    border: 2px solid var(--hifi-accent, #4a90d9);
    border-radius: 8px;
    box-shadow: 0 0 0 4px rgba(74, 144, 217, 0.2), 0 0 20px rgba(74, 144, 217, 0.15);
    pointer-events: none;
    transition: all 0.3s ease;
    animation: tour-pulse 2s ease-in-out infinite;
  }

  @keyframes tour-pulse {
    0%, 100% { box-shadow: 0 0 0 4px rgba(74, 144, 217, 0.2), 0 0 20px rgba(74, 144, 217, 0.15); }
    50% { box-shadow: 0 0 0 6px rgba(74, 144, 217, 0.3), 0 0 30px rgba(74, 144, 217, 0.25); }
  }

  /* Tooltip */
  .tour-tooltip {
    position: fixed;
    z-index: 4502;
    background: var(--hifi-bg-secondary, #252525);
    border: 1px solid var(--hifi-border, #3a3a3a);
    border-radius: var(--hifi-border-radius-md, 12px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    padding: 16px;
    transition: top 0.3s ease, left 0.3s ease;
    font-family: 'Barlow', sans-serif;
  }

  .tour-tooltip-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .tour-tooltip-title {
    font-family: var(--hifi-font-labels, 'Barlow Condensed', sans-serif);
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--hifi-accent, #4a90d9);
  }

  .tour-tooltip-close {
    background: none;
    border: none;
    color: var(--hifi-text-secondary, #888);
    cursor: pointer;
    font-size: 14px;
    padding: 4px;
    border-radius: 4px;
    transition: color 0.15s;
  }
  .tour-tooltip-close:hover {
    color: var(--hifi-text-primary, #e0e0e0);
  }

  .tour-tooltip-text {
    font-size: 13px;
    line-height: 1.5;
    color: var(--hifi-text-primary, #e0e0e0);
    margin-bottom: 12px;
  }

  .tour-tooltip-hint {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    background: rgba(255, 204, 0, 0.08);
    border-radius: 6px;
    margin-bottom: 12px;
  }

  .tour-hint-text {
    font-size: 11px;
    font-weight: 500;
    color: var(--hifi-led-yellow, #ffcc00);
    font-style: italic;
  }

  .tour-tooltip-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .tour-progress {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .tour-step-info {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    color: var(--hifi-text-secondary, #888);
    text-transform: uppercase;
  }

  .tour-dots {
    display: flex;
    gap: 4px;
  }

  .tour-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--hifi-border-dark, #333);
    transition: background 0.2s;
  }
  .tour-dot.active {
    background: var(--hifi-accent, #4a90d9);
    box-shadow: 0 0 4px rgba(74, 144, 217, 0.5);
  }
  .tour-dot.done {
    background: var(--hifi-led-green, #33cc33);
  }

  .tour-buttons {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }

  .tour-btn {
    font-family: var(--hifi-font-labels, 'Barlow Condensed', sans-serif);
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 6px 14px;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    transition: background 0.15s, transform 0.1s;
  }
  .tour-btn:active { transform: scale(0.96); }

  .tour-btn-primary {
    background: var(--hifi-accent, #4a90d9);
    color: #fff;
  }
  .tour-btn-primary:hover { background: #5a9fe9; }

  .tour-btn-secondary {
    background: var(--hifi-bg-primary, #1e1e1e);
    color: var(--hifi-text-secondary, #888);
    border: 1px solid var(--hifi-border-dark, #333);
  }
  .tour-btn-secondary:hover { color: var(--hifi-text-primary, #e0e0e0); }

  /* Szenario-Menü */
  .tour-menu-backdrop {
    position: fixed;
    inset: 0;
    z-index: 4400;
  }

  .tour-menu {
    position: fixed;
    top: 52px;
    right: 120px;
    z-index: 4450;
    background: var(--hifi-bg-secondary, #252525);
    border: 1px solid var(--hifi-border, #3a3a3a);
    border-radius: var(--hifi-border-radius-md, 12px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    min-width: 280px;
    overflow: hidden;
  }

  .tour-menu-header {
    font-family: var(--hifi-font-labels, 'Barlow Condensed', sans-serif);
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary, #888);
    padding: 12px 16px 8px;
  }

  .tour-menu-item {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 16px;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s;
  }
  .tour-menu-item:hover {
    background: var(--hifi-row-hover, rgba(255, 255, 255, 0.04));
  }
  .tour-menu-item.completed {
    opacity: 0.7;
  }

  .tour-menu-info {
    flex: 1;
    min-width: 0;
  }

  .tour-menu-title {
    font-family: 'Barlow', sans-serif;
    font-size: 13px;
    font-weight: 500;
    color: var(--hifi-text-primary, #e0e0e0);
  }

  .tour-menu-desc {
    font-size: 11px;
    color: var(--hifi-text-secondary, #888);
    margin-top: 2px;
  }

  .tour-menu-steps {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary, #888);
    flex-shrink: 0;
  }
</style>
