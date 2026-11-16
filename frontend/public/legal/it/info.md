# RadioHub - Informazioni tecniche

Questo manuale spiega i concetti chiave, i termini tecnici e le limitazioni di RadioHub. Vi aiuta a capire perché certe funzionalità funzionano nel modo in cui funzionano.

---

## Modalità di riproduzione

### Modalità HLS (predefinita)

HLS sta per "HTTP Live Streaming". RadioHub converte il flusso radio tramite il backend in piccoli segmenti che il browser può riprodurre. Questo permette:

- **Differita:** Riavvolgere all'interno del programma in corso
- **Pausa e ripresa:** Il buffer continua in sottofondo
- **Registrazione del buffer:** Registrare contenuto già ascoltato (HLS-REC)
- **Controllo del bitrate:** Adattamento automatico alla connessione

Il buffer HLS viene gestito nel backend. La dimensione può essere configurata in [Impostazioni > Generale](#/setup/allgemein/einstellungen) (Buffer differita).

### Modalità Direct

In modalità Direct, il browser si collega direttamente al flusso originale della stazione. Questo è più efficiente in termini di risorse ma senza differita, pausa o registrazione del buffer. Utile per i server che non supportano la conversione HLS.

---

## Badge nella lista delle stazioni

### ICY (verde / grigio)

**ICY** sta per "Icecast Metadata" - un protocollo che permette alle stazioni radio di inviare il titolo corrente all'interno del flusso. Quando una stazione supporta ICY, RadioHub visualizza il titolo attuale e può dividere automaticamente le registrazioni in brani individuali.

- **ICY (verde, "good"):** La stazione fornisce marcature temporali precise per i cambi di titolo. I tagli saranno puliti.
- **ICY (verde, "poor"):** La stazione fornisce dati ICY, ma le marcature temporali sono imprecise (ad es. segnalazione in ritardo). I tagli possono avere sovrapposizioni o lacune.
- **ICY (grigio):** ICY è presente ma la qualità non è ancora stata valutata. Fai clic per alternare tra "good" e "poor".

**Perché è importante?** Alcune stazioni segnalano il nuovo titolo solo alcuni secondi dopo il cambio effettivo. RadioHub utilizza le posizioni in byte nel flusso audio per il calcolo dei tagli, ma se la stazione segnala in ritardo, il taglio sarà sfasato.

### Badge AD (rilevamento pubblicità)

RadioHub può verificare le stazioni per la pubblicità. La verifica può essere avviata in [Setup > Radio > Stazioni](#/setup/radio/sender) e analizza gli URL dei flussi e le risposte del server:

- **0% AD (verde):** Nessun sospetto di pubblicità dopo la verifica
- **XX% AD (giallo):** Percentuale di sospetto (ad es. "35% AD") - soglia configurabile
- **AD (rosso):** Contrassegnato manualmente come pubblicità (nascosto)
- **OK (blu):** Approvato manualmente nonostante il sospetto

---

## Sistema di registrazione

### Registrazione segmentata

RadioHub registra in segmenti di 30 minuti. Se la connessione alla stazione si interrompe, al massimo il segmento corrente viene perso - non l'intera registrazione. Per una registrazione di 8 ore, sarebbero al massimo 30 minuti invece di tutto. Le impostazioni di registrazione (formato, bitrate, cartella) si trovano in [Setup > Registrazioni](#/setup/aufnahmen).

### Rilevamento di blocco

Durante una registrazione, RadioHub monitora la dimensione del file. Se il file non cresce per 30 secondi, il processo di registrazione viene rilevato come "bloccato" e riavviato. Questo previene registrazioni silenziose dove FFmpeg è in esecuzione ma non riceve più dati.

### Divisione per titolo ICY

Se una stazione ha metadati ICY, i segmenti di 30 minuti vengono automaticamente divisi in brani individuali basandosi sui cambi di titolo rilevati dopo la registrazione. Senza ICY, i blocchi di 30 minuti rimangono come segmenti.

### Flussi HTTPS e riconnessione

Molte stazioni utilizzano HTTPS. La funzione di riconnessione integrata di FFmpeg funziona in modo affidabile solo con flussi HTTP. Per questo motivo, RadioHub gestisce autonomamente il monitoraggio e il riavvio in caso di perdita di connessione, indipendentemente dal protocollo.

---

## Differita e buffer

### Come funziona la differita?

Il backend mantiene un buffer rotante di segmenti audio. Ogni segmento dura alcuni secondi. Il browser richiede questi segmenti tramite la playlist HLS. Quando si riavvolge, vengono caricati segmenti più vecchi dal buffer.

### Registrazione del buffer (HLS-REC)

La registrazione del buffer utilizza il buffer HLS esistente. Quando si avvia una registrazione, RadioHub può includere gli ultimi X minuti dal buffer. Il periodo di retrospettiva è configurabile in [Impostazioni > Generale](#/setup/allgemein/einstellungen) (Registrazione HLS). Questo permette di registrare un brano già in riproduzione.

---

## Cutter (strumento di montaggio)

### Forma d'onda

La visualizzazione della forma d'onda viene calcolata dai dati audio (valori di picco). Mostra il volume nel tempo e aiuta nel posizionamento preciso dei punti di taglio.

### Marcatori

I marcatori sono punti di taglio nella forma d'onda. Possono essere impostati manualmente o automaticamente dai cambi di titolo ICY. Durante il taglio, la registrazione viene divisa in questi punti in segmenti.

### Analisi delle transizioni

L'analisi esamina le zone audio intorno a ciascun marcatore. Valuta se la transizione è pulita (silenzio tra i titoli) o problematica (ad es. dissolvenza incrociata dove due titoli si sovrappongono). Colori: Verde = buono, Giallo = da verificare, Rosso = problematico.

### Normalizzazione (EBU R128)

La normalizzazione regola il volume secondo lo standard EBU R128 - lo standard europeo di diffusione per una sonorità consistente. In questo modo tutti i segmenti suonano ugualmente forte, indipendentemente dal volume originale della stazione.

---

## Sistema podcast

### Download automatico

I podcast sottoscritti possono scaricare automaticamente i nuovi episodi. L'intervallo è configurabile in [Setup > Podcast](#/setup/podcast). I download vengono archiviati localmente e sono disponibili offline.

### Aggiornamento dei feed

I feed dei podcast vengono interrogati via RSS/Atom. L'[intervallo di aggiornamento](#/setup/podcast) determina con quale frequenza RadioHub controlla la presenza di nuovi episodi.

---

## Archiviazione e dati

In [Setup > Archiviazione](#/setup/speicher), è possibile configurare i percorsi di archiviazione per registrazioni, podcast e cache. Il display mostra lo spazio utilizzato e libero per zona.

Le fonti di dati esterne (API Radio-Browser, Podcast Index) sono visibili in [Setup > Servizi](#/setup/dienste) e possono essere reindirizzate alle proprie istanze se necessario.

---

## Processi automatici in sottofondo

RadioHub esegue diversi processi in sottofondo che funzionano senza interazione dell'utente:

### Aggiornamento dei feed podcast

All'avvio di RadioHub, viene lanciato un processo periodico in sottofondo che controlla automaticamente tutti i feed podcast sottoscritti per nuovi episodi. L'intervallo (predefinito: 6 ore) è configurabile in [Setup > Podcast](#/setup/podcast). Con il download automatico attivato, i nuovi episodi vengono scaricati automaticamente.

### Gestione del buffer HLS

Non appena una stazione viene riprodotta in modalità HLS, il backend avvia un processo FFmpeg che divide il flusso audio in brevi segmenti (1 secondo ciascuno). Questi formano un buffer rotante di 10 minuti. In parallelo, un registratore di metadati ICY rileva i cambi di titolo nel flusso. Entrambi i processi terminano automaticamente quando la riproduzione viene interrotta.

### Monitoraggio delle registrazioni

Durante una registrazione attiva, sono in esecuzione due processi di monitoraggio:

- **Rilevamento di blocco:** Ogni 30 secondi si verifica se il file di registrazione sta crescendo. Tre controlli consecutivi senza crescita (90 secondi) attivano un riavvio del processo di registrazione.
- **Monitoraggio dello spazio:** Lo spazio libero su disco viene controllato regolarmente. Se scende sotto i 100 MB, la registrazione viene automaticamente interrotta per prevenire la perdita di dati.

### Registrazione del buffer HLS (HLS-REC)

Durante una registrazione del buffer HLS, un processo collettore copia i nuovi segmenti dal buffer HLS alla directory di registrazione ogni 0,5 secondi. All'avvio, i minuti di retrospettiva configurati vengono inoltre presi dal buffer esistente. All'arresto, i segmenti vengono automaticamente uniti e divisi in titoli individuali se sono disponibili dati ICY.

### Cache dei favicon

Durante il caricamento della lista delle stazioni, le icone mancanti vengono scaricate in sottofondo e memorizzate nella cache locale. Questo processo viene eseguito silenziosamente e non influisce sull'interfaccia.

### Rilevamento del bitrate

Alla prima riproduzione di una stazione, RadioHub verifica il bitrate effettivo e il codec tramite FFprobe. Il risultato viene salvato e visualizzato nella lista delle stazioni. In [Setup > Radio > Stazioni](#/setup/radio/sender), può essere avviata una verifica in blocco per tutte le stazioni.

---

## Limitazioni note

- **Differita solo in modalità HLS:** I flussi diretti vengono trasmessi 1:1, senza buffering.
- **La qualità ICY varia:** Alcune stazioni forniscono metadati imprecisi o ritardati. Questo influisce sulla precisione dei tagli.
- **Certificati SSL:** Alcune stazioni utilizzano configurazioni SSL insolite. RadioHub aggira il problema quando necessario, ma possono comparire avvisi.
- **Registrazioni lunghe:** Durante le perdite di connessione, al massimo 30 minuti vengono persi (un segmento). I segmenti più vecchi vengono conservati.
- **Limitazioni del browser:** L'API Web Audio nel browser può fornire dati del VU-metro solo quando il contesto audio è attivo. Alcuni browser richiedono l'interazione dell'utente per questo.

---

## Per approfondire

Per i curiosi della tecnica - le tecnologie e gli standard dietro RadioHub:

### Protocolli di streaming

- [HTTP Live Streaming (HLS)](https://it.wikipedia.org/wiki/HTTP_Live_Streaming) - Protocollo di streaming adattivo di Apple utilizzato da RadioHub per la differita
- [Icecast](https://it.wikipedia.org/wiki/Icecast) - Server di streaming open-source che ha reso popolare il protocollo di metadati ICY
- [SHOUTcast / Protocollo ICY](https://it.wikipedia.org/wiki/SHOUTcast) - Origine dello standard di metadati ICY per le informazioni sui titoli nei flussi
- [Radio su Internet](https://it.wikipedia.org/wiki/Web_radio) - Panoramica generale dello streaming radio su Internet

### Formati audio e codec

- [MP3 (MPEG-1 Audio Layer 3)](https://it.wikipedia.org/wiki/MP3) - Il formato audio più comune per i flussi radio
- [AAC (Advanced Audio Coding)](https://it.wikipedia.org/wiki/Advanced_Audio_Coding) - Codec più moderno con migliore qualità allo stesso bitrate
- [Ogg Vorbis](https://it.wikipedia.org/wiki/Vorbis) - Codec audio libero e aperto
- [FLAC (Free Lossless Audio Codec)](https://it.wikipedia.org/wiki/FLAC) - Compressione senza perdita per la massima qualità

### Elaborazione audio

- [EBU R128](https://it.wikipedia.org/wiki/EBU_R_128) - Standard europeo di normalizzazione della sonorità nella trasmissione
- [FFmpeg](https://it.wikipedia.org/wiki/FFmpeg) - Il framework multimediale centrale utilizzato da RadioHub per conversione, registrazione e montaggio
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) - Interfaccia del browser per l'analisi audio (VU-metro, forma d'onda)

### Fonti di dati

- [API Radio-Browser](https://www.radio-browser.info/) - Database comunitario aperto con oltre 30.000 stazioni radio in tutto il mondo
- [Podcast Index](https://podcastindex.org/) - Catalogo podcast aperto come alternativa ai cataloghi proprietari
- [RSS (Really Simple Syndication)](https://it.wikipedia.org/wiki/RSS) - Il formato feed attraverso il quale i podcast forniscono nuovi episodi

### Fondamenti tecnici

- [Bitrate](https://it.wikipedia.org/wiki/Bitrate) - Tasso di dati di un flusso audio (ad es. 128 kbps, 320 kbps)
- [Streaming](https://it.wikipedia.org/wiki/Streaming) - Fondamenti della trasmissione dati in tempo reale
- [Compressione audio](https://it.wikipedia.org/wiki/Compressione_audio) - Come funziona la compressione con perdita
- [SSL/TLS](https://it.wikipedia.org/wiki/Transport_Layer_Security) - Crittografia utilizzata nei flussi HTTPS
