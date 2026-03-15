/**
 * RadioHub Tour Lokalisierungen v2.0
 * 7 Touren -- Deutsch + Englisch
 * Separate Datei -- nicht in den Haupt-Locales um Kopplung zu vermeiden.
 */

const locales = {
  de: {
    // === Menü ===
    'tour.menuTitle': 'Lernmodus',
    'tour.welcome': 'Willkommen',
    'tour.welcomeDesc': 'Sender laden, auswählen und abspielen',
    'tour.favorites': 'Favoriten',
    'tour.favoritesDesc': 'Lieblingssender markieren und filtern',
    'tour.playerFeatures': 'Player-Funktionen',
    'tour.playerFeaturesDesc': 'Timeshift, Seekbar, Bitrate und Modi',
    'tour.recording': 'Aufnahme',
    'tour.recordingDesc': 'Sender aufnehmen und Sessions verwalten',
    'tour.podcast': 'Podcasts',
    'tour.podcastDesc': 'Podcasts suchen, abonnieren und abspielen',
    'tour.sourceJump': 'Quell-Sprung',
    'tour.sourceJumpDesc': 'Von überall zur Wiedergabe zurückspringen',
    'tour.settings': 'Einstellungen',
    'tour.settingsDesc': 'Filter, Dienste und Optionen anpassen',

    // === Buttons ===
    'tour.next': 'Weiter',
    'tour.prev': 'Zurück',
    'tour.skip': 'Beenden',
    'tour.close': 'Schließen',
    'tour.startTour': 'Starten',
    'tour.completed': 'Abgeschlossen',
    'tour.step': 'Schritt',
    'tour.of': 'von',
    'tour.waitAction': 'Führe die Aktion aus...',

    // === 1. Willkommen ===
    'tour.w.navTitle': 'Willkommen bei RadioHub',
    'tour.w.navText': 'Vier Bereiche warten auf dich: Radio, Aufnahme, Podcast und Einstellungen. Du erreichst sie per Klick oder mit den Tasten 1-4.',
    'tour.w.loadTitle': 'Sender laden',
    'tour.w.loadText': 'Deine Senderliste ist noch leer. Klicke auf den Aktualisieren-Button um tausende Internetradio-Sender zu laden.',
    'tour.w.filterTitle': 'Filter und Sortierung',
    'tour.w.filterText': 'Links filterst du nach Land, Kategorie, Bitrate oder Stimmen. Die Zahlen zeigen wie viele Sender jeder Filter enthält.',
    'tour.w.selectTitle': 'Sender auswählen',
    'tour.w.selectText': 'Klicke jetzt auf einen Sender der dich interessiert. Per Klick auf die Zeile siehst du Details, per Klick auf die LED oder das Cover startest du die Wiedergabe.',
    'tour.w.displayTitle': 'Wiedergabe läuft',
    'tour.w.displayText': 'Im Display siehst du den Sendernamen und den aktuellen Titel (ICY-Metadaten). Die Quellanzeige unten zeigt den Stream-Modus.',
    'tour.w.doneTitle': 'Geschafft!',
    'tour.w.doneText': 'Du kennst jetzt die Grundlagen. Mit der Suchleiste findest du Sender nach Name. Probiere als nächstes "Favoriten" oder "Aufnahme".',

    // === 2. Favoriten ===
    'tour.fav.headerTitle': 'Favoriten-Spalte',
    'tour.fav.headerText': 'Ganz rechts in der Senderliste findest du die Favoriten-Spalte. Jeder Sender hat eine LED die gelb leuchtet wenn er als Favorit gespeichert ist.',
    'tour.fav.addTitle': 'Favorit markieren',
    'tour.fav.addText': 'Klicke jetzt auf die LED in der Stern-Spalte neben einem Sender. Sie wechselt auf Gelb -- der Sender ist jetzt dein Favorit.',
    'tour.fav.ledTitle': 'Favoriten-LED',
    'tour.fav.ledText': 'Gelbe LEDs zeigen deine Favoriten. Ein erneuter Klick entfernt die Markierung. Deine Favoriten bleiben dauerhaft gespeichert.',
    'tour.fav.filterTitle': 'Nur Favoriten anzeigen',
    'tour.fav.filterText': 'Dieser Button filtert die Senderliste auf deine Favoriten. So findest du deine Lieblingssender sofort.',
    'tour.fav.showTitle': 'Gefilterte Ansicht',
    'tour.fav.showText': 'Jetzt siehst du nur deine Favoriten. Der Filter bleibt aktiv bis du ihn ausschaltest -- auch nach einem Neustart.',
    'tour.fav.doneTitle': 'Favoriten eingerichtet',
    'tour.fav.doneText': 'Du weißt jetzt wie Favoriten funktionieren. Tipp: Mit Prev/Next (Pfeiltasten) springst du zwischen deinen Favoriten hin und her.',

    // === 3. Player-Funktionen ===
    'tour.pf.modeTitle': 'Stream-Modus: Direct vs. HLS',
    'tour.pf.modeText': 'Dieser Button wechselt zwischen Direct (Direktstream, minimale Latenz) und HLS (Timeshift mit Puffer). Im HLS-Modus kannst du Live-Radio zurückspulen und zeitversetzt hören.',
    'tour.pf.seekTitle': 'Segment-Seekbar',
    'tour.pf.seekText': 'Der Fader ist deine Seekbar. Im HLS-Modus springst du in 10-Sekunden-Segmenten durch den Puffer. Bei Aufnahmen und Podcasts navigierst du durch die gesamte Datei. Ziehe ihn einfach nach links.',
    'tour.pf.liveTitle': 'GoLive-Button',
    'tour.pf.liveText': 'Wenn du im HLS-Modus zurückgespult hast, springt dieser Button sofort zum Live-Punkt. Die LED zeigt: Grün = du bist live, Aus = du bist zeitversetzt.',
    'tour.pf.bitrateTitle': 'Bitrate-LEDs (HLS)',
    'tour.pf.bitrateText': 'Im HLS-Modus zeigen 8 LEDs die Bitrate-Stufen von 32 bis 320 kbps. Klicke auf eine LED um die Qualität manuell festzulegen, oder lass die automatische Anpassung arbeiten.',
    'tour.pf.playModeTitle': 'Wiedergabe-Modus',
    'tour.pf.playModeText': 'Dieser Button wechselt den Modus: Linear (der Reihe nach), Loop (Endlosschleife) oder Shuffle (Zufall). Relevant für Playlists, Aufnahme-Segmente und Podcast-Episoden.',
    'tour.pf.timerTitle': 'Timer und Zeitanzeige',
    'tour.pf.timerText': 'Der Timer zeigt die Laufzeit. Er wird Rot bei Aufnahme, Grün bei Podcast. Im HLS-Modus siehst du den Puffer-Status und Zeitversatz zum Live-Punkt.',
    'tour.pf.sourceTitle': 'Quellanzeige und Navigation',
    'tour.pf.sourceText': 'Die Quellanzeige zeigt LIVE, HLS, STREAM, REC oder FILE. Sie ist klickbar: Ein Klick springt zum aktuell spielenden Inhalt zurück -- egal in welchem Tab du bist.',

    // === 4. Aufnahme ===
    'tour.rec.prepTitle': 'Sender abspielen',
    'tour.rec.prepText': 'Um aufzunehmen muss ein Sender laufen. Spiele jetzt einen Sender ab, falls noch keiner läuft -- klicke auf eine LED in der Senderliste.',
    'tour.rec.startTitle': 'Aufnahme starten',
    'tour.rec.startText': 'Drücke jetzt den roten REC-Button. Die Aufnahme startet sofort und läuft im Hintergrund weiter -- du kannst in andere Tabs wechseln.',
    'tour.rec.runningTitle': 'Aufnahme läuft',
    'tour.rec.runningText': 'Der Timer ist rot und zählt die Dauer. ICY-fähige Sender liefern Titelwechsel die automatisch als Schnittmarken gesetzt werden -- perfekt zum späteren Zerschneiden.',
    'tour.rec.stopTitle': 'Aufnahme stoppen',
    'tour.rec.stopText': 'Drücke jetzt den Stop-Button um die Aufnahme zu beenden. Die Session wird automatisch gespeichert.',
    'tour.rec.sessionsTitle': 'Sessions-Übersicht',
    'tour.rec.sessionsText': 'In der Seitenleiste siehst du alle Aufnahme-Sessions mit Datum, Sender und Dauer. Die aktive Session ist markiert.',
    'tour.rec.detailTitle': 'Session öffnen',
    'tour.rec.detailText': 'Klicke auf eine Session um die einzelnen Segmente zu sehen. Von hier kannst du Segmente abspielen, einzeln exportieren oder per Batch verarbeiten.',
    'tour.rec.doneTitle': 'Aufnahme gemeistert',
    'tour.rec.doneText': 'Du kennst jetzt den Aufnahme-Workflow. Tipp: Die Aufnahme läuft auch bei Tab-Wechsel weiter. Probiere den "Quell-Sprung" um jederzeit zurückzukehren.',

    // === 5. Podcast ===
    'tour.pod.tabTitle': 'Podcast-Tab',
    'tour.pod.tabText': 'Im Podcast-Bereich verwaltest du Abonnements und hörst Episoden. Noch ist alles leer -- lass uns deinen ersten Podcast abonnieren.',
    'tour.pod.searchTitle': 'Suche öffnen',
    'tour.pod.searchText': 'Die Suche ist jetzt offen. Du kannst Episoden, deine Abos oder das externe Podcast-Verzeichnis durchsuchen.',
    'tour.pod.scopeTitle': 'Extern suchen',
    'tour.pod.scopeText': 'Wir wechseln auf "Extern" um im Podcast-Verzeichnis nach neuen Podcasts zu suchen. Hier findest du hunderttausende Podcasts.',
    'tour.pod.inputTitle': 'Suchergebnisse',
    'tour.pod.inputText': 'Der Suchbegriff wurde automatisch eingegeben. Warte kurz auf die Ergebnisse aus dem Verzeichnis.',
    'tour.pod.subscribeTitle': 'Jetzt abonnieren',
    'tour.pod.subscribeText': 'Klicke auf einen Podcast in den Suchergebnissen um ihn zu abonnieren. Er erscheint dann in deiner Seitenleiste.',
    'tour.pod.sidebarTitle': 'Dein erstes Abo',
    'tour.pod.sidebarText': 'Dein Abo ist in der Seitenleiste. Hier siehst du alle abonnierten Podcasts mit Episoden-Zähler. Das Sync-Symbol zeigt ob Auto-Download aktiv ist.',
    'tour.pod.playTitle': 'Episode abspielen',
    'tour.pod.playText': 'Klicke auf eine Episode um sie abzuspielen. Die Wiedergabe startet als Stream -- du kannst sofort hören ohne vorher herunterzuladen.',

    // === 6. Quell-Sprung ===
    'tour.sj.introTitle': 'Quell-Sprung vorbereiten',
    'tour.sj.introText': 'Der Quell-Sprung bringt dich von überall zur aktuellen Wiedergabe zurück. Dafür muss etwas laufen -- spiele einen Sender oder eine Episode ab.',
    'tour.sj.modeTitle': 'Quellanzeige',
    'tour.sj.modeText': 'Die Quellanzeige zeigt den aktiven Modus: LIVE, HLS, STREAM oder REC. Sie ist gleichzeitig ein klickbarer Link zur Quelle.',
    'tour.sj.switchTitle': 'Tab gewechselt',
    'tour.sj.switchText': 'Wir sind jetzt in den Einstellungen, aber die Wiedergabe läuft weiter. Schau auf die Quellanzeige im Player unten.',
    'tour.sj.awayTitle': 'Wiedergabe im Hintergrund',
    'tour.sj.awayText': 'Siehst du? Die Quellanzeige zeigt noch immer den Stream-Modus. Die Wiedergabe stoppt nicht beim Tab-Wechsel.',
    'tour.sj.jumpTitle': 'Jetzt springen!',
    'tour.sj.jumpText': 'Klicke jetzt auf die Quellanzeige im Player. Du springst automatisch zum Tab mit dem aktuell spielenden Inhalt zurück.',
    'tour.sj.doneTitle': 'Quell-Sprung gemeistert',
    'tour.sj.doneText': 'Du bist zurück! Der Quell-Sprung funktioniert aus jedem Tab -- egal ob Radio, Podcast oder Aufnahme gerade spielt.',

    // === 7. Einstellungen ===
    'tour.set.tabTitle': 'Einstellungen',
    'tour.set.tabText': 'Hier passt du RadioHub an deine Vorlieben an. Die wichtigsten Bereiche: Theme, Radio-Filter und externe Dienste.',
    'tour.set.sidebarTitle': 'Bereiche',
    'tour.set.sidebarText': 'Sechs Bereiche stehen zur Auswahl: Allgemein, Radio, Podcast, Aufnahmen, Speicher und Dienste. Oben wechselst du zwischen Einstellungen, Tastenkürzel und Info.',
    'tour.set.themeTitle': 'Dunkel oder Hell',
    'tour.set.themeText': 'Wähle deinen bevorzugten Anzeigemodus. Die Einstellung wird gespeichert. Du erreichst den Theme-Wechsel auch über den Button rechts im Header.',
    'tour.set.radioTitle': 'Radio-Filter',
    'tour.set.radioText': 'Im Radio-Bereich konfigurierst du welche Sender angezeigt werden. Hier findest du Sprachfilter, Seltenheitsschwelle und die Block-Zone.',
    'tour.set.filterTitle': 'Sprachfilter und Block-Zone',
    'tour.set.filterText': 'Schließe Sprachen aus die dich nicht interessieren. Die Block-Zone blendet einzelne Sender permanent aus. Mit "Vorschau" siehst du welche Sender betroffen wären.',
    'tour.set.servicesTitle': 'Externe Dienste',
    'tour.set.servicesText': 'Hier siehst du alle APIs: Radio-Verzeichnis, Podcast-Suche, Werbeerkennung mit Domain-Blacklist. Die URLs lassen sich anpassen.'
  },

  en: {
    // === Menu ===
    'tour.menuTitle': 'Learn Mode',
    'tour.welcome': 'Welcome',
    'tour.welcomeDesc': 'Load, select and play stations',
    'tour.favorites': 'Favorites',
    'tour.favoritesDesc': 'Mark and filter favorite stations',
    'tour.playerFeatures': 'Player Features',
    'tour.playerFeaturesDesc': 'Timeshift, seekbar, bitrate and modes',
    'tour.recording': 'Recording',
    'tour.recordingDesc': 'Record stations and manage sessions',
    'tour.podcast': 'Podcasts',
    'tour.podcastDesc': 'Search, subscribe and play podcasts',
    'tour.sourceJump': 'Source Jump',
    'tour.sourceJumpDesc': 'Jump back to playback from anywhere',
    'tour.settings': 'Settings',
    'tour.settingsDesc': 'Customize filters, services and options',

    // === Buttons ===
    'tour.next': 'Next',
    'tour.prev': 'Back',
    'tour.skip': 'End',
    'tour.close': 'Close',
    'tour.startTour': 'Start',
    'tour.completed': 'Completed',
    'tour.step': 'Step',
    'tour.of': 'of',
    'tour.waitAction': 'Perform the action...',

    // === 1. Welcome ===
    'tour.w.navTitle': 'Welcome to RadioHub',
    'tour.w.navText': 'Four sections await: Radio, Recording, Podcast and Settings. Click a tab or press keys 1-4.',
    'tour.w.loadTitle': 'Load Stations',
    'tour.w.loadText': 'Your station list is empty. Click the refresh button to load thousands of internet radio stations.',
    'tour.w.filterTitle': 'Filters and Sorting',
    'tour.w.filterText': 'Filter by country, category, bitrate or votes on the left. Numbers show how many stations each filter contains.',
    'tour.w.selectTitle': 'Select a Station',
    'tour.w.selectText': 'Click on a station that interests you. Click the row for details, click the LED or cover to start playback.',
    'tour.w.displayTitle': 'Playback Active',
    'tour.w.displayText': 'The display shows the station name and current title (ICY metadata). The source indicator below shows the stream mode.',
    'tour.w.doneTitle': 'Done!',
    'tour.w.doneText': 'You know the basics now. Use the search bar to find stations by name. Try "Favorites" or "Recording" next.',

    // === 2. Favorites ===
    'tour.fav.headerTitle': 'Favorites Column',
    'tour.fav.headerText': 'On the far right of the station list you find the favorites column. Each station has an LED that glows yellow when marked as favorite.',
    'tour.fav.addTitle': 'Mark a Favorite',
    'tour.fav.addText': 'Click the LED in the star column next to a station. It turns yellow -- the station is now your favorite.',
    'tour.fav.ledTitle': 'Favorite LED',
    'tour.fav.ledText': 'Yellow LEDs mark your favorites. Click again to remove. Your favorites are saved permanently.',
    'tour.fav.filterTitle': 'Show Favorites Only',
    'tour.fav.filterText': 'This button filters the station list to your favorites. Find your favorite stations instantly.',
    'tour.fav.showTitle': 'Filtered View',
    'tour.fav.showText': 'You now see only your favorites. The filter stays active until you turn it off -- even after restart.',
    'tour.fav.doneTitle': 'Favorites Set Up',
    'tour.fav.doneText': 'You know how favorites work. Tip: Prev/Next (arrow keys) jumps between your favorites.',

    // === 3. Player Features ===
    'tour.pf.modeTitle': 'Stream Mode: Direct vs. HLS',
    'tour.pf.modeText': 'This button switches between Direct (minimal latency) and HLS (timeshift with buffer). In HLS mode you can rewind live radio and listen time-shifted.',
    'tour.pf.seekTitle': 'Segment Seekbar',
    'tour.pf.seekText': 'The fader is your seekbar. In HLS mode it jumps in 10-second segments through the buffer. For recordings and podcasts it navigates the entire file.',
    'tour.pf.liveTitle': 'GoLive Button',
    'tour.pf.liveText': 'When you have rewound in HLS mode, this button jumps back to the live point. LED: Green = live, Off = time-shifted.',
    'tour.pf.bitrateTitle': 'Bitrate LEDs (HLS)',
    'tour.pf.bitrateText': '8 LEDs show bitrate levels from 32 to 320 kbps in HLS mode. Click an LED to set quality manually, or let auto-adjustment handle it.',
    'tour.pf.playModeTitle': 'Playback Mode',
    'tour.pf.playModeText': 'This button cycles through modes: Linear (sequential), Loop (repeat) or Shuffle (random). Relevant for playlists, recording segments and podcast episodes.',
    'tour.pf.timerTitle': 'Timer Display',
    'tour.pf.timerText': 'The timer shows elapsed time. Red during recording, green for podcasts. In HLS mode you also see buffer status and time offset.',
    'tour.pf.sourceTitle': 'Source Indicator and Navigation',
    'tour.pf.sourceText': 'Shows LIVE, HLS, STREAM, REC or FILE. It is clickable: click to jump back to the currently playing content -- from any tab.',

    // === 4. Recording ===
    'tour.rec.prepTitle': 'Play a Station',
    'tour.rec.prepText': 'To record, a station must be playing. Play a station now if none is running -- click an LED in the station list.',
    'tour.rec.startTitle': 'Start Recording',
    'tour.rec.startText': 'Press the red REC button now. Recording starts immediately and runs in the background -- you can switch tabs.',
    'tour.rec.runningTitle': 'Recording Active',
    'tour.rec.runningText': 'The timer turns red and counts duration. ICY-capable stations deliver title changes that are automatically set as cut marks.',
    'tour.rec.stopTitle': 'Stop Recording',
    'tour.rec.stopText': 'Press the Stop button to end the recording. The session is saved automatically.',
    'tour.rec.sessionsTitle': 'Sessions Overview',
    'tour.rec.sessionsText': 'The sidebar shows all recording sessions with date, station and duration. The active session is highlighted.',
    'tour.rec.detailTitle': 'Open Session',
    'tour.rec.detailText': 'Click a session to see its segments. From here you can play segments, export individually or batch process.',
    'tour.rec.doneTitle': 'Recording Mastered',
    'tour.rec.doneText': 'You know the recording workflow now. Tip: Recording continues across tab switches. Try "Source Jump" to get back anytime.',

    // === 5. Podcast ===
    'tour.pod.tabTitle': 'Podcast Tab',
    'tour.pod.tabText': 'Manage your podcast subscriptions and listen to episodes here. Everything is empty -- let us subscribe to your first podcast.',
    'tour.pod.searchTitle': 'Open Search',
    'tour.pod.searchText': 'The search panel is now open. You can search episodes, subscriptions or the external podcast directory.',
    'tour.pod.scopeTitle': 'Search Externally',
    'tour.pod.scopeText': 'We switch to "External" to search the podcast directory for new podcasts. Hundreds of thousands are available.',
    'tour.pod.inputTitle': 'Search Results',
    'tour.pod.inputText': 'The search term was entered automatically. Wait a moment for results from the directory.',
    'tour.pod.subscribeTitle': 'Subscribe Now',
    'tour.pod.subscribeText': 'Click a podcast in the search results to subscribe. It will appear in your sidebar.',
    'tour.pod.sidebarTitle': 'Your First Subscription',
    'tour.pod.sidebarText': 'Your subscription is in the sidebar. Here you see all subscribed podcasts with episode count. The sync icon shows if auto-download is active.',
    'tour.pod.playTitle': 'Play Episode',
    'tour.pod.playText': 'Click an episode to play it. Playback starts as a stream -- listen immediately without downloading first.',

    // === 6. Source Jump ===
    'tour.sj.introTitle': 'Prepare Source Jump',
    'tour.sj.introText': 'Source jump brings you back to the current playback from anywhere. Something must be playing -- start a station or episode.',
    'tour.sj.modeTitle': 'Source Indicator',
    'tour.sj.modeText': 'The source indicator shows the active mode: LIVE, HLS, STREAM or REC. It is also a clickable link to the source.',
    'tour.sj.switchTitle': 'Tab Switched',
    'tour.sj.switchText': 'We are now in Settings, but playback continues. Look at the source indicator in the player below.',
    'tour.sj.awayTitle': 'Background Playback',
    'tour.sj.awayText': 'See? The source indicator still shows the stream mode. Playback does not stop when switching tabs.',
    'tour.sj.jumpTitle': 'Jump Now!',
    'tour.sj.jumpText': 'Click the source indicator in the player now. You will automatically jump back to the tab with the currently playing content.',
    'tour.sj.doneTitle': 'Source Jump Mastered',
    'tour.sj.doneText': 'You are back! Source jump works from any tab -- whether radio, podcast or recording is playing.',

    // === 7. Settings ===
    'tour.set.tabTitle': 'Settings',
    'tour.set.tabText': 'Customize RadioHub to your preferences. Key areas: theme, radio filters and external services.',
    'tour.set.sidebarTitle': 'Sections',
    'tour.set.sidebarText': 'Six sections: General, Radio, Podcast, Recordings, Storage and Services. Switch between Settings, Keyboard shortcuts and Info at the top.',
    'tour.set.themeTitle': 'Dark or Light',
    'tour.set.themeText': 'Choose your preferred display mode. The setting is saved. You can also switch the theme via the button in the header.',
    'tour.set.radioTitle': 'Radio Filters',
    'tour.set.radioText': 'Configure which stations are displayed in the Radio section. Here you find language filters, rarity threshold and the block zone.',
    'tour.set.filterTitle': 'Language Filter and Block Zone',
    'tour.set.filterText': 'Exclude languages you are not interested in. The block zone permanently hides individual stations. Use "Preview" to see which stations would be affected.',
    'tour.set.servicesTitle': 'External Services',
    'tour.set.servicesText': 'See all APIs here: radio directory, podcast search, ad detection with domain blacklist. URLs can be customized.'
  }
};

/**
 * Tour-Text holen (mit Fallback auf Deutsch)
 * @param {string} key - z.B. 'tour.w.navTitle'
 * @param {string} lang - z.B. 'de', 'en'
 */
export function tt(key, lang = 'de') {
  const l = locales[lang] || locales['en'] || locales['de'];
  return l[key] || locales['de'][key] || key;
}
