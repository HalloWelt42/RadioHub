# RadioHub - Technické informace

Tato příručka vysvětluje klíčové koncepty, odborné pojmy a omezení RadioHubu. Pomůže vám pochopit, proč některé funkce fungují tak, jak fungují.

---

## Režimy přehrávání

### Režim HLS (výchozí)

HLS znamená "HTTP Live Streaming". RadioHub převádí rozhlasový stream přes backend na malé segmenty, které může prohlížeč přehrávat. To umožňuje:

- **Časový posun:** Přetáčení zpět v rámci běžícího programu
- **Pozastavení a pokračování:** Buffer pokračuje na pozadí
- **Nahrávání z bufferu:** Nahrávání dříve poslechnutého obsahu (HLS-REC)
- **Řízení bitrate:** Automatické přizpůsobení připojení

HLS buffer je spravován v backendu. Velikost lze nastavit v [Nastavení > Obecné](#/setup/allgemein/einstellungen) (Vyrovnávací paměť).

### Přímý režim

V přímém režimu se prohlížeč připojuje přímo k původnímu streamu stanice. To je úspornější na zdroje, ale bez časového posunu, pozastavení nebo nahrávání z bufferu. Užitečné pro servery, které nepodporují konverzi HLS.

---

## Odznaky v seznamu stanic

### ICY (zelený / šedý)

**ICY** znamená "Icecast Metadata" - protokol, který umožňuje rádiovým stanicím odesílat aktuální název v rámci streamu. Když stanice podporuje ICY, RadioHub zobrazuje aktuální název a může automaticky rozdělit nahrávky na jednotlivé skladby.

- **ICY (zelený, "dobrý"):** Stanice poskytuje přesné časové značky změn titulů. Střihy budou čisté.
- **ICY (zelený, "špatný"):** Stanice poskytuje ICY data, ale časové značky jsou nepřesné (např. zpožděné hlášení). Střihy mohou mít překryvy nebo mezery.
- **ICY (šedý):** ICY je přítomno, ale kvalita dosud nebyla hodnocena. Kliknutím přepínáte mezi "dobrý" a "špatný".

**Proč je to důležité?** Některé stanice hlásí nový titul teprve sekundy po skutečné změně. RadioHub používá pozice bajtů v audio streamu pro výpočet střihu, ale pokud stanice hlásí pozdě, střih bude nepřesný.

### Odznaky AD (detekce reklam)

RadioHub může kontrolovat stanice na reklamy. Kontrola se spouští v [Setup > Rádio > Stanice](#/setup/radio/sender) a analyzuje URL streamu a odpovědi serveru:

- **0% AD (zelený):** Žádné podezření na reklamu po kontrole
- **XX% AD (žlutý):** Procentuální podezření (např. "35% AD") - práh je konfigurovatelný
- **AD (červený):** Ručně označeno jako reklama (skryto)
- **OK (modrý):** Ručně schváleno navzdory podezření

---

## Nahrávací systém

### Segmentované nahrávání

RadioHub nahrává v 30minutových segmentech. Pokud dojde k přerušení spojení se stanicí, ztratí se nanejvýš aktuální segment - ne celá nahrávka. U 8hodinové nahrávky to znamená nanejvýš 30 minut místo všeho. Nastavení nahrávání (formát, bitrate, složka) najdete v [Setup > Nahrávky](#/setup/aufnahmen).

### Detekce zablokování

Během nahrávání RadioHub sleduje velikost souboru. Pokud soubor neroste 30 sekund, nahrávací proces je detekován jako "zablokovaný" a restartován. Tím se předchází tichým nahrávkám, kde FFmpeg běží, ale již nepřijímá data.

### ICY rozdělení podle titulů

Pokud stanice má ICY metadata, 30minutové segmenty se po nahrávání automaticky rozdělí na jednotlivé skladby na základě detekovaných změn titulů. Bez ICY zůstávají 30minutové bloky jako segmenty.

### HTTPS streamy a opětovné připojení

Mnoho stanic používá HTTPS. Vestavěná funkce opětovného připojení ve FFmpeg funguje spolehlivě pouze s HTTP streamy. Proto RadioHub sám zajišťuje monitorování a restart při přerušení spojení, bez ohledu na protokol.

---

## Časový posun a buffer

### Jak funguje časový posun?

Backend udržuje rotující buffer audio segmentů. Každý segment je dlouhý několik sekund. Prohlížeč požaduje tyto segmenty přes HLS playlist. Při přetáčení zpět se načítají starší segmenty z bufferu.

### Nahrávání z bufferu (HLS-REC)

Nahrávání z bufferu využívá existující HLS buffer. Když spustíte nahrávání, RadioHub může zahrnout posledních X minut z bufferu. Doba zpětného pohledu je konfigurovatelná v [Nastavení > Obecné](#/setup/allgemein/einstellungen) (Nahrávání HLS). To umožňuje nahrát skladbu, která již hraje.

---

## Cutter (nástroj pro střih)

### Průběh vlny

Zobrazení průběhu vlny se vypočítává z audio dat (špičkové hodnoty). Ukazuje hlasitost v čase a pomáhá s přesným umístěním bodů střihu.

### Markery

Markery jsou body střihu v průběhu vlny. Lze je nastavit ručně nebo automaticky převzít ze změn titulů ICY. Při střihu se nahrávka rozdělí v těchto bodech na segmenty.

### Analýza přechodů

Analýza zkoumá audio oblasti kolem každého markeru. Hodnotí, zda je přechod čistý (ticho mezi tituly) nebo problematický (např. prolínání, kde se dva tituly překrývají). Barvy: Zelená = dobrý, Žlutá = zkontrolovat, Červená = problematický.

### Normalizace (EBU R128)

Normalizace přizpůsobuje hlasitost standardu EBU R128 - evropskému vysílacímu standardu pro konzistentní hlasitost. Díky tomu znějí všechny segmenty stejně hlasitě, bez ohledu na původní hlasitost stanice.

---

## Podcastový systém

### Automatické stahování

Odebírané podcasty mohou automaticky stahovat nové epizody. Interval je konfigurovatelný v [Setup > Podcast](#/setup/podcast). Stažené soubory jsou uloženy lokálně a dostupné offline.

### Aktualizace kanálu

Podcastové kanály jsou dotazovány přes RSS/Atom. [Interval aktualizace](#/setup/podcast) určuje, jak často RadioHub kontroluje nové epizody.

---

## Úložiště a data

V [Setup > Úložiště](#/setup/speicher) lze nastavit cesty úložiště pro nahrávky, podcasty a cache. Zobrazení ukazuje obsazený a volný prostor na zónu.

Externí zdroje dat (Radio-Browser API, Podcast Index) jsou viditelné v [Setup > Služby](#/setup/dienste) a v případě potřeby je lze přesměrovat na vlastní instance.

---

## Automatické procesy na pozadí

RadioHub provozuje několik procesů na pozadí, které fungují bez interakce uživatele:

### Aktualizace podcastových kanálů

Při spuštění RadioHubu se spouští periodický proces na pozadí, který automaticky kontroluje všechny odebírané podcastové kanály na nové epizody. Interval (výchozí: 6 hodin) je konfigurovatelný v [Setup > Podcast](#/setup/podcast). S aktivním automatickým stahováním se nové epizody stahují automaticky.

### Správa HLS bufferu

Jakmile je stanice přehrávána v režimu HLS, backend spustí FFmpeg proces, který rozděluje audio stream na krátké segmenty (1 sekunda). Ty tvoří rotující 10minutový buffer. Paralelně běží ICY metadata logger, který detekuje změny titulů ve streamu. Oba procesy se automaticky ukončí při zastavení přehrávání.

### Monitorování nahrávání

Během aktivního nahrávání běží dva monitorovací procesy:

- **Detekce zablokování:** Každých 30 sekund se kontroluje, zda nahrávací soubor roste. Tři po sobě jdoucí kontroly bez růstu (90 sekund) spustí restart nahrávacího procesu.
- **Monitorování úložiště:** Pravidelně se kontroluje volné místo na disku. Pokud klesne pod 100 MB, nahrávání se automaticky zastaví, aby se zabránilo ztrátě dat.

### Nahrávání z HLS bufferu (HLS-REC)

Během nahrávání z HLS bufferu kopíruje sběrný proces nové segmenty z HLS bufferu do adresáře nahrávání každých 0,5 sekundy. Na začátku se z existujícího bufferu navíc převezmou konfigurované minuty zpětného pohledu. Při zastavení se segmenty automaticky sloučí a rozdělí na jednotlivé tituly, pokud jsou k dispozici ICY data.

### Favicon cache

Při načítání seznamu stanic se chybějící ikony stanic stahují na pozadí a ukládají lokálně do cache. Tento proces běží tiše a neovlivňuje rozhraní.

### Detekce bitrate

Při prvním přehrávání stanice RadioHub zjistí skutečný bitrate a kodek pomocí FFprobe. Výsledek je uložen a zobrazen v seznamu stanic. V [Setup > Rádio > Stanice](#/setup/radio/sender) lze spustit hromadnou kontrolu pro všechny stanice.

---

## Známá omezení

- **Časový posun pouze v režimu HLS:** Přímé streamy se předávají 1:1, bez bufferování.
- **Kvalita ICY se liší:** Některé stanice dodávají nepřesná nebo zpožděná metadata. To ovlivňuje přesnost střihu.
- **SSL certifikáty:** Některé stanice používají neobvyklé konfigurace SSL. RadioHub to v případě potřeby obchází, ale mohou se objevit varování.
- **Dlouhé nahrávky:** Při přerušení spojení se ztratí nanejvýš 30 minut (jeden segment). Starší segmenty zůstávají zachovány.
- **Omezení prohlížeče:** Web Audio API v prohlížeči může poskytovat data pro VU metr pouze tehdy, když je audio kontext aktivní. Některé prohlížeče vyžadují pro toto interakci uživatele.

---

## Další čtení

Pro technicky zvídavé - technologie a standardy za RadioHubem:

### Streamovací protokoly

- [HTTP Live Streaming (HLS)](https://cs.wikipedia.org/wiki/HTTP_Live_Streaming) - Adaptivní streamovací protokol od Apple používaný RadioHubem pro časový posun
- [Icecast](https://cs.wikipedia.org/wiki/Icecast) - Open-source streamovací server, který popularizoval protokol ICY metadata
- [SHOUTcast / ICY protokol](https://cs.wikipedia.org/wiki/SHOUTcast) - Původ standardu ICY metadata pro informace o titulech ve streamech
- [Internetové rádio](https://cs.wikipedia.org/wiki/Internetov%C3%A9_r%C3%A1dio) - Obecný přehled rádiového streamování na internetu

### Audio formáty a kodeky

- [MP3 (MPEG-1 Audio Layer 3)](https://cs.wikipedia.org/wiki/MP3) - Nejběžnější audio formát pro rádiové streamy
- [AAC (Advanced Audio Coding)](https://cs.wikipedia.org/wiki/Advanced_Audio_Coding) - Modernější kodek s lepší kvalitou při stejném bitrate
- [Ogg Vorbis](https://cs.wikipedia.org/wiki/Vorbis) - Svobodný, otevřený audio kodek
- [FLAC (Free Lossless Audio Codec)](https://cs.wikipedia.org/wiki/FLAC) - Bezztrátová komprese pro nejvyšší kvalitu

### Zpracování zvuku

- [EBU R128](https://en.wikipedia.org/wiki/EBU_R_128) - Evropský standard pro normalizaci hlasitosti ve vysílání
- [FFmpeg](https://cs.wikipedia.org/wiki/FFmpeg) - Centrální multimediální framework používaný RadioHubem pro konverzi, nahrávání a střih
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) - Rozhraní prohlížeče pro analýzu zvuku (VU metr, průběh vlny)

### Datové zdroje

- [Radio-Browser API](https://www.radio-browser.info/) - Otevřená komunitní databáze s více než 30 000 rádiovými stanicemi po celém světě
- [Podcast Index](https://podcastindex.org/) - Otevřený podcastový katalog jako alternativa k proprietárním adresářům
- [RSS (Really Simple Syndication)](https://cs.wikipedia.org/wiki/RSS) - Formát kanálu, přes který podcasty poskytují nové epizody

### Technické základy

- [Bitrate](https://cs.wikipedia.org/wiki/Datov%C3%BD_tok) - Datový tok audio streamu (např. 128 kbps, 320 kbps)
- [Streamování médií](https://cs.wikipedia.org/wiki/Streamov%C3%A1n%C3%AD) - Základy přenosu dat v reálném čase
- [Komprese audio dat](https://cs.wikipedia.org/wiki/Ztr%C3%A1tov%C3%A1_komprese) - Jak funguje ztrátová komprese
- [SSL/TLS](https://cs.wikipedia.org/wiki/Transport_Layer_Security) - Šifrování používané v HTTPS streamech
