"""Der Betrieb des RadioHub als Begleiter des Gerüsts (RAD-6): was die App beim Start, nach jedem Aufbau der Zugänge
und beim Beenden tut. Das Gerüst ruft `starten` nach Datenbank, Einstellungen, Protokoll und Zugängen, dann
`verbunden`; beim Beenden `stoppen`.

Start:
1. Einstellungen binden (Dienste lesen sie über `einstellungen.stand()`)
2. Datenbank des RadioHub auf den Stand der Stufen (`database.einrichten`; ein Bestand wird ohne Umbau übernommen) und
   für die Senderquelle öffnen; ist der Senderbestand noch nicht aufbereitet (erster Start mit Stufe 2), geschieht das
   gleich, sonst bei neuer Fassung des Bausteins als Auftrag; ohne einen einzigen Sender (frisch) startet gleich der
   Abgleich mit dem Senderverzeichnis
3. einmal: Werte der Tabelle config, die jetzt Einstellungen sind, übernehmen (`uebergang.config_uebernehmen`)
4. Ablage über den Zugang des Gerüsts zur Kellerwolke, verwaiste Aufnahmen bereinigen, Werbedomains, Podcast-Abruf
   alle `podcast_refresh_interval` Sekunden, liegengebliebene Aufnahmen nachträglich ablegen, Abgleich mit dem
   Senderverzeichnis jede Nacht zur Uhrzeit `abgleich_uhrzeit` (Auftrag `sender_abgleich`)

Was dabei geschieht, steht im Protokoll der App (Datenbank, Übertrag, Ablage, Abruf der Podcasts) und im Log.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import httpx

from appkern.app import Begleiter, Geruest

from . import ablage as ablage_paket
from . import database, einstellungen, uebergang
from .ablage import AblageEinstellungen, AblageFehler
from .config import DB_PATH, VERSION
from .services import buffer_manager, hls_buffer, podcast_service, rec_manager, timeshift_buffer
from .services.ad_detector import seed_domain_blacklist
from .services.aufnahmen import aufnahmen
from .services.empfang import empfaenge, mitschnitte_raeumen
from .services import zeitstimmen
from .services.senderquelle import abgleich, dienst as senderquelle

log = logging.getLogger("radiohub.betrieb")

ERSTER_ABRUF_S = 60


def naechster_lauf(uhrzeit: str, ab: datetime) -> datetime | None:
    """Nächster Zeitpunkt zur Uhrzeit "HH:MM" nach `ab`; None ohne Uhrzeit."""
    if not uhrzeit:
        return None
    stunde, minute = (int(x) for x in uhrzeit.split(":"))
    lauf = ab.replace(hour=stunde, minute=minute, second=0, microsecond=0)
    return lauf if lauf > ab else lauf + timedelta(days=1)


class Radiobetrieb(Begleiter):
    def __init__(self, geruest: Geruest, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """`transport` nur für Tests (Senderverzeichnis nachgestellt)."""
        self.geruest = geruest
        self.datenbank: database.Einrichtung | None = None
        self.datenbank_fehler: str | None = None      # /health meldet ihn
        self._aufgaben: list[asyncio.Task] = []
        geruest.auftraege.anmelden(*abgleich.arten(abgleich.client_fabrik(transport)))

    async def _eintragen(self, ereignis: str, text: str, stufe: str = "info") -> None:
        (log.warning if stufe != "info" else log.info)("%s: %s", ereignis, text)
        await self.geruest.protokoll.eintragen(ereignis, text, stufe=stufe)

    async def starten(self) -> None:
        einstellungen.binden(self.geruest.einstellungen)
        self.geruest.einstellungen.anbieten("zeitstimme", lambda: zeitstimmen.angebot(self.geruest.verbund))
        self.geruest.einstellungen.regel(einstellungen.regeln_pruefen)
        try:
            self.datenbank = await database.einrichten(DB_PATH)
        except Exception as f:  # noqa: BLE001 - ohne Datenbank läuft nichts; /health und Protokoll sagen es
            self.datenbank_fehler = f"{type(f).__name__}: {f}"
            await self._eintragen("radio.datenbank", f"Datenbank {DB_PATH} nicht eingerichtet: {self.datenbank_fehler}",
                                  "fehler")
            raise
        await self._eintragen("radio.datenbank", f"{DB_PATH.name}: {self.datenbank.satz()}")
        await database.oeffnen(DB_PATH)
        await self._config_uebernehmen()
        await self._senderbestand_pruefen()
        self._ablage_einrichten()
        rec_manager.startup()           # verwaiste Aufnahmen bereinigen (ihr Rest wird unten nachgeholt)
        mitschnitte_raeumen()           # Mitschnitte der Empfänge eines vorigen Laufs
        seed_domain_blacklist()         # Werbedomains der Erkennung
        aufnahmen.aufraeumen()          # alte Arbeitskopien
        self._aufgaben = [asyncio.create_task(self._podcasts_abrufen(), name="podcast-abruf"),
                          asyncio.create_task(self._liegengebliebene_ablegen(), name="aufnahmen-nachholen"),
                          asyncio.create_task(self._abgleich_planen(), name="abgleich-plan")]
        log.info("RadioHub %s gestartet, Daten in %s", VERSION, DB_PATH.parent)

    async def verbunden(self) -> None:
        """Nach jedem Aufbau der Zugänge (geänderte Kellerwolke): Ablage neu über den neuen Zugang."""
        ablage = self._ablage_einrichten()
        zustand = await ablage.zustand()
        await self._eintragen("radio.ablage", str(zustand.get("meldung") or ""),
                              "info" if zustand.get("verbunden") else "warnung")

    async def stoppen(self) -> None:
        for aufgabe in self._aufgaben:
            aufgabe.cancel()
        await asyncio.gather(*self._aufgaben, return_exceptions=True)
        self._aufgaben = []
        if rec_manager.active_session:
            await rec_manager.stop()
        await buffer_manager.stop_buffering()
        await timeshift_buffer.stop_buffering()
        await hls_buffer.stop()
        await empfaenge.alle_beenden()
        await podcast_service.close()
        await ablage_paket.ablage().schliessen()
        await database.schliessen()
        einstellungen.binden(None)
        log.info("RadioHub %s gestoppt", VERSION)

    # --- Teile ----------------------------------------------------------------------------------------------------

    def _ablage_einrichten(self):
        return ablage_paket.starten(self.geruest.kellerwolke, AblageEinstellungen.aus(einstellungen.stand()))

    async def _config_uebernehmen(self) -> None:
        """Je Übertrag einmal: Werte der Tabelle config, die jetzt Einstellungen sind; danach merkt sich das Gerüst den
        Übertrag (Baustein in appkern_schema). Ein neuer Übertrag (RAD-11) läuft auch dort, wo der erste schon lief."""
        db = self.geruest.db
        for baustein, felder in einstellungen.UEBERTRAEGE:
            if await db.zeile("SELECT stufe FROM appkern_schema WHERE baustein=?", (baustein,)):
                continue
            uebernommen, uebergangen = await uebergang.config_uebernehmen(self.geruest.einstellungen, DB_PATH, felder)
            if uebernommen:
                await self._eintragen("radio.uebertrag", f"Aus der Tabelle config in die Einstellungen: {', '.join(uebernommen)}")
            for grund in uebergangen:
                await self._eintragen("radio.uebertrag", f"Nicht übernommen, es gilt die Vorgabe: {grund}", "warnung")
            await db.einrichten(baustein, [""])

    async def _senderbestand_pruefen(self) -> None:
        """Erster Start mit Stufe 2: Bestand gleich aufbereiten (ohne ihn kennt die Senderquelle keinen Sender). Eine
        neue Fassung des Bausteins oder ein abweichender Bestand: Auftrag, die bisherige Aufbereitung gilt so lange."""
        if await senderquelle.ohne_sender():
            self._aufgaben.append(asyncio.create_task(self._einreihen(abgleich.ART, "start"), name="erster-abgleich"))
            return
        grund = await senderquelle.aufbereitung_noetig()
        if grund == "leer":
            anzahl = await senderquelle.aufbereiten()
            await self._eintragen("radio.senderquelle", f"Senderbestand erstmals aufbereitet: {anzahl} Sender")
        elif grund:
            self._aufgaben.append(asyncio.create_task(self._einreihen(abgleich.ART_AUFBEREITEN, "start"),
                                                      name="aufbereiten"))

    async def _einreihen(self, art: str, anlass: str) -> None:
        await self.geruest.auftraege.gestartet.wait()
        eingabe = {"anlass": anlass} if art == abgleich.ART else None
        await self.geruest.auftraege.einreihen(art, eingabe, von="Zeitplan" if anlass == "zeitplan" else "RadioHub")

    async def _abgleich_planen(self) -> None:
        """Jede Nacht zur Uhrzeit der Einstellung abgleich_uhrzeit (leer: nie); eine geänderte Uhrzeit gilt ohne
        Neustart."""
        gemerkt, naechster = None, None
        while True:
            uhrzeit = einstellungen.stand().abgleich_uhrzeit
            if uhrzeit != gemerkt:
                gemerkt, naechster = uhrzeit, naechster_lauf(uhrzeit, datetime.now())
            if naechster and datetime.now() >= naechster:
                try:
                    await self._einreihen(abgleich.ART, "zeitplan")
                except Exception as f:  # noqa: BLE001 - der nächste Tag versucht es wieder
                    await self._eintragen("radio.abgleich", f"Abgleich nicht eingereiht: {f}", "warnung")
                naechster = naechster_lauf(uhrzeit, datetime.now() + timedelta(minutes=1))
            await asyncio.sleep(30)

    async def _podcasts_abrufen(self) -> None:
        """Abruf der Feeds aller Abos im eingestellten Abstand (erster Abruf eine Minute nach dem Start)."""
        podcast_service.set_next_refresh(datetime.now() + timedelta(seconds=ERSTER_ABRUF_S))
        await asyncio.sleep(ERSTER_ABRUF_S)
        while True:
            if podcast_service.auto_refresh_enabled:
                try:
                    ergebnis = await podcast_service.refresh_all()
                    await self._eintragen("radio.podcasts", f"{ergebnis.get('refreshed', 0)} von {ergebnis.get('total', 0)} "
                                          f"Feeds abgerufen, {ergebnis.get('new_episodes', 0)} neue Folgen")
                except Exception as f:  # noqa: BLE001 - der nächste Abruf versucht es wieder
                    await self._eintragen("radio.podcasts", f"Abruf fehlgeschlagen: {f}", "warnung")
            podcast_service.reset_refresh_timer()
            await asyncio.sleep(podcast_service.refresh_interval)

    async def _liegengebliebene_ablegen(self) -> None:
        """Aufnahmen, die ein Neustart oder eine fehlende Ablage im Arbeitsordner gelassen hat, nachträglich ablegen."""
        try:
            anzahl = await aufnahmen.liegengebliebene_ablegen()
            if anzahl:
                await self._eintragen("radio.ablage", f"{anzahl} liegengebliebene Stücke nachträglich abgelegt")
        except AblageFehler as f:
            await self._eintragen("radio.ablage", f"Nachholen nicht möglich: {f}", "warnung")
