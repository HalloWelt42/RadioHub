<script lang="ts">
  // Kopf einer gewählten Aufnahme (Entwurf aufnahmen.html): Logo, Sender, Zeit, Art, Ordner, Zahlen mit Güte; Hören,
  // Schneiden, Nach Titeln teilen (nur wenn beim Aufnehmen Titelwechsel erkannt wurden und sie noch ungeteilt ist),
  // Titel als ZIP, als eine Datei, Ordner wechseln, Löschen mit Rückfrage und Folgen.
  import { Auswahl, Rueckfrage } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { datum, dauer, groesse } from "../../lib/aufnahmen/anzeige";
  import { vorzeitig, zumHoeren, type Aufnahme, type Aufnahmeordner } from "../../lib/aufnahmen";
  import Logo from "../radio/Logo.svelte";

  let { aufnahme: a, ordner, titelwechsel, zip, eineDatei, kannSchneiden, kannVerwalten, onhoeren, onschneiden, onteilen, onverschieben, onloeschen }: {
    aufnahme: Aufnahme;
    ordner: Aufnahmeordner[];
    titelwechsel: number;
    zip: string;
    eineDatei: string;
    kannSchneiden: boolean;
    kannVerwalten: boolean;
    onhoeren: () => void;
    onschneiden: () => void;
    onteilen: () => Promise<void>;
    onverschieben: (ordnerId: number | null) => void;
    onloeschen: () => Promise<void>;
  } = $props();

  let fragt = $state(false);
  let arbeitet = $state(false);
  const ordnerName = $derived(ordner.find((o) => o.id === a.ordnerId)?.name ?? t("aufnahmenAnsicht.ohneOrdner"));
  const ordnerWahl = $derived([{ wert: "", titel: t("aufnahmenAnsicht.ohneOrdner") }, ...ordner.map((o) => ({ wert: String(o.id), titel: o.name }))]);
  const guete = $derived<["rot" | "gelb" | "gruen", string]>(vorzeitig(a) ? ["rot", t(`aufnahmenAnsicht.${a.status}`)]
    : a.luecken ? ["gelb", t("aufnahmenAnsicht.luecken", { n: a.luecken })] : ["gruen", t("aufnahmenAnsicht.ohneLuecken")]);

  async function sicher(arbeit: () => Promise<void>) {
    arbeitet = true;
    try { await arbeit(); } finally { arbeitet = false; }
  }
</script>

<section class="rh-abo-kopf rh-a-kopf">
  <Logo uuid={a.senderUuid} name={a.sender} logo="" />
  <div class="rh-abo-text">
    <h2>{a.sender}</h2>
    <p class="rh-still">{datum(a.beginn)} · {a.art === "puffer" ? t("aufnahmenAnsicht.puffer") : t("aufnahmenAnsicht.direkt")} · {ordnerName}</p>
    <div class="rh-abo-zahlen">
      <span><b>{a.titelzahl}</b>{t("aufnahmenAnsicht.titelzahl")}</span><span><b>{dauer(a.dauer)}</b>{t("aufnahmenAnsicht.lang")}</span>
      <span><b>{groesse(a.groesse)}</b></span>{#if a.codec}<span><b>{a.codec}{a.bitrate ? ` ${a.bitrate}` : ""}</b>{a.bitrate ? "kbit/s" : ""}</span>{/if}
      <span class="rh-a-guete">{guete[1]}</span>
    </div>
  </div>
  <div class="rh-detail-knoepfe rh-abo-knoepfe">
    <button class="knopf primaer" type="button" disabled={!zumHoeren(a)} title={zumHoeren(a) ? undefined : t("aufnahmenAnsicht.erstBeenden")} onclick={onhoeren}><i class="fa-solid fa-play"></i>{t("aufnahmenAnsicht.hoeren")}</button>
    {#if kannSchneiden}<button class="knopf" type="button" onclick={onschneiden}><i class="fa-solid fa-scissors"></i>{t("aufnahmenAnsicht.schneiden")}</button>{/if}
    {#if kannSchneiden && a.stueckzahl <= 1 && titelwechsel > 1}
      <button class="knopf" type="button" disabled={arbeitet} title={t("aufnahmenAnsicht.teilenHilfe")} onclick={() => void sicher(onteilen)}>
        <i class="fa-solid {arbeitet ? 'fa-spinner fa-spin' : 'fa-wand-magic-sparkles'}"></i>{t("aufnahmenAnsicht.teilen", { n: titelwechsel })}</button>
    {/if}
    <a class="knopf" href={zip} download title={t("aufnahmenAnsicht.titelLadenHilfe")}><i class="fa-solid fa-file-zipper"></i>{t("aufnahmenAnsicht.titelLaden")}</a>
    <a class="knopf" href={eineDatei} download title={t("aufnahmenAnsicht.eineDateiHilfe")}><i class="fa-solid fa-download"></i>{t("aufnahmenAnsicht.eineDatei")}</a>
    {#if kannVerwalten}
      <Auswahl wert={a.ordnerId === null ? "" : String(a.ordnerId)} optionen={ordnerWahl} symbol="fa-folder-tree" titel={t("aufnahmenAnsicht.verschieben")}
               onwahl={(w: string) => onverschieben(w ? Number(w) : null)} />
      <button class="knopf" type="button" onclick={() => (fragt = true)}><i class="fa-solid fa-trash-can rh-loeschen"></i>{t("aufnahmenAnsicht.loeschen")}</button>
    {/if}
  </div>
  {#if fragt}
    <Rueckfrage frage={t("aufnahmenAnsicht.aufnahmeLoeschenFrage", { name: `${a.sender}, ${datum(a.beginn)}`, n: a.stueckzahl, mb: groesse(a.groesse) })}
                knopf={t("aufnahmenAnsicht.loeschen")} beschaeftigt={arbeitet} onabbrechen={() => (fragt = false)}
                onja={() => void sicher(async () => { await onloeschen(); fragt = false; })} />
  {/if}
</section>
