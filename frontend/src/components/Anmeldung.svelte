<script>
  // Anmeldung mit dem Konto der Kellerwolke (RAD-6): Passwort, Koppeln mit einem Code (Telefon, Web-App vom
  // Startbildschirm, bleibt angemeldet, bis man das Gerät in der Kellerwolke trennt) oder, solange keine Kellerwolke
  // eingetragen ist, die erste Einrichtung. Übergangsweise bis zur Schale des Appkerns in Teil 2c.
  import {
    CODE_LAENGE, anmelden, codeAusLinkNehmen, codeNormal, einrichten, geraeteArt, koppeln, namensvorschlag, sitzung, starten
  } from '../lib/sitzung.svelte.js';

  const ausLink = codeAusLinkNehmen();
  const app = $derived(sitzung.app);
  // am Telefon als Web-App ist Koppeln der übliche Weg
  let modus = $state(ausLink || geraeteArt() === 'webapp' ? 'code' : 'passwort');
  let kennung = $state('');
  let passwort = $state('');
  let code = $state(ausLink);
  let name = $state(namensvorschlag());
  let adresse = $state('');
  let schluessel = $state('');
  let einrichtungscode = $state('');
  let fehler = $state('');
  let laeuft = $state(false);

  async function los(e, arbeit) {
    e.preventDefault();
    fehler = '';
    laeuft = true;
    try {
      await arbeit();
    } catch (f) {
      fehler = f.message;
    } finally {
      laeuft = false;
    }
  }
</script>

<div class="anmeldung">
  {#if sitzung.fehler}
    <div class="karte">
      <h1><i class="fa-solid fa-radio"></i> RadioHub</h1>
      <p class="fehler">{sitzung.fehler}</p>
      <button class="hifi-btn hifi-btn-primary" type="button" onclick={starten}>Erneut versuchen</button>
    </div>
  {:else if app?.einrichtung_noetig}
    <form class="karte" onsubmit={(e) => los(e, () => einrichten(adresse.trim(), schluessel.trim(), einrichtungscode.trim()))}>
      <h1><i class="fa-solid fa-radio"></i> {app.name} einrichten</h1>
      <p class="hinweis">Adresse der Kellerwolke und ein App-Schlüssel für RadioHub (in der Kellerwolke unter
        Einstellungen, Zugänge). Dem Konto des Schlüssels gehört RadioHub; nur dieses Konto meldet sich danach an.</p>
      <label>Kellerwolke<input bind:value={adresse} placeholder="https://rechner:39280" autocomplete="off" /></label>
      <label>App-Schlüssel<input bind:value={schluessel} type="password" autocomplete="off" /></label>
      {#if app.einrichtungscode}
        <label>Einrichtungscode<input bind:value={einrichtungscode} autocomplete="one-time-code" /></label>
        <p class="hinweis">Der Code steht am Rechner von RadioHub in {app.einrichtungscode}.</p>
      {/if}
      {#if fehler}<p class="fehler">{fehler}</p>{/if}
      <button class="hifi-btn hifi-btn-primary" type="submit" disabled={laeuft || !adresse || !schluessel}>
        {laeuft ? 'Einrichten ...' : 'Einrichten'}
      </button>
    </form>
  {:else if modus === 'passwort'}
    <form class="karte" onsubmit={(e) => los(e, () => anmelden(kennung.trim(), passwort))}>
      <h1><i class="fa-solid fa-radio"></i> {app?.name ?? 'RadioHub'}</h1>
      <p class="hinweis">Anmelden mit dem Konto der Kellerwolke unter <b>{app?.kellerwolke}</b>.
        {#if app?.besitzer}RadioHub gehört dem Konto <b>{app.besitzer}</b>.{/if}</p>
      <label>Name oder Kürzel<input bind:value={kennung} autocomplete="username" /></label>
      <label>Passwort<input bind:value={passwort} type="password" autocomplete="current-password" /></label>
      {#if fehler}<p class="fehler">{fehler}</p>{/if}
      <button class="hifi-btn hifi-btn-primary" type="submit" disabled={laeuft || !kennung || !passwort}>
        {laeuft ? 'Anmelden ...' : 'Anmelden'}
      </button>
      <button class="hifi-btn" type="button" onclick={() => ((modus = 'code'), (fehler = ''))}>
        <i class="fa-solid fa-link"></i> Mit Code koppeln
      </button>
    </form>
  {:else}
    <form class="karte" onsubmit={(e) => los(e, () => koppeln(code, name.trim(), geraeteArt()))}>
      <h1><i class="fa-solid fa-link"></i> Gerät koppeln</h1>
      <p class="hinweis">Den Code zeigt die Kellerwolke unter <b>{app?.kellerwolke}</b> (Einstellungen, Geräte); ein Code
        aus einer anderen Kellerwolke gilt hier nicht. Danach bleibt dieses Gerät angemeldet, bis du es dort trennst;
        ein Passwort wird hier nicht gespeichert. Am iPhone einmal in der Web-App vom Startbildschirm koppeln.</p>
      <label>Code<input value={code} maxlength={CODE_LAENGE + 2} autocomplete="one-time-code" autocapitalize="characters"
                        spellcheck="false" oninput={(e) => { code = codeNormal(e.currentTarget.value); e.currentTarget.value = code; }} /></label>
      <label>Name des Geräts<input bind:value={name} maxlength="60" /></label>
      {#if fehler}<p class="fehler">{fehler}</p>{/if}
      <button class="hifi-btn hifi-btn-primary" type="submit" disabled={laeuft || code.length !== CODE_LAENGE || !name.trim()}>
        {laeuft ? 'Koppeln ...' : 'Koppeln'}
      </button>
      <button class="hifi-btn" type="button" onclick={() => ((modus = 'passwort'), (fehler = ''))}>
        Mit Passwort anmelden
      </button>
    </form>
  {/if}
</div>

<style>
  .anmeldung {
    min-height: 100dvh;
    display: grid;
    place-items: center;
    padding: 16px;
    background: var(--hifi-bg-primary);
    color: var(--hifi-text-primary);
    font-family: var(--hifi-font-family);
  }

  .karte {
    width: min(420px, 100%);
    display: grid;
    gap: 14px;
    padding: 24px;
    border-radius: var(--hifi-border-radius-md);
    background: var(--hifi-bg-panel);
    box-shadow: var(--hifi-shadow-raised);
  }

  h1 {
    margin: 0;
    font-size: var(--hifi-font-size-xl);
    display: flex;
    gap: 10px;
    align-items: center;
  }

  label {
    display: grid;
    gap: 6px;
    font-size: var(--hifi-font-size-lg);
    color: var(--hifi-text-label);
  }

  /* mindestens 16 px, sonst vergrößert das iPhone beim Tippen */
  input {
    font: inherit;
    font-size: var(--hifi-font-size-lg);
    padding: 10px 12px;
    border-radius: var(--hifi-border-radius-sm);
    border: 1px solid var(--hifi-border-dark);
    background: var(--hifi-bg-secondary);
    color: var(--hifi-text-value);
    box-shadow: var(--hifi-shadow-inset);
  }

  .hinweis {
    margin: 0;
    font-size: var(--hifi-font-size-lg);
    color: var(--hifi-text-secondary);
    line-height: 1.4;
  }

  .fehler {
    margin: 0;
    font-size: var(--hifi-font-size-lg);
    color: var(--hifi-led-red);
  }

  .hifi-btn {
    font-size: var(--hifi-font-size-lg);
  }
</style>
