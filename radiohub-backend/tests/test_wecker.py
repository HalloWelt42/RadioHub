"""Wecker und Ort über die Schnittstelle."""


def test_wecker_anlegen_aendern_loeschen(client):
    sender = {"uuid": "u-1", "name": "Testwelle", "url": "http://welle.test/stream"}
    neu = client.post("/api/wecker", json={"zeit": "06:30", "tage": [5, 1, 1], "sender": sender}).json()
    assert neu["tage"] == [1, 5] and neu["sender"]["name"] == "Testwelle" and neu["aktiv"] is True
    assert client.post("/api/wecker", json={"zeit": "25:00", "sender": sender}).status_code == 422
    assert client.post("/api/wecker", json={"zeit": "07:00", "quelle": "podcast"}).status_code == 400
    geaendert = client.put(f"/api/wecker/{neu['id']}", json={"zeit": "07:15", "aktiv": False, "quelle": "podcast",
                                                             "podcast_id": 3}).json()
    assert geaendert["zeit"] == "07:15" and geaendert["aktiv"] is False and geaendert["podcast_id"] == 3
    assert any(w["id"] == neu["id"] for w in client.get("/api/wecker").json()["wecker"])
    assert client.delete(f"/api/wecker/{neu['id']}").status_code == 200
    assert client.delete(f"/api/wecker/{neu['id']}").status_code == 404


def test_ort_fuer_sonnenzeiten(client):
    assert client.put("/api/wecker/ort", json={"name": "Probeort", "breite": 50.9, "laenge": 6.9}).status_code == 200
    assert client.get("/api/wecker/ort").json() == {"name": "Probeort", "breite": 50.9, "laenge": 6.9}
    assert client.put("/api/wecker/ort", json={"breite": 99}).status_code == 422
