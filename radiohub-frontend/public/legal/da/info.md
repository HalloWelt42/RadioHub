# RadioHub - Teknisk information

Denne manual forklarer de vigtigste begreber, tekniske termer og begrænsninger i RadioHub. Den hjælper dig med at forstå, hvorfor visse funktioner virker, som de gør.

---

## Afspilningstilstande

### HLS-tilstand (Standard)

HLS står for "HTTP Live Streaming". RadioHub konverterer radiostrømmen via backend til små segmenter, som browseren kan afspille. Dette muliggør:

- **Tidsforskydning:** Spol tilbage i det kørende program
- **Pause og genoptag:** Bufferen fortsætter i baggrunden
- **Bufferoptagelse:** Optag tidligere hørt indhold (HLS-REC)
- **Bitratekontrol:** Automatisk tilpasning til forbindelsen

HLS-bufferen vedligeholdes i backend. Størrelsen kan konfigureres under [Indstillinger > Generelt](#/setup/allgemein/einstellungen) (Tidsforskydningsbuffer).

### Direct-tilstand

I Direct-tilstand forbinder browseren direkte til stationens originale strøm. Dette er mere ressourceeffektivt, men uden tidsforskydning, pause eller bufferoptagelse. Nyttigt for servere, der ikke understøtter HLS-konvertering.

---

## Badges i stationslisten

### ICY (grøn / grå)

**ICY** står for "Icecast Metadata" - en protokol, der gør det muligt for radiostationer at sende den aktuelle titel i strømmen. Når en station understøtter ICY, viser RadioHub den aktuelle titel og kan automatisk opdele optagelser i individuelle sange.

- **ICY (grøn, "good"):** Stationen leverer præcise titelskift-tidsstempler. Klip vil være rene.
- **ICY (grøn, "poor"):** Stationen leverer ICY-data, men tidsstemplerne er upræcise (f.eks. forsinkede rapporter). Klip kan have overlap eller huller.
- **ICY (grå):** ICY er til stede, men kvaliteten er ikke vurderet endnu. Klik for at skifte mellem "good" og "poor".

**Hvorfor er dette vigtigt?** Nogle stationer rapporterer den nye titel først flere sekunder efter det faktiske skift. RadioHub bruger byte-positioner i lydstrømmen til klipberegning, men hvis stationen rapporterer forsinket, vil klippet være forskudt.

### AD Badges (Reklamegenkendelse)

RadioHub kan kontrollere stationer for reklamer. Kontrollen kan startes under [Setup > Radio > Stationer](#/setup/radio/sender) og analyserer stream-URL'er og serversvar:

- **0% AD (grøn):** Ingen reklamemistanke efter kontrol
- **XX% AD (gul):** Procentvis mistanke (f.eks. "35% AD") - tærskel konfigurerbar
- **AD (rød):** Manuelt markeret som reklame (skjult)
- **OK (blå):** Manuelt godkendt trods mistanke

---

## Optagelsessystem

### Segmenteret optagelse

RadioHub optager i 30-minutters segmenter. Hvis forbindelsen til stationen afbrydes, mistes højst det aktuelle segment - ikke hele optagelsen. For en 8-timers optagelse ville det være højst 30 minutter i stedet for alt. Optagelsesindstillinger (format, bitrate, mappe) under [Setup > Optagelser](#/setup/aufnahmen).

### Stallgenkendelse

Under en optagelse overvåger RadioHub filstørrelsen. Hvis filen ikke vokser i 30 sekunder, registreres optagelsesprocessen som "stalled" og genstartes. Dette forhindrer tavse optagelser, hvor FFmpeg kører, men ikke længere modtager data.

### ICY-titelopdeling

Hvis en station har ICY-metadata, opdeles 30-minutters segmenterne automatisk i individuelle sange baseret på registrerede titelskift efter optagelse. Uden ICY forbliver 30-minutters blokkene som segmenter.

### HTTPS-strømme og genforbindelse

Mange stationer bruger HTTPS. FFmpegs indbyggede genforbindelsesfunktion virker kun pålideligt med HTTP-strømme. Derfor håndterer RadioHub selv overvågning og genstart ved forbindelsesafbrydelser, uanset protokol.

---

## Tidsforskydning og buffer

### Hvordan virker tidsforskydning?

Backend vedligeholder en rullende buffer af lydsegmenter. Hvert segment er et par sekunder langt. Browseren anmoder om disse segmenter via HLS-playliste. Ved tilbagespoling indlæses ældre segmenter fra bufferen.

### Bufferoptagelse (HLS-REC)

Bufferoptagelse bruger den eksisterende HLS-buffer. Når du starter en optagelse, kan RadioHub inkludere de sidste X minutter fra bufferen. Tilbageblikkperioden kan konfigureres under [Indstillinger > Generelt](#/setup/allgemein/einstellungen) (HLS-optagelse). Dette gør det muligt at optage en sang, der allerede spiller.

---

## Cutter (Redigeringsværktøj)

### Bølgeform

Bølgeformvisningen beregnes ud fra lyddata (toppunkter). Den viser lydstyrken over tid og hjælper med præcis placering af klippepunkter.

### Markører

Markører er klippepunkter i bølgeformen. De kan sættes manuelt eller automatisk overtages fra ICY-titelskift. Ved klipning opdeles optagelsen ved disse punkter i segmenter.

### Overgangsanalyse

Analysen undersøger lydområderne omkring hver markør. Den vurderer, om overgangen er ren (stilhed mellem titler) eller problematisk (f.eks. crossfade, hvor to titler overlapper). Farver: Grøn = god, Gul = kontroller, Rød = problematisk.

### Normalisering (EBU R128)

Normalisering justerer lydstyrken til EBU R128-standarden - den europæiske udsendelsesstandard for ensartet lydstyrke. På denne måde lyder alle segmenter lige højt, uanset stationens originale lydstyrke.

---

## Podcast-system

### Auto-download

Abonnerede podcasts kan automatisk downloade nye episoder. Intervallet kan konfigureres under [Setup > Podcast](#/setup/podcast). Downloads gemmes lokalt og er tilgængelige offline.

### Feed-opdatering

Podcast-feeds hentes via RSS/Atom. [Opdateringsintervallet](#/setup/podcast) bestemmer, hvor ofte RadioHub tjekker for nye episoder.

---

## Lagring og data

Under [Setup > Lagring](#/setup/speicher) kan lagringssti for optagelser, podcasts og cache konfigureres. Visningen viser brugt og fri plads per zone.

Eksterne datakilder (Radio-Browser API, Podcast Index) er synlige under [Setup > Tjenester](#/setup/dienste) og kan omdirigeres til egne instanser om nødvendigt.

---

## Automatiske baggrundsprocesser

RadioHub kører flere processer i baggrunden, der arbejder uden brugerinteraktion:

### Podcast-feedopdatering

Når RadioHub starter, lanceres en periodisk baggrundsproces, der automatisk tjekker alle abonnerede podcast-feeds for nye episoder. Intervallet (standard: 6 timer) kan konfigureres under [Setup > Podcast](#/setup/podcast). Med auto-download aktiveret downloades nye episoder automatisk.

### HLS-bufferadministration

Så snart en station afspilles i HLS-tilstand, starter backend en FFmpeg-proces, der opdeler lydstrømmen i korte segmenter (1 sekund hver). Disse danner en rullende 10-minutters buffer. Parallelt kører en ICY-metadatalogger, der registrerer titelskift i strømmen. Begge processer afsluttes automatisk, når afspilningen stoppes.

### Optagelsesovervågning

Under en aktiv optagelse kører to overvågningsprocesser:

- **Stallgenkendelse:** Hvert 30. sekund tjekkes, om optagelsesfilen vokser. Tre på hinanden følgende tjek uden vækst (90 sekunder) udløser en genstart af optagelsesprocessen.
- **Lagerovervågning:** Fri diskplads tjekkes regelmæssigt. Hvis den falder under 100 MB, stoppes optagelsen automatisk for at forhindre datatab.

### HLS-bufferoptagelse (HLS-REC)

Under en HLS-bufferoptagelse kopierer en indsamlingsproces nye segmenter fra HLS-bufferen til optagelsesmappen hvert 0,5 sekund. Ved start tages de konfigurerede tilbageblikkminutter derudover fra den eksisterende buffer. Ved stop fusioneres segmenterne automatisk og opdeles i individuelle titler, hvis ICY-data er tilgængelige.

### Favicon-cache

Ved indlæsning af stationslisten downloades manglende stationsikoner i baggrunden og caches lokalt. Denne proces kører lydløst og påvirker ikke grænsefladen.

### Bitrateeregistrering

Ved første afspilning af en station kontrollerer RadioHub den faktiske bitrate og codec via FFprobe. Resultatet gemmes og vises i stationslisten. Under [Setup > Radio > Stationer](#/setup/radio/sender) kan en massekontrol for alle stationer startes.

---

## Kendte begrænsninger

- **Tidsforskydning kun i HLS-tilstand:** Direkte strømme sendes igennem 1:1, uden buffering.
- **ICY-kvalitet varierer:** Nogle stationer leverer upræcise eller forsinkede metadata. Dette påvirker klippræcisionen.
- **SSL-certifikater:** Nogle stationer bruger usædvanlige SSL-konfigurationer. RadioHub arbejder omkring dette om nødvendigt, men advarsler kan forekomme.
- **Lange optagelser:** Ved forbindelsesafbrydelser mistes højst 30 minutter (et segment). Ældre segmenter bevares.
- **Browserbegrænsninger:** Web Audio API i browseren kan kun levere VU-meterdata, når lydkonteksten er aktiv. Nogle browsere kræver brugerinteraktion for dette.

---

## Yderligere læsning

For de teknisk nysgerrige - teknologierne og standarderne bag RadioHub:

### Streamingprotokoller

- [HTTP Live Streaming (HLS)](https://da.wikipedia.org/wiki/HTTP_Live_Streaming) - Apples adaptive streamingprotokol brugt af RadioHub til tidsforskydning
- [Icecast](https://da.wikipedia.org/wiki/Icecast) - Open source-streamingserver, der populariserede ICY-metadataprotokollen
- [SHOUTcast / ICY-protokol](https://en.wikipedia.org/wiki/SHOUTcast) - Oprindelse af ICY-metadatastandarden for titelinformation i strømme
- [Internetradio](https://da.wikipedia.org/wiki/Internetradio) - Generelt overblik over radiostreaming på internettet

### Lydformater og codecs

- [MP3 (MPEG-1 Audio Layer 3)](https://da.wikipedia.org/wiki/MP3) - Det mest almindelige lydformat til radiostrømme
- [AAC (Advanced Audio Coding)](https://da.wikipedia.org/wiki/Advanced_Audio_Coding) - Mere moderne codec med bedre kvalitet ved samme bitrate
- [Ogg Vorbis](https://da.wikipedia.org/wiki/Vorbis) - Fri, åben lydcodec
- [FLAC (Free Lossless Audio Codec)](https://da.wikipedia.org/wiki/FLAC) - Tabsfri komprimering for højeste kvalitet

### Lydbehandling

- [EBU R128](https://en.wikipedia.org/wiki/EBU_R_128) - Europæisk standard for lydstyrkenormalisering i udsendelser
- [FFmpeg](https://da.wikipedia.org/wiki/FFmpeg) - Det centrale multimediaframework brugt af RadioHub til konvertering, optagelse og klipning
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) - Browsergrænseflade for lydanalyse (VU-meter, bølgeform)

### Datakilder

- [Radio-Browser API](https://www.radio-browser.info/) - Åben fællesskabsdatabase med over 30.000 radiostationer verden over
- [Podcast Index](https://podcastindex.org/) - Åbent podcastkatalog som alternativ til proprietære biblioteker
- [RSS (Really Simple Syndication)](https://da.wikipedia.org/wiki/RSS) - Feedformatet, hvorigennem podcasts leverer nye episoder

### Tekniske grundbegreber

- [Bitrate](https://da.wikipedia.org/wiki/Bitrate) - Datahastighed for en lydstrøm (f.eks. 128 kbps, 320 kbps)
- [Streaming media](https://da.wikipedia.org/wiki/Streaming) - Grundlæggende om realtidsdataoverførsel
- [Lydkomprimering](https://en.wikipedia.org/wiki/Audio_coding_format) - Hvordan tabsgivende komprimering fungerer
- [SSL/TLS](https://da.wikipedia.org/wiki/Transport_Layer_Security) - Kryptering brugt i HTTPS-strømme
