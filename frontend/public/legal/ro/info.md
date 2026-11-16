# RadioHub - Informații tehnice

Acest manual explică conceptele cheie, termenii tehnici și limitările RadioHub. Vă ajută să înțelegeți de ce anumite funcții funcționează așa cum o fac.

---

## Moduri de redare

### Modul HLS (implicit)

HLS înseamnă "HTTP Live Streaming". RadioHub convertește fluxul radio prin backend în segmente mici pe care browserul le poate reda. Acest lucru permite:

- **Timeshift:** Derulare înapoi în cadrul programului curent
- **Pauză și reluare:** Bufferul continuă în fundal
- **Înregistrare din buffer:** Înregistrarea conținutului deja ascultat (HLS-REC)
- **Control bitrate:** Adaptare automată la conexiune

Bufferul HLS este menținut în backend. Dimensiunea poate fi configurată în [Setări > General](#/setup/allgemein/einstellungen) (Buffer Timeshift).

### Modul Direct

În modul Direct, browserul se conectează direct la fluxul original al postului. Acest lucru consumă mai puține resurse, dar fără timeshift, pauză sau înregistrare din buffer. Util pentru serverele care nu suportă conversia HLS.

---

## Insigne în lista de posturi

### ICY (verde / gri)

**ICY** înseamnă "Icecast Metadata" - un protocol care permite posturilor de radio să trimită titlul curent în cadrul fluxului. Când un post suportă ICY, RadioHub afișează titlul curent și poate împărți automat înregistrările în piese individuale.

- **ICY (verde, "bun"):** Postul furnizează marcaje temporale precise ale schimbărilor de titlu. Tăierile vor fi curate.
- **ICY (verde, "slab"):** Postul furnizează date ICY, dar marcajele temporale sunt inexacte (de exemplu, raportări întârziate). Tăierile pot avea suprapuneri sau goluri.
- **ICY (gri):** ICY este prezent, dar calitatea nu a fost încă evaluată. Faceți clic pentru a comuta între "bun" și "slab".

**De ce contează?** Unele posturi raportează noul titlu abia la câteva secunde după schimbarea efectivă. RadioHub folosește pozițiile de octeți din fluxul audio pentru calculul tăierii, dar dacă postul raportează cu întârziere, tăierea va fi inexactă.

### Insigne AD (detectare reclame)

RadioHub poate verifica posturile pentru reclame. Verificarea poate fi pornită din [Setări > Radio > Posturi](#/setup/radio/sender) și analizează URL-urile fluxurilor și răspunsurile serverelor:

- **0% AD (verde):** Nicio suspiciune de reclamă după verificare
- **XX% AD (galben):** Suspiciune procentuală (de exemplu, "35% AD") - pragul este configurabil
- **AD (roșu):** Marcat manual ca reclamă (ascuns)
- **OK (albastru):** Aprobat manual în ciuda suspiciunii

---

## Sistem de înregistrare

### Înregistrare segmentată

RadioHub înregistrează în segmente de 30 de minute. Dacă conexiunea la post se întrerupe, se pierde cel mult segmentul curent - nu întreaga înregistrare. Pentru o înregistrare de 8 ore, aceasta înseamnă cel mult 30 de minute pierdute în loc de totul. Setările de înregistrare (format, bitrate, folder) se găsesc în [Setări > Înregistrări](#/setup/aufnahmen).

### Detectare blocaj

În timpul unei înregistrări, RadioHub monitorizează dimensiunea fișierului. Dacă fișierul nu crește timp de 30 de secunde, procesul de înregistrare este detectat ca "blocat" și repornit. Aceasta previne înregistrările silențioase în care FFmpeg rulează dar nu mai primește date.

### Împărțire pe titluri ICY

Dacă un post are metadate ICY, segmentele de 30 de minute sunt automat împărțite în piese individuale pe baza schimbărilor de titlu detectate după înregistrare. Fără ICY, blocurile de 30 de minute rămân ca segmente.

### Fluxuri HTTPS și reconectare

Multe posturi folosesc HTTPS. Funcția de reconectare integrată a FFmpeg funcționează fiabil doar cu fluxuri HTTP. De aceea, RadioHub gestionează singur monitorizarea și repornirea la întreruperea conexiunii, indiferent de protocol.

---

## Timeshift și buffer

### Cum funcționează timeshift?

Backendul menține un buffer rotativ de segmente audio. Fiecare segment are câteva secunde. Browserul solicită aceste segmente prin playlistul HLS. La derulare înapoi, segmentele mai vechi sunt încărcate din buffer.

### Înregistrare din buffer (HLS-REC)

Înregistrarea din buffer folosește bufferul HLS existent. Când porniți o înregistrare, RadioHub poate include ultimele X minute din buffer. Perioada de retrospectivă este configurabilă în [Setări > General](#/setup/allgemein/einstellungen) (Înregistrare HLS). Aceasta permite înregistrarea unei piese care se redă deja.

---

## Cutter (instrument de editare)

### Forma de undă

Afișajul formei de undă este calculat din datele audio (valori de vârf). Arată volumul în timp și ajută la plasarea precisă a punctelor de tăiere.

### Marcaje

Marcajele sunt puncte de tăiere în forma de undă. Pot fi setate manual sau preluate automat din schimbările de titlu ICY. La tăiere, înregistrarea este împărțită în segmente la aceste puncte.

### Analiza tranzițiilor

Analiza examinează zonele audio din jurul fiecărui marcaj. Evaluează dacă tranziția este curată (liniște între titluri) sau problematică (de exemplu, crossfade unde două titluri se suprapun). Culori: Verde = bun, Galben = de verificat, Roșu = problematic.

### Normalizare (EBU R128)

Normalizarea ajustează volumul la standardul EBU R128 - standardul european de difuzare pentru o intensitate sonoră consistentă. Astfel, toate segmentele sună la același volum, indiferent de volumul original al postului.

---

## Sistem de podcasturi

### Descărcare automată

Podcasturile abonate pot descărca automat episoade noi. Intervalul este configurabil în [Setări > Podcast](#/setup/podcast). Descărcările sunt stocate local și disponibile offline.

### Actualizare flux

Fluxurile de podcasturi sunt interogate prin RSS/Atom. [Intervalul de actualizare](#/setup/podcast) determină cât de des RadioHub verifică dacă există episoade noi.

---

## Stocare și date

În [Setări > Stocare](#/setup/speicher), căile de stocare pentru înregistrări, podcasturi și cache pot fi configurate. Afișajul arată spațiul utilizat și liber pe fiecare zonă.

Sursele externe de date (Radio-Browser API, Podcast Index) sunt vizibile în [Setări > Servicii](#/setup/dienste) și pot fi redirecționate către instanțe proprii dacă este necesar.

---

## Procese automate în fundal

RadioHub rulează mai multe procese în fundal care funcționează fără interacțiunea utilizatorului:

### Actualizare fluxuri de podcasturi

Când RadioHub pornește, se lansează un proces periodic în fundal care verifică automat toate fluxurile de podcasturi abonate pentru episoade noi. Intervalul (implicit: 6 ore) este configurabil în [Setări > Podcast](#/setup/podcast). Cu descărcarea automată activată, episoadele noi sunt descărcate automat.

### Gestionare buffer HLS

De îndată ce un post este redat în modul HLS, backendul pornește un proces FFmpeg care împarte fluxul audio în segmente scurte (1 secundă fiecare). Acestea formează un buffer rotativ de 10 minute. În paralel, rulează un logger de metadate ICY care detectează schimbările de titlu în flux. Ambele procese se opresc automat când redarea este oprită.

### Monitorizare înregistrări

În timpul unei înregistrări active, rulează două procese de monitorizare:

- **Detectare blocaj:** La fiecare 30 de secunde se verifică dacă fișierul de înregistrare crește. Trei verificări consecutive fără creștere (90 de secunde) declanșează repornirea procesului de înregistrare.
- **Monitorizare stocare:** Spațiul liber pe disc este verificat regulat. Dacă scade sub 100 MB, înregistrarea este oprită automat pentru a preveni pierderea datelor.

### Înregistrare buffer HLS (HLS-REC)

În timpul unei înregistrări buffer HLS, un proces colector copiază segmente noi din bufferul HLS în directorul de înregistrare la fiecare 0,5 secunde. La pornire, minutele de retrospectivă configurate sunt luate suplimentar din bufferul existent. La oprire, segmentele sunt automat îmbinate și împărțite în titluri individuale dacă sunt disponibile date ICY.

### Cache favicon

La încărcarea listei de posturi, pictogramele lipsă ale posturilor sunt descărcate în fundal și stocate local în cache. Acest proces rulează silențios și nu afectează interfața.

### Detectare bitrate

La prima redare a unui post, RadioHub verifică bitrateul real și codecul prin FFprobe. Rezultatul este salvat și afișat în lista de posturi. În [Setări > Radio > Posturi](#/setup/radio/sender), poate fi pornită o verificare în masă pentru toate posturile.

---

## Limitări cunoscute

- **Timeshift doar în modul HLS:** Fluxurile directe sunt transmise 1:1, fără buffer.
- **Calitatea ICY variază:** Unele posturi furnizează metadate inexacte sau întârziate. Aceasta afectează precizia tăierii.
- **Certificate SSL:** Unele posturi folosesc configurații SSL neobișnuite. RadioHub gestionează acest lucru la nevoie, dar pot apărea avertismente.
- **Înregistrări lungi:** La întreruperea conexiunii, se pierd cel mult 30 de minute (un segment). Segmentele mai vechi sunt păstrate.
- **Limitări ale browserului:** Web Audio API din browser poate furniza date pentru VU meter doar când contextul audio este activ. Unele browsere necesită interacțiune din partea utilizatorului pentru aceasta.

---

## Lectură suplimentară

Pentru cei tehnic curioși - tehnologiile și standardele din spatele RadioHub:

### Protocoale de streaming

- [HTTP Live Streaming (HLS)](https://ro.wikipedia.org/wiki/HTTP_Live_Streaming) - Protocolul de streaming adaptiv Apple folosit de RadioHub pentru timeshift
- [Icecast](https://ro.wikipedia.org/wiki/Icecast) - Server de streaming open-source care a popularizat protocolul de metadate ICY
- [SHOUTcast / Protocol ICY](https://ro.wikipedia.org/wiki/SHOUTcast) - Originea standardului de metadate ICY pentru informații despre titluri în fluxuri
- [Radio pe internet](https://ro.wikipedia.org/wiki/Radio_pe_internet) - Prezentare generală a streaming-ului radio pe internet

### Formate audio și codecuri

- [MP3 (MPEG-1 Audio Layer 3)](https://ro.wikipedia.org/wiki/MP3) - Cel mai comun format audio pentru fluxuri radio
- [AAC (Advanced Audio Coding)](https://ro.wikipedia.org/wiki/Advanced_Audio_Coding) - Codec mai modern cu calitate mai bună la aceeași rată de biți
- [Ogg Vorbis](https://ro.wikipedia.org/wiki/Vorbis) - Codec audio gratuit și deschis
- [FLAC (Free Lossless Audio Codec)](https://ro.wikipedia.org/wiki/FLAC) - Compresie fără pierderi pentru cea mai înaltă calitate

### Procesare audio

- [EBU R128](https://en.wikipedia.org/wiki/EBU_R_128) - Standard european pentru normalizarea intensității sonore în difuzare
- [FFmpeg](https://ro.wikipedia.org/wiki/FFmpeg) - Framework-ul multimedia central folosit de RadioHub pentru conversie, înregistrare și tăiere
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) - Interfață browser pentru analiza audio (VU meter, formă de undă)

### Surse de date

- [Radio-Browser API](https://www.radio-browser.info/) - Bază de date comunitară deschisă cu peste 30.000 de posturi de radio din întreaga lume
- [Podcast Index](https://podcastindex.org/) - Catalog deschis de podcasturi ca alternativă la directoarele proprietare
- [RSS (Really Simple Syndication)](https://ro.wikipedia.org/wiki/RSS) - Formatul de flux prin care podcasturile furnizează episoade noi

### Fundamente tehnice

- [Bitrate](https://ro.wikipedia.org/wiki/Bitrate) - Rata de date a unui flux audio (de exemplu, 128 kbps, 320 kbps)
- [Streaming media](https://ro.wikipedia.org/wiki/Streaming) - Fundamente ale transmisiei de date în timp real
- [Compresie audio](https://en.wikipedia.org/wiki/Audio_coding_format) - Cum funcționează compresia cu pierderi
- [SSL/TLS](https://ro.wikipedia.org/wiki/Transport_Layer_Security) - Criptarea folosită în fluxurile HTTPS
