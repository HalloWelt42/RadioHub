# RadioHub - Informacje techniczne

Ten poradnik wyjasnia kluczowe koncepcje, terminy techniczne i ograniczenia RadioHub. Pomaga zrozumiec, dlaczego pewne funkcje dzialaja w okreslony sposob.

---

## Tryby odtwarzania

### Tryb HLS (domyslny)

HLS oznacza "HTTP Live Streaming". RadioHub konwertuje strumien radiowy przez backend na male segmenty, ktore przegladarka moze odtwarzac. Umozliwia to:

- **Przesuniecie czasowe (Timeshift):** Przewijanie wstecz w ramach biezacego programu
- **Pauza i wznowienie:** Bufor kontynuuje w tle
- **Nagrywanie z bufora:** Nagrywanie wczesniej sluchanej tresci (HLS-REC)
- **Kontrola bitrate:** Automatyczne dostosowanie do polaczenia

Bufor HLS jest utrzymywany w backendzie. Rozmiar mozna skonfigurowac w [Ustawienia > Ogolne](#/setup/allgemein/einstellungen) (Bufor przesuniecia czasowego).

### Tryb bezposredni

W trybie bezposrednim przegladarka laczy sie bezposrednio z oryginalnym strumieniem stacji. Jest to bardziej oszczedne pod wzgledem zasobow, ale bez przesuniecia czasowego, pauzy lub nagrywania z bufora. Przydatne dla serwerow, ktore nie obsluguja konwersji HLS.

---

## Odznaki na liscie stacji

### ICY (zielone / szare)

**ICY** oznacza "Icecast Metadata" - protokol pozwalajacy stacjom radiowym wysylac aktualny tytul w ramach strumienia. Gdy stacja obsluguje ICY, RadioHub wyswietla aktualny tytul i moze automatycznie dzielic nagrania na poszczegolne utwory.

- **ICY (zielone, "dobre"):** Stacja dostarcza precyzyjne znaczniki czasu zmiany tytulu. Ciecia beda czyste.
- **ICY (zielone, "slabe"):** Stacja dostarcza dane ICY, ale znaczniki czasu sa niedokladne (np. opoznione raporty). Ciecia moga miec nakladanie sie lub przerwy.
- **ICY (szare):** ICY jest obecne, ale jakosc nie zostala jeszcze oceniona. Kliknij, aby przelaczac miedzy "dobre" i "slabe".

**Dlaczego to ma znaczenie?** Niektore stacje zgaszaja nowy tytul dopiero sekundy po faktycznej zmianie. RadioHub uzywa pozycji bajtow w strumieniu audio do obliczania ciecia, ale jesli stacja zglasza z opoznieniem, ciecie bedzie niedokladne.

### Odznaki AD (Wykrywanie reklam)

RadioHub moze sprawdzac stacje pod katem reklam. Sprawdzanie mozna uruchomic w [Setup > Radio > Stacje](#/setup/radio/sender) i analizuje adresy URL strumieni oraz odpowiedzi serwerow:

- **0% AD (zielone):** Brak podejrzenia reklam po sprawdzeniu
- **XX% AD (zolte):** Procentowe podejrzenie (np. "35% AD") - prog konfigurowalny
- **AD (czerwone):** Recznie oznaczone jako reklama (ukryte)
- **OK (niebieskie):** Recznie zatwierdzone pomimo podejrzenia

---

## System nagrywania

### Nagrywanie segmentowane

RadioHub nagrywa w segmentach 30-minutowych. Jesli polaczenie ze stacja zostanie przerwane, tracony jest co najwyzej biezacy segment - nie cale nagranie. Przy 8-godzinnym nagraniu to co najwyzej 30 minut zamiast wszystkiego. Ustawienia nagrywania (format, bitrate, folder) w [Setup > Nagrania](#/setup/aufnahmen).

### Wykrywanie zastoju

Podczas nagrywania RadioHub monitoruje rozmiar pliku. Jesli plik nie rosnie przez 30 sekund, proces nagrywania jest wykrywany jako "zastoj" i uruchamiany ponownie. Zapobiega to cichym nagraniom, w ktorych FFmpeg dziala, ale nie otrzymuje juz danych.

### Podzial wedlug tytulow ICY

Jesli stacja ma metadane ICY, 30-minutowe segmenty sa automatycznie dzielone na poszczegolne utwory na podstawie wykrytych zmian tytulow po zakonczeniu nagrywania. Bez ICY 30-minutowe bloki pozostaja jako segmenty.

### Strumienie HTTPS i ponowne polaczenie

Wiele stacji uzywa HTTPS. Wbudowana funkcja ponownego polaczenia FFmpeg dziala niezawodnie tylko ze strumieniami HTTP. Dlatego RadioHub sam zarzadza monitorowaniem i ponownym uruchomieniem przy przerwach polaczenia, niezaleznie od protokolu.

---

## Przesuniecie czasowe i bufor

### Jak dziala przesuniecie czasowe?

Backend utrzymuje rotacyjny bufor segmentow audio. Kazdy segment ma kilka sekund dlugosci. Przegladarka zada tych segmentow przez liste odtwarzania HLS. Przy przewijaniu wstecz starsze segmenty sa ladowane z bufora.

### Nagrywanie z bufora (HLS-REC)

Nagrywanie z bufora wykorzystuje istniejacy bufor HLS. Gdy rozpoczynasz nagrywanie, RadioHub moze wlaczyc ostatnie X minut z bufora. Okres retrospekcji jest konfigurowalny w [Ustawienia > Ogolne](#/setup/allgemein/einstellungen) (Nagrywanie HLS). Pozwala to nagrywac utwor, ktory juz jest odtwarzany.

---

## Cutter (Narzedzie do edycji)

### Fala dzwiekowa

Wizualizacja fali dzwiekowej jest obliczana z danych audio (wartosci szczytowe). Pokazuje glosnosc w czasie i pomaga w precyzyjnym umieszczaniu punktow ciecia.

### Markery

Markery to punkty ciecia na fali dzwiekowej. Moga byc ustawiane recznie lub automatycznie pobierane ze zmian tytulow ICY. Podczas ciecia nagranie jest dzielone w tych punktach na segmenty.

### Analiza przejsc

Analiza bada obszary audio wokol kazdego markera. Ocenia, czy przejscie jest czyste (cisza miedzy tytulami) czy problematyczne (np. crossfade, gdzie dwa tytuly nakladaja sie na siebie). Kolory: Zielony = dobry, Zolty = sprawdzic, Czerwony = problematyczny.

### Normalizacja (EBU R128)

Normalizacja dostosowuje glosnosc do standardu EBU R128 - europejskiego standardu nadawczego dla spojnej glosnosci. W ten sposob wszystkie segmenty brzmia jednakowo glosno, niezaleznie od oryginalnej glosnosci stacji.

---

## System podcastow

### Automatyczne pobieranie

Subskrybowane podcasty moga automatycznie pobierac nowe odcinki. Interwal jest konfigurowalny w [Setup > Podcast](#/setup/podcast). Pobrane pliki sa przechowywane lokalnie i dostepne offline.

### Aktualizacja kanalu

Kanaly podcastow sa odpytywane przez RSS/Atom. [Interwal aktualizacji](#/setup/podcast) okresla, jak czesto RadioHub sprawdza nowe odcinki.

---

## Pamiec i dane

W [Setup > Pamiec](#/setup/speicher) mozna skonfigurowac sciezki przechowywania nagran, podcastow i cache. Wyswietlacz pokazuje zajete i wolne miejsce na zone.

Zewnetrzne zrodla danych (Radio-Browser API, Podcast Index) sa widoczne w [Setup > Uslugi](#/setup/dienste) i w razie potrzeby moga byc przekierowane do wlasnych instancji.

---

## Automatyczne procesy w tle

RadioHub uruchamia kilka procesow w tle, ktore dzialaja bez interakcji uzytkownika:

### Aktualizacja kanalow podcastow

Gdy RadioHub sie uruchamia, uruchamiany jest okresowy proces w tle, ktory automatycznie sprawdza wszystkie subskrybowane kanaly podcastow pod katem nowych odcinkow. Interwal (domyslnie: 6 godzin) jest konfigurowalny w [Setup > Podcast](#/setup/podcast). Przy wlaczonym automatycznym pobieraniu nowe odcinki sa pobierane automatycznie.

### Zarzadzanie buforem HLS

Gdy stacja jest odtwarzana w trybie HLS, backend uruchamia proces FFmpeg, ktory dzieli strumien audio na krotkie segmenty (po 1 sekundzie). Tworza one rotacyjny 10-minutowy bufor. Rownolegle dziala rejestrator metadanych ICY, ktory wykrywa zmiany tytulow w strumieniu. Oba procesy konczaja sie automatycznie po zatrzymaniu odtwarzania.

### Monitorowanie nagrywania

Podczas aktywnego nagrywania dzialaja dwa procesy monitorujace:

- **Wykrywanie zastoju:** Co 30 sekund sprawdzane jest, czy plik nagrania rosnie. Trzy kolejne sprawdzenia bez wzrostu (90 sekund) uruchamiaja ponowne uruchomienie procesu nagrywania.
- **Monitorowanie pamieci:** Wolne miejsce na dysku jest regularnie sprawdzane. Jesli spadnie ponizej 100 MB, nagrywanie jest automatycznie zatrzymywane, aby zapobiec utracie danych.

### Nagrywanie z bufora HLS (HLS-REC)

Podczas nagrywania z bufora HLS proces kolekcji kopiuje nowe segmenty z bufora HLS do katalogu nagran co 0,5 sekundy. Na poczatku skonfigurowane minuty retrospekcji sa dodatkowo pobierane z istniejacego bufora. Po zatrzymaniu segmenty sa automatycznie laczone i dzielone na poszczegolne tytuly, jesli dane ICY sa dostepne.

### Cache favicon

Podczas ladowania listy stacji brakujace ikony stacji sa pobierane w tle i przechowywane w lokalnej pamieci podrecznej. Ten proces dziala cicho i nie wplywa na interfejs.

### Wykrywanie bitrate

Przy pierwszym odtwarzaniu stacji RadioHub sprawdza rzeczywisty bitrate i kodek przez FFprobe. Wynik jest zapisywany i wyswietlany na liscie stacji. W [Setup > Radio > Stacje](#/setup/radio/sender) mozna uruchomic masowe sprawdzanie dla wszystkich stacji.

---

## Znane ograniczenia

- **Przesuniecie czasowe tylko w trybie HLS:** Strumienie bezposrednie sa przekazywane 1:1, bez buforowania.
- **Jakosc ICY jest rozna:** Niektore stacje dostarczaja niedokladne lub opoznione metadane. Wplywa to na dokladnosc ciec.
- **Certyfikaty SSL:** Niektore stacje uzywaja nietypowych konfiguracji SSL. RadioHub radzi sobie z tym w razie potrzeby, ale moga pojawiac sie ostrzezenia.
- **Dlugie nagrania:** Przy przerwach polaczenia tracone jest co najwyzej 30 minut (jeden segment). Starsze segmenty sa zachowywane.
- **Ograniczenia przegladarki:** Web Audio API w przegladarce moze dostarczac dane miernika VU tylko wtedy, gdy kontekst audio jest aktywny. Niektore przegladarki wymagaja do tego interakcji uzytkownika.

---

## Dalsze informacje

Dla ciekawych technicznie - technologie i standardy stojace za RadioHub:

### Protokoly streamingu

- [HTTP Live Streaming (HLS)](https://pl.wikipedia.org/wiki/HTTP_Live_Streaming) - Adaptacyjny protokol streamingu Apple uzywany przez RadioHub do przesuniecia czasowego
- [Icecast](https://pl.wikipedia.org/wiki/Icecast) - Serwer streamingu open-source, ktory spopularyzowal protokol metadanych ICY
- [SHOUTcast / Protokol ICY](https://pl.wikipedia.org/wiki/SHOUTcast) - Poczatek standardu metadanych ICY dla informacji o tytulach w strumieniach
- [Radio internetowe](https://pl.wikipedia.org/wiki/Radio_internetowe) - Ogolny przeglad streamingu radiowego w internecie

### Formaty audio i kodeki

- [MP3 (MPEG-1 Audio Layer 3)](https://pl.wikipedia.org/wiki/MP3) - Najpopularniejszy format audio dla strumieni radiowych
- [AAC (Advanced Audio Coding)](https://pl.wikipedia.org/wiki/Advanced_Audio_Coding) - Nowoczesniejszy kodek z lepsza jakoscia przy tym samym bitrate
- [Ogg Vorbis](https://pl.wikipedia.org/wiki/Vorbis) - Wolny, otwarty kodek audio
- [FLAC (Free Lossless Audio Codec)](https://pl.wikipedia.org/wiki/FLAC) - Bezstratna kompresja dla najwyzszej jakosci

### Przetwarzanie audio

- [EBU R128](https://en.wikipedia.org/wiki/EBU_R_128) - Europejski standard normalizacji glosnosci w nadawaniu
- [FFmpeg](https://pl.wikipedia.org/wiki/FFmpeg) - Centralne narzedzie multimedialne uzywane przez RadioHub do konwersji, nagrywania i ciecia
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) - Interfejs przegladarki do analizy audio (miernik VU, fala dzwiekowa)

### Zrodla danych

- [Radio-Browser API](https://www.radio-browser.info/) - Otwarta baza danych spolecznosci z ponad 30 000 stacji radiowych na calym swiecie
- [Podcast Index](https://podcastindex.org/) - Otwarty katalog podcastow jako alternatywa dla komercyjnych katalogow
- [RSS (Really Simple Syndication)](https://pl.wikipedia.org/wiki/RSS) - Format kanalu, przez ktory podcasty udostepniaja nowe odcinki

### Podstawy techniczne

- [Bitrate](https://pl.wikipedia.org/wiki/Przep%C5%82ywno%C5%9B%C4%87_binarna) - Szybkosc transmisji danych strumienia audio (np. 128 kbps, 320 kbps)
- [Streaming media](https://pl.wikipedia.org/wiki/Streaming) - Podstawy transmisji danych w czasie rzeczywistym
- [Kompresja audio](https://pl.wikipedia.org/wiki/Kodek_d%C5%BAwi%C4%99ku) - Jak dziala kompresja stratna
- [SSL/TLS](https://pl.wikipedia.org/wiki/Transport_Layer_Security) - Szyfrowanie uzywane w strumieniach HTTPS
