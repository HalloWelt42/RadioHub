# RadioHub - Technische Informatie

Deze handleiding legt de belangrijkste concepten, technische termen en beperkingen van RadioHub uit. Het helpt u te begrijpen waarom bepaalde functies werken zoals ze werken.

---

## Afspeelmodi

### HLS-modus (Standaard)

HLS staat voor "HTTP Live Streaming". RadioHub converteert de radiostream via de backend naar kleine segmenten die de browser kan afspelen. Dit maakt het volgende mogelijk:

- **Tijdverschuiving (Timeshift):** Terugspoelen binnen het lopende programma
- **Pauzeren en Hervatten:** De buffer gaat op de achtergrond door
- **Bufferopname:** Eerder gehoorde inhoud opnemen (HLS-REC)
- **Bitratecontrole:** Automatische aanpassing aan de verbinding

De HLS-buffer wordt in de backend onderhouden. De grootte kan worden ingesteld onder [Instellingen > Algemeen](#/setup/allgemein/einstellungen) (Tijdverschuiving-buffer).

### Directe modus

In de directe modus maakt de browser rechtstreeks verbinding met de originele stream van de zender. Dit is zuiniger met bronnen, maar zonder tijdverschuiving, pauze of bufferopname. Handig voor servers die geen HLS-conversie ondersteunen.

---

## Badges in de Zenderlijst

### ICY (groen / grijs)

**ICY** staat voor "Icecast Metadata" - een protocol waarmee radiozenders de huidige titel binnen de stream kunnen meesturen. Wanneer een zender ICY ondersteunt, toont RadioHub de huidige titel en kan opnamen automatisch in individuele nummers worden opgesplitst.

- **ICY (groen, "goed"):** De zender levert nauwkeurige tijdstempels voor titelwisselingen. De knipbewerkingen zullen schoon zijn.
- **ICY (groen, "slecht"):** De zender levert ICY-gegevens, maar de tijdstempels zijn onnauwkeurig (bijv. vertraagde meldingen). Knipbewerkingen kunnen overlappingen of hiaten hebben.
- **ICY (grijs):** ICY is aanwezig maar de kwaliteit is nog niet beoordeeld. Klik om te wisselen tussen "goed" en "slecht".

**Waarom is dit belangrijk?** Sommige zenders melden de nieuwe titel pas seconden na de daadwerkelijke wijziging. RadioHub gebruikt byteposities in de audiostream voor de knipberekening, maar als de zender te laat meldt, zal het knippunt onjuist zijn.

### AD-badges (Reclameherkenning)

RadioHub kan zenders controleren op reclame. De controle kan worden gestart onder [Setup > Radio > Zenders](#/setup/radio/sender) en analyseert stream-URLs en serverreacties:

- **0% AD (groen):** Geen reclameverdenking na controle
- **XX% AD (geel):** Percentage verdenking (bijv. "35% AD") - drempel configureerbaar
- **AD (rood):** Handmatig als reclame gemarkeerd (verborgen)
- **OK (blauw):** Handmatig goedgekeurd ondanks verdenking

---

## Opnamesysteem

### Gesegmenteerde Opname

RadioHub neemt op in segmenten van 30 minuten. Als de verbinding met de zender wegvalt, gaat hoogstens het huidige segment verloren - niet de gehele opname. Bij een opname van 8 uur is dat hoogstens 30 minuten in plaats van alles. Opname-instellingen (formaat, bitrate, map) onder [Setup > Opnamen](#/setup/aufnahmen).

### Stagnatie-detectie

Tijdens een opname bewaakt RadioHub de bestandsgrootte. Als het bestand gedurende 30 seconden niet groeit, wordt het opnameproces als "gestagneerd" gedetecteerd en herstart. Dit voorkomt stille opnamen waarbij FFmpeg draait maar geen gegevens meer ontvangt.

### ICY-titelsplitsing

Als een zender ICY-metadata heeft, worden de 30-minutensegmenten na de opname automatisch in individuele nummers gesplitst op basis van gedetecteerde titelwisselingen. Zonder ICY blijven de 30-minutenblokken als segmenten behouden.

### HTTPS-streams en Herverbinding

Veel zenders gebruiken HTTPS. De ingebouwde herverbindingsfunctie van FFmpeg werkt alleen betrouwbaar met HTTP-streams. Daarom beheert RadioHub de bewaking en herstart bij verbindingsverlies zelf, ongeacht het protocol.

---

## Tijdverschuiving en Buffer

### Hoe Werkt Tijdverschuiving?

De backend onderhoudt een roterende buffer van audiosegmenten. Elk segment is enkele seconden lang. De browser vraagt deze segmenten op via een HLS-afspeellijst. Bij terugspoelen worden oudere segmenten uit de buffer geladen.

### Bufferopname (HLS-REC)

Bufferopname maakt gebruik van de bestaande HLS-buffer. Wanneer u een opname start, kan RadioHub de laatste X minuten uit de buffer meenemen. De terugblikperiode is configureerbaar onder [Instellingen > Algemeen](#/setup/allgemein/einstellungen) (HLS-opname). Hiermee kunt u een nummer opnemen dat al speelt.

---

## Cutter (Bewerkingstool)

### Golfvorm

De golfvormweergave wordt berekend uit de audiogegevens (piekwaarden). Het toont het volume over de tijd en helpt bij het nauwkeurig plaatsen van knippunten.

### Markers

Markers zijn knippunten in de golfvorm. Ze kunnen handmatig worden geplaatst of automatisch worden overgenomen van ICY-titelwisselingen. Bij het knippen wordt de opname op deze punten in segmenten gesplitst.

### Overgangsanalyse

De analyse onderzoekt de audiogebieden rond elke marker. Het beoordeelt of de overgang schoon is (stilte tussen titels) of problematisch (bijv. crossfade waarbij twee titels overlappen). Kleuren: Groen = goed, Geel = controleren, Rood = problematisch.

### Normalisatie (EBU R128)

Normalisatie past het volume aan naar de EBU R128-standaard - de Europese omroepstandaard voor consistent volume. Zo klinken alle segmenten even hard, ongeacht het oorspronkelijke volume van de zender.

---

## Podcastsysteem

### Automatisch Downloaden

Geabonneerde podcasts kunnen automatisch nieuwe afleveringen downloaden. Het interval is configureerbaar onder [Setup > Podcast](#/setup/podcast). Downloads worden lokaal opgeslagen en zijn offline beschikbaar.

### Feed-update

Podcastfeeds worden via RSS/Atom bevraagd. Het [update-interval](#/setup/podcast) bepaalt hoe vaak RadioHub op nieuwe afleveringen controleert.

---

## Opslag en Gegevens

Onder [Setup > Opslag](#/setup/speicher) kunnen de opslagpaden voor opnamen, podcasts en cache worden ingesteld. De weergave toont gebruikt en vrij ruimte per zone.

Externe gegevensbronnen (Radio-Browser API, Podcast Index) zijn zichtbaar onder [Setup > Diensten](#/setup/dienste) en kunnen indien nodig naar eigen instanties worden omgeleid.

---

## Automatische Achtergrondprocessen

RadioHub voert verschillende processen op de achtergrond uit die zonder gebruikersinteractie werken:

### Podcast-feedupdate

Wanneer RadioHub start, wordt een periodiek achtergrondproces gestart dat automatisch alle geabonneerde podcastfeeds op nieuwe afleveringen controleert. Het interval (standaard: 6 uur) is configureerbaar onder [Setup > Podcast](#/setup/podcast). Met automatisch downloaden ingeschakeld worden nieuwe afleveringen automatisch gedownload.

### HLS-bufferbeheer

Zodra een zender in HLS-modus wordt afgespeeld, start de backend een FFmpeg-proces dat de audiostream in korte segmenten splitst (elk 1 seconde). Deze vormen een roterende 10-minutenbuffer. Tegelijkertijd draait een ICY-metadatalogger die titelwisselingen in de stream detecteert. Beide processen stoppen automatisch wanneer het afspelen wordt gestopt.

### Opnamebewaking

Tijdens een actieve opname draaien twee bewakingsprocessen:

- **Stagnatie-detectie:** Elke 30 seconden wordt gecontroleerd of het opnamebestand groeit. Drie opeenvolgende controles zonder groei (90 seconden) activeren een herstart van het opnameproces.
- **Opslagbewaking:** De vrije schijfruimte wordt regelmatig gecontroleerd. Als deze onder 100 MB daalt, wordt de opname automatisch gestopt om gegevensverlies te voorkomen.

### HLS-bufferopname (HLS-REC)

Tijdens een HLS-bufferopname kopieert een verzamelproces elke 0,5 seconde nieuwe segmenten van de HLS-buffer naar de opnamedirectory. Bij de start worden de ingestelde terugblikminuten aanvullend uit de bestaande buffer gehaald. Bij het stoppen worden segmenten automatisch samengevoegd en in individuele titels gesplitst als ICY-gegevens beschikbaar zijn.

### Favicon-cache

Bij het laden van de zenderlijst worden ontbrekende zendericonen op de achtergrond gedownload en lokaal gecacht. Dit proces draait geruisloos en heeft geen invloed op de interface.

### Bitratedetectie

Bij het voor de eerste keer afspelen van een zender controleert RadioHub de werkelijke bitrate en codec via FFprobe. Het resultaat wordt opgeslagen en weergegeven in de zenderlijst. Onder [Setup > Radio > Zenders](#/setup/radio/sender) kan een bulkcontrole voor alle zenders worden gestart.

---

## Bekende Beperkingen

- **Tijdverschuiving alleen in HLS-modus:** Directe streams worden 1:1 doorgegeven, zonder buffering.
- **ICY-kwaliteit varieert:** Sommige zenders leveren onnauwkeurige of vertraagde metadata. Dit beinvloedt de knipnauwkeurigheid.
- **SSL-certificaten:** Sommige zenders gebruiken ongebruikelijke SSL-configuraties. RadioHub werkt hier indien nodig omheen, maar waarschuwingen kunnen voorkomen.
- **Lange opnamen:** Bij verbindingsverlies gaan hoogstens 30 minuten verloren (een segment). Oudere segmenten blijven behouden.
- **Browserbeperkingen:** De Web Audio API in de browser kan alleen VU-metergegevens leveren wanneer de audiocontext actief is. Sommige browsers vereisen gebruikersinteractie hiervoor.

---

## Verder Lezen

Voor de technisch nieuwsgierigen - de technologieen en standaarden achter RadioHub:

### Streamingprotocollen

- [HTTP Live Streaming (HLS)](https://nl.wikipedia.org/wiki/HTTP_Live_Streaming) - Het adaptieve streamingprotocol van Apple dat door RadioHub wordt gebruikt voor tijdverschuiving
- [Icecast](https://nl.wikipedia.org/wiki/Icecast) - Open-source streamingserver die het ICY-metadataprotocol populair maakte
- [SHOUTcast / ICY-protocol](https://nl.wikipedia.org/wiki/SHOUTcast) - Oorsprong van de ICY-metadatastandaard voor titelinformatie in streams
- [Internetradio](https://nl.wikipedia.org/wiki/Internetradio) - Algemeen overzicht van radiostreaming op het internet

### Audioformaten en Codecs

- [MP3 (MPEG-1 Audio Layer 3)](https://nl.wikipedia.org/wiki/MP3_(audioformaat)) - Het meest voorkomende audioformaat voor radiostreams
- [AAC (Advanced Audio Coding)](https://nl.wikipedia.org/wiki/Advanced_Audio_Coding) - Modernere codec met betere kwaliteit bij dezelfde bitrate
- [Ogg Vorbis](https://nl.wikipedia.org/wiki/Vorbis) - Vrije, open audiocodec
- [FLAC (Free Lossless Audio Codec)](https://nl.wikipedia.org/wiki/FLAC) - Verliesloze compressie voor de hoogste kwaliteit

### Audioverwerking

- [EBU R128](https://en.wikipedia.org/wiki/EBU_R_128) - Europese standaard voor volumenormalisatie in de omroep
- [FFmpeg](https://nl.wikipedia.org/wiki/FFmpeg) - Het centrale multimediaframework dat door RadioHub wordt gebruikt voor conversie, opname en knippen
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) - Browserinterface voor audio-analyse (VU-meter, golfvorm)

### Gegevensbronnen

- [Radio-Browser API](https://www.radio-browser.info/) - Open communitydatabase met meer dan 30.000 radiozenders wereldwijd
- [Podcast Index](https://podcastindex.org/) - Open podcastcatalogus als alternatief voor proprietary directories
- [RSS (Really Simple Syndication)](https://nl.wikipedia.org/wiki/Really_Simple_Syndication) - Het feedformaat waarmee podcasts nieuwe afleveringen aanbieden

### Technische Grondslagen

- [Bitrate](https://nl.wikipedia.org/wiki/Bitrate) - Datasnelheid van een audiostream (bijv. 128 kbps, 320 kbps)
- [Streaming media](https://nl.wikipedia.org/wiki/Streaming_media) - Grondslagen van real-time gegevensoverdracht
- [Audiodatacompressie](https://nl.wikipedia.org/wiki/Audiocompressie_(data)) - Hoe compressie met verlies werkt
- [SSL/TLS](https://nl.wikipedia.org/wiki/Transport_Layer_Security) - Versleuteling gebruikt in HTTPS-streams
