<script>
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { actions } from '../../lib/store.svelte.js';

  let activeCrypto = $state('btc');
  let copyFeedback = $state(null);

  const cryptos = [
    { id: 'btc', label: 'BITCOIN', symbol: 'BTC', icon: 'fa-brands fa-bitcoin', address: 'bc1qnd599khdkv3v3npmj9ufxzf6h4fzanny2acwqr', qr: '/images/btc-qr.svg' },
    { id: 'doge', label: 'DOGECOIN', symbol: 'DOGE', icon: 'fa-solid fa-dog', address: 'DL7tuiYCqm3xQjMDXChdxeQxqUGMACn1ZV', qr: '/images/doge-qr.svg' },
    { id: 'eth', label: 'ETHEREUM', symbol: 'ETH', icon: 'fa-brands fa-ethereum', address: '0x8A28fc47bFFFA03C8f685fa0836E2dBe1CA14F27', qr: '/images/eth-qr.svg' }
  ];

  async function copyAddress(address) {
    try {
      await navigator.clipboard.writeText(address);
      copyFeedback = address;
      actions.showToast('Adresse kopiert', 'success');
      setTimeout(() => { copyFeedback = null; }, 2000);
    } catch (e) {
      actions.showToast('Kopieren fehlgeschlagen', 'error');
    }
  }
</script>

<!-- Ko-fi -->
<div class="hifi-panel">
  <div class="hifi-panel-header">
    <i class="fa-solid fa-mug-hot header-icon"></i>
    <span class="hifi-font-label">RADIOHUB UNTERSTÜTZEN</span>
  </div>
  <div class="donate-section">
    <p class="donate-text">
      RadioHub ist ein nicht-kommerzielles Open-Source-Projekt.
      Wenn dir die Software gefällt, freue ich mich über eine kleine Unterstützung.
    </p>
    <a href="https://ko-fi.com/HalloWelt42" target="_blank" rel="noopener" class="kofi-btn">
      <i class="fa-solid fa-mug-hot"></i>
      <span>Unterstütze mich auf Ko-fi</span>
    </a>
  </div>
</div>

<!-- Crypto -->
<div class="hifi-panel">
  <div class="hifi-panel-header">
    <i class="fa-solid fa-coins header-icon"></i>
    <span class="hifi-font-label">KRYPTOWÄHRUNG</span>
  </div>
  <div class="crypto-section">
    <!-- Crypto Tabs -->
    <div class="crypto-tabs">
      {#each cryptos as crypto}
        <button
          class="pill-btn"
          class:active={activeCrypto === crypto.id}
          onclick={() => activeCrypto = crypto.id}
        >
          <HiFiLed color={activeCrypto === crypto.id ? 'green' : 'off'} size="small" />
          <i class={crypto.icon}></i>
          <span>{crypto.symbol}</span>
        </button>
      {/each}
    </div>

    <!-- Crypto Content -->
    {#each cryptos as crypto}
      {#if activeCrypto === crypto.id}
        <div class="crypto-content">
          <div class="crypto-qr">
            <img src={crypto.qr} alt="{crypto.symbol} QR Code" />
          </div>
          <div class="crypto-details">
            <span class="crypto-label">{crypto.label}</span>
            <code class="crypto-address">{crypto.address}</code>
            <button
              class="pill-btn copy-btn"
              onclick={() => copyAddress(crypto.address)}
            >
              <i class="fa-solid {copyFeedback === crypto.address ? 'fa-check' : 'fa-copy'}"></i>
              <span>{copyFeedback === crypto.address ? 'KOPIERT' : 'KOPIEREN'}</span>
            </button>
          </div>
        </div>
      {/if}
    {/each}
  </div>
</div>

<!-- Footer -->
<div class="donate-footer">
  <i class="fa-solid fa-heart"></i>
  Vielen Dank für deine Unterstützung!
</div>

<style>
  .header-icon {
    color: var(--hifi-accent);
    font-size: 12px;
    margin-right: 4px;
  }

  /* === Donate Section === */
  .donate-section {
    padding: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }

  .donate-text {
    font-family: var(--hifi-font-body);
    font-size: 12px;
    line-height: 1.7;
    color: var(--hifi-text-secondary);
    text-align: center;
    margin: 0;
    max-width: 400px;
  }

  .kofi-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 28px;
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
    filter: brightness(1.1);
  }

  /* === Crypto Section === */
  .crypto-section {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .crypto-tabs {
    display: flex;
    gap: 4px;
  }

  /* === Pill Button (einheitlich) === */
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

  /* === Crypto Content === */
  .crypto-content {
    display: flex;
    gap: 20px;
    align-items: center;
    padding: 16px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-md);
  }

  .crypto-qr {
    width: 120px;
    height: 120px;
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

  .crypto-details {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
    flex: 1;
  }

  .crypto-label {
    font-family: var(--hifi-font-values);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--hifi-text-primary);
  }

  .crypto-address {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 10px;
    color: var(--hifi-text-secondary);
    background: var(--hifi-bg-panel);
    padding: 6px 10px;
    border-radius: var(--hifi-border-radius-sm);
    word-break: break-all;
    line-height: 1.5;
  }

  .copy-btn {
    align-self: flex-start;
  }

  /* === Footer === */
  .donate-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 16px;
    font-family: var(--hifi-font-body);
    font-size: 11px;
    color: var(--hifi-text-secondary);
  }

  .donate-footer i {
    color: var(--hifi-led-red);
  }
</style>
