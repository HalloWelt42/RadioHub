"""Feinschnitt einer Aufnahme (RAD-45): Grenzen an der Stille, Werbung als ein Stück, Einschübe für sich, Titel nach
dem größten Anteil. Zahlen aus dem echten Mitschnitt von Mangoradio (21.11.2026)."""

from app.services import feinschnitt as fs


def test_grenze_am_ende_der_stille_vor_der_angabe():
    # 1986zig: Angabe bei 324,0; Stille 320,54 bis 323,16, dazu ein Aussetzer im neuen Lied kurz nach der Angabe
    stillen = [(320.54, 323.16), (324.30, 324.32)]
    assert fs.grenze(324.0, stillen) == 323.16
    # ohne Stille in der Nähe bleibt es bei der Angabe
    assert fs.grenze(500.0, stillen) == 500.0


def test_lange_pause_schlaegt_kurzen_aussetzer():
    # Aussetzer von 20 ms genau 0,7 s vor der Angabe, die echte Pause (2,5 s) endet 1,8 s davor
    assert fs.grenze(100.0, [(95.7, 98.2), (99.28, 99.30)]) == 98.2


def test_stuecke_wie_mangoradio():
    angaben = [fs.Angabe(1.0, "o2online.de - Ein bisschen Verbraucherinformationen ..."),
               fs.Angabe(11.0, "o2online.de - ...  zweite Halbzeit ..."),
               fs.Angabe(21.0, "Alvaro Soler - Sofia"),
               fs.Angabe(146.0, ""),
               fs.Angabe(148.0, "Cash Cash, Taylor Dayne - Tell It To My Heart"),
               fs.Angabe(200.0, "MANGORADIO", gesperrt=True)]
    stillen = [(19.99, 20.12), (145.30, 145.46), (147.75, 147.94)]
    werbung = [fs.Werbung(0.0, 20.12, "o2online.de")]
    liste = fs.stuecke(300.0, angaben, stillen, werbung)
    # geschnitten wird in der Pause: 0,15 s vor ihrem Ende, bei kurzen Pausen in ihrer Mitte
    assert [(round(s.von, 3), round(s.bis, 3), s.art, s.name) for s in liste] == [
        (0.0, 20.055, "werbung", "Werbung: o2online.de"),
        (20.055, 145.38, "titel", "Alvaro Soler - Sofia"),
        (145.38, 147.845, "einschub", "Einschub"),
        (147.845, 300.0, "titel", "Cash Cash, Taylor Dayne - Tell It To My Heart")]
    assert all(s.sicher for s in liste)


def test_titel_nach_dem_groessten_anteil_und_splitter():
    # eine Angabe kommt mitten im Lied ohne Stille (der Sender korrigiert den Titel): kein neues Stück unter 1,5 s,
    # aber ein Stück, dessen Titel weniger als 2/3 abdeckt, heißt nach dem größeren Teil und gilt als unsicher
    angaben = [fs.Angabe(0.0, "A"), fs.Angabe(60.0, "B"), fs.Angabe(60.8, "B (Radio Edit)")]
    liste = fs.stuecke(100.0, angaben, [], [])
    assert [(s.von, s.bis, s.name) for s in liste] == [(0.0, 60.0, "A"), (60.0, 100.0, "B (Radio Edit)")]
    angaben = [fs.Angabe(0.0, "A"), fs.Angabe(40.0, "B"), fs.Angabe(70.0, "C")]
    [a, b, c] = fs.stuecke(100.0, angaben, [], [])
    assert (b.name, b.sicher) == ("B", True)


def test_werbung_ohne_titel_dazwischen_und_leere_aufnahme():
    liste = fs.stuecke(60.0, [fs.Angabe(0.0, "Lied")], [], [fs.Werbung(20.0, 35.0, "")])
    assert [(s.von, s.bis, s.name) for s in liste] == [(0.0, 20.0, "Lied"), (20.0, 35.0, "Werbung"), (35.0, 60.0, "Lied")]
    assert fs.stuecke(0.0, [], [], []) == []


def test_angabe_am_rand_der_werbung_teilt_sie_nicht():
    # Spot beim Verbinden: die (leere) Angabe kommt 0,5 s nach dem Anfang, der nächste Titel genau am Ende
    liste = fs.stuecke(60.0, [fs.Angabe(0.5, ""), fs.Angabe(15.2, "Lied")], [], [fs.Werbung(0.0, 15.0, "otto.de")])
    assert [(s.von, s.bis, s.name) for s in liste] == [(0.0, 15.0, "Werbung: otto.de"), (15.0, 60.0, "Lied")]


def test_kein_splitter_vor_der_werbung():
    # Mangoradio 10:46: der Titel des Spots setzt seine Grenze 0,8 s vor die Werbestelle
    angaben = [fs.Angabe(0.0, "Mikolas Josef - Lie To Me"), fs.Angabe(646.0, "o2online.de - Ein bisschen ..."),
               fs.Angabe(666.0, "The Chainsmokers, ROZES - Roses")]
    liste = fs.stuecke(700.0, angaben, [(645.0, 645.25), (665.5, 665.7)], [fs.Werbung(646.08, 665.70, "o2online.de")])
    assert [(s.von, s.bis, s.name) for s in liste] == [
        (0.0, 646.08, "Mikolas Josef - Lie To Me"), (646.08, 665.6, "Werbung: o2online.de"),
        (665.6, 700.0, "The Chainsmokers, ROZES - Roses")]


def test_einschub_nach_langer_pause():
    # Mangoradio 2:25: Pause 142,32 bis 145,46, Einspieler ohne Titel (Angabe 146,0), kurze Stille 147,75 bis 147,94,
    # dann das nächste Lied (Angabe 148,0). Die lange Pause gehört dem Einspieler, nicht dem Lied.
    angaben = [fs.Angabe(21.0, "Alvaro Soler - Sofia"), fs.Angabe(146.0, ""), fs.Angabe(148.0, "Cash Cash - Tell It To My Heart")]
    liste = fs.stuecke(300.0, angaben, [(142.32, 145.46), (147.75, 147.94)], [])
    assert [(round(s.von, 3), round(s.bis, 3), s.name) for s in liste][2:] == [
        (145.31, 147.845, "Einschub"), (147.845, 300.0, "Cash Cash - Tell It To My Heart")]


def test_schnitt_in_der_pause():
    # lange Pause: 0,15 s vor ihrem Ende; kurze Pause (40 ms): in ihrer Mitte; ohne Pause genau am Wechsel
    assert fs.schnittstelle(323.16, [(320.54, 323.16)]) == 323.01
    assert fs.schnittstelle(29.89, [(29.85, 29.89)]) == 29.87
    assert fs.schnittstelle(50.0, [(29.85, 29.89)]) == 50.0


def test_pause_schlaegt_luecke_in_der_sprache():
    # PayPal-Spot (Mangoradio 21.11.2026): Angabe 30,0; 50-ms-Lücke in der Sprache 29,32 bis 29,35, echte Pause
    # 29,77 bis 29,89 (danach beginnt das Programm)
    assert fs.grenze(30.0, [(29.32, 29.35), (29.77, 29.89)]) == 29.89
