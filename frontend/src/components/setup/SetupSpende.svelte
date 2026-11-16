<script>
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { actions } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';

  let activeCrypto = $state(null);
  let copyFeedback = $state(null);

  const cryptos = [
    { id: 'btc', label: 'BITCOIN', symbol: 'BTC', icon: 'fa-brands fa-bitcoin', color: '#f7931a', address: 'bc1qnd599khdkv3v3npmj9ufxzf6h4fzanny2acwqr', qr: '/images/btc-qr.svg' },
    { id: 'doge', label: 'DOGECOIN', symbol: 'DOGE', icon: 'fa-solid fa-dog', color: '#c3a634', address: 'DL7tuiYCqm3xQjMDXChdxeQxqUGMACn1ZV', qr: '/images/doge-qr.svg' },
    { id: 'eth', label: 'ETHEREUM', symbol: 'ETH', icon: 'fa-brands fa-ethereum', color: '#627eea', address: '0x8A28fc47bFFFA03C8f685fa0836E2dBe1CA14F27', qr: '/images/eth-qr.svg' }
  ];

  function selectCrypto(id) {
    activeCrypto = activeCrypto === id ? null : id;
  }

  async function copyAddress(address) {
    try {
      await navigator.clipboard.writeText(address);
      copyFeedback = address;
      actions.showToast(t('spende.adresseKopiert'), 'success');
      setTimeout(() => { copyFeedback = null; }, 2000);
    } catch (e) {
      actions.showToast(t('spende.kopierenFehler'), 'error');
    }
  }
</script>

<div class="spende-page">
  <!-- Intro -->
  <div class="intro">
    <div class="intro-icon">
      <i class="fa-solid fa-heart"></i>
    </div>
    <h2 class="intro-title">{t('spende.unterstuetzen')}</h2>
    <p class="intro-text">
      {t('spende.introText')}
    </p>
  </div>

  <!-- Ko-fi -->
  <a href="https://ko-fi.com/HalloWelt42" target="_blank" rel="noopener" class="kofi-btn">
    <i class="fa-solid fa-mug-hot"></i>
    <span>{t('spende.kofiText')}</span>
  </a>

  <!-- Divider -->
  <div class="divider">
    <span class="divider-line"></span>
    <span class="divider-label">{t('spende.oderKrypto')}</span>
    <span class="divider-line"></span>
  </div>

  <!-- Crypto Cards -->
  <div class="crypto-cards">
    {#each cryptos as crypto}
      <button
        class="crypto-card"
        class:active={activeCrypto === crypto.id}
        onclick={() => selectCrypto(crypto.id)}
      >
        <div class="crypto-icon" style="--crypto-color: {crypto.color}">
          <i class={crypto.icon}></i>
        </div>
        <span class="crypto-name">{crypto.symbol}</span>
        <HiFiLed color={activeCrypto === crypto.id ? 'green' : 'off'} size="small" />
      </button>
    {/each}
  </div>

  <!-- Selected Crypto Detail -->
  {#each cryptos as crypto}
    {#if activeCrypto === crypto.id}
      <div class="crypto-detail">
        <div class="crypto-qr">
          <img src={crypto.qr} alt="{crypto.symbol} QR Code" />
        </div>
        <div class="crypto-info">
          <span class="crypto-label">{crypto.label}</span>
          <code class="crypto-address">{crypto.address}</code>
          <button
            class="copy-btn"
            onclick={() => copyAddress(crypto.address)}
          >
            <i class="fa-solid {copyFeedback === crypto.address ? 'fa-check' : 'fa-copy'}"></i>
            <span>{copyFeedback === crypto.address ? t('spende.kopiert') : t('spende.adresseKopieren')}</span>
          </button>
        </div>
      </div>
    {/if}
  {/each}

  <!-- Footer -->
  <div class="spende-footer">
    <i class="fa-solid fa-heart"></i>
    {t('spende.danke')}
  </div>
</div>

<style>
  .spende-page {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
    padding: 12px 0;
  }

  /* === Intro === */
  .intro {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    text-align: center;
    max-width: 460px;
  }

  .intro-icon {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: var(--hifi-bg-tertiary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: var(--hifi-led-red);
    box-shadow: var(--hifi-shadow-outset);
  }

  .intro-title {
    font-family: var(--hifi-font-display);
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--hifi-text-primary);
    margin: 0;
  }

  .intro-text {
    font-family: var(--hifi-font-body);
    font-size: 13px;
    line-height: 1.7;
    color: var(--hifi-text-secondary);
    margin: 0;
  }

  /* === Ko-fi Button === */
  .kofi-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 32px;
    background: var(--hifi-accent);
    border: none;
    border-radius: var(--hifi-border-radius-pill);
    color: #fff;
    font-family: var(--hifi-font-values);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.15s ease;
    box-shadow: var(--hifi-shadow-button);
  }

  .kofi-btn:hover {
    filter: brightness(1.15);
    transform: translateY(-1px);
  }

  .kofi-btn i {
    font-size: 16px;
  }

  /* === Divider === */
  .divider {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    max-width: 500px;
  }

  .divider-line {
    flex: 1;
    height: 1px;
    background: var(--hifi-border-dark);
  }

  .divider-label {
    font-family: var(--hifi-font-values);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: var(--hifi-text-muted);
    white-space: nowrap;
  }

  /* === Crypto Cards === */
  .crypto-cards {
    display: flex;
    gap: 12px;
  }

  .crypto-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 16px 28px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-md);
    cursor: pointer;
    transition: all 0.15s ease;
    box-shadow: var(--hifi-shadow-outset);
  }

  .crypto-card:hover {
    background: var(--hifi-bg-secondary);
    border-color: var(--hifi-border-light, rgba(255,255,255,0.1));
    transform: translateY(-2px);
  }

  .crypto-card.active {
    background: var(--hifi-bg-panel);
    border-color: var(--hifi-accent);
    box-shadow: var(--hifi-shadow-inset);
    transform: none;
  }

  .crypto-icon {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: var(--hifi-bg-panel);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    color: var(--crypto-color);
    transition: all 0.15s ease;
  }

  .crypto-card:hover .crypto-icon,
  .crypto-card.active .crypto-icon {
    background: var(--hifi-bg-tertiary);
  }

  .crypto-name {
    font-family: var(--hifi-font-values);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
  }

  .crypto-card.active .crypto-name {
    color: var(--hifi-text-primary);
  }

  /* === Crypto Detail === */
  .crypto-detail {
    display: flex;
    gap: 20px;
    align-items: center;
    padding: 20px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-md);
    border: 1px solid var(--hifi-border-dark);
    width: 100%;
    max-width: 500px;
  }

  .crypto-qr {
    width: 128px;
    height: 128px;
    flex-shrink: 0;
    background: #fff;
    border-radius: var(--hifi-border-radius-sm);
    padding: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .crypto-qr img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  .crypto-info {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
    flex: 1;
  }

  .crypto-label {
    font-family: var(--hifi-font-display);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--hifi-text-primary);
  }

  .crypto-address {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 10px;
    color: var(--hifi-text-secondary);
    background: var(--hifi-bg-panel);
    padding: 8px 10px;
    border-radius: var(--hifi-border-radius-sm);
    word-break: break-all;
    line-height: 1.5;
  }

  .copy-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    align-self: flex-start;
    padding: 8px 16px;
    background: var(--hifi-bg-panel);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-pill);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .copy-btn:hover {
    background: var(--hifi-bg-secondary);
    color: var(--hifi-accent);
  }

  /* === Footer === */
  .spende-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 8px 16px;
    font-family: var(--hifi-font-body);
    font-size: 11px;
    color: var(--hifi-text-secondary);
  }

  .spende-footer i {
    color: var(--hifi-led-red);
  }
</style>
