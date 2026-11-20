"""Verdikte als reine Funktionen: Schwellen und jede Zahl im Text an handgesetzten Zellen; Zahlenformat mit Dezimalkomma."""

import pytest

import prt_evaluation as E


def cell1(pmin, pmax, N=12):
    return {"N": N, "pmin": pmin, "pmax": pmax}


def cell2(**kw):
    base = {"N": 6, "dU": 4.8, "dU1": 0.67, "relU": False, "nonU": False, "dL": 1.1, "dL05": 0.5, "relL": False, "nonL": False,
            "repU": 0.7, "rep0U": 4.5, "repUV": 0.17, "okU": False, "badU": False}
    base.update(kw)
    return base


# ------------------------------------------------------------------------------------------------ Format

def test_zahlenformat_mit_dezimalkomma():
    assert E.fz(1.26, 1) == "1,3" and E.fz(1.0, 2) == "1,00"
    assert E.fz(12.0, 1) == "12,0" and E.fpct(8.9) == "8,9 %" and E.fshare(0.5) == "50 %" and E.fshare(0.083, 1) == "8,3 %"
    assert E.theta_text(0.9) == "0,90" and E.rot_text(True) == "mit Drehung" and E.rot_text(False) == "ohne Drehung"
    assert "." not in E.fpct(3.14159, 2)


def test_rel_und_preise():
    assert E.rel(110, 100) == pytest.approx(10.0) and E.rel(5, 0) == 0.0                     # Nenner 0: keine Aussage statt Division durch 0
    rec = {"U": {"cost": 6395}, "L": {"cost": 6395}, "area_best": {"cost": 5864}}
    assert E.price_packing(rec) == pytest.approx((6395 - 5864) / 5864 * 100)
    assert E.price_order(rec) == 0.0
    assert E.gap_to_search(7000, rec, "U") == pytest.approx((7000 - 6395) / 6395 * 100)


# ------------------------------------------------------------------------------------------------ Frage 1: Fläche

@pytest.mark.parametrize("pmin,pmax,klasse,art", [(0.0, 0.10, "nie", "success"), (0.0, 0.11, "dazwischen", "info"), (0.49, 0.9, "dazwischen", "info"),
                                                   (0.50, 0.50, "oft", "warning"), (0.50, 1.0, "oft", "warning")])
def test_flaeche_klassen_an_den_schwellen(pmin, pmax, klasse, art):
    assert E.m1_class(cell1(pmin, pmax)) == klasse
    kind, text = E.verdict_flaeche(cell1(pmin, pmax), 0.9, False)
    assert kind == art and "12 Instanzen" in text and "ohne Drehung" in text and "θ = 0,90" in text


def test_flaeche_text_nennt_die_anteile_und_die_stellung():
    kind, text = E.verdict_flaeche(cell1(0.4167, 0.5833), 1.0, True)
    assert "42 %" in text and "58 %" in text and "mit Drehung" in text and "θ = 1,00" in text and kind == "info"


def test_flaeche_bei_phi_075_nennt_die_zuordnung_zur_zelle_bei_090():
    assert "φ = 0,90" in E.verdict_flaeche(cell1(0, 0), 0.9, False, 0.75)[1]
    assert "φ = 0,90" not in E.verdict_flaeche(cell1(0, 0), 0.9, False, 0.90)[1]
    assert "0,90" in E.zelle_phi_hinweis(0.75) and E.zelle_phi_hinweis(0.9) == ""


def test_fehlende_zelle_wird_gemeldet_statt_geraten():
    for fn in (lambda: E.verdict_flaeche(None, 0.9, False), lambda: E.verdict_packen(None, False), lambda: E.verdict_reparatur(None, False), lambda: E.verdict_reihenfolge(None, False)):
        kind, text = fn()
        assert kind == "info" and "keine Zelle" in text


# ------------------------------------------------------------------------------------------------ Frage 2 bis 3 und Zusatz

def test_packen_drei_zustaende_und_zahlen():
    kind, text = E.verdict_packen(cell2(relU=True), False)
    assert kind == "warning" and "4,8 %" in text and "67 %" in text and "6 Instanzen" in text and "θ = 1,00" in text
    assert E.verdict_packen(cell2(nonU=True, dU=0.3), True)[0] == "success"
    assert "mit Drehung" in E.verdict_packen(cell2(), True)[1]
    assert E.verdict_packen(cell2(), False)[0] == "info"


def test_packen_zwischenfall_nennt_die_bedingungen_statt_weniger_als_die_schwelle():
    """Mittel über der Schwelle, aber nicht in der Hälfte der Instanzen ≥ 1 %: die Meldung darf nicht „weniger als die Schwelle“ sagen (Prüfer-Befund B4)."""
    import prt_results as R
    cell = R.m2_cell(True, "mitte", 20, 5, "gleich", 0.75)
    assert cell["dU"] > 4.0 and not cell["relU"] and not cell["nonU"]
    kind, text = E.verdict_packen(cell, True)
    assert kind == "info" and "nicht beide Bedingungen für „spürbar“" in text and "weniger als" not in text
    for rot in (False, True):
        for c in R.block(rot)["m2_zellen"]:
            _, t1 = E.verdict_packen(c, rot)
            _, t2 = E.verdict_reihenfolge(c, rot)
            if c["dU"] >= 2.0:
                assert "weniger als die Schwelle" not in t1
            if c["dL"] >= 1.0 and not c["relL"]:
                assert "kostet hier wenig" not in t2 and "nicht beide Bedingungen" in t2


def test_reparatur_drei_zustaende_und_zahlen():
    kind, text = E.verdict_reparatur(cell2(okU=True), False)
    assert kind == "success" and "0,7 %" in text and "4,5 %" in text and "0,17 Fahrzeuge" in text
    assert E.verdict_reparatur(cell2(badU=True), False)[0] == "warning"
    assert E.verdict_reparatur(cell2(), False)[0] == "info"


def test_reihenfolge_drei_zustaende_und_zahlen():
    kind, text = E.verdict_reihenfolge(cell2(relL=True, dL=3.5, dL05=0.83), False)
    assert kind == "warning" and "3,5 %" in text and "83 %" in text
    assert E.verdict_reihenfolge(cell2(nonL=True), False)[0] == "success"
    assert E.verdict_reihenfolge(cell2(), True)[0] == "info"


# ------------------------------------------------------------------------------------------------ eine Instanz

def _t(u, l, **kw):
    return {"u": u, "l": l, **kw}


def test_instanz_zaehlung_und_art():
    infos = [_t("feas", "feas"), _t("infeas", "infeas"), _t("unknown", "unknown"), _t("feas", "infeas")]
    kind, text = E.verdict_instanz(infos, infos, 0.9, False)
    assert kind == "warning"
    assert "von 4 Touren" in text and "ohne Reihenfolge 2 packbar, 1 nachweislich nicht packbar, 1 unbekannt" in text and "mit Entladereihenfolge 1 packbar, 2 nachweislich nicht packbar, 1 unbekannt" in text
    assert E.verdict_instanz([_t("feas", "feas")], [_t("feas", "feas")], 0.9, True)[0] == "success"
    assert E.verdict_instanz([_t("feas", "feas"), _t("unknown", "unknown")], [_t("feas", "feas"), _t("unknown", "unknown")], 0.9, True)[0] == "info"
    assert E.count_status(infos, "l") == {"feas": 1, "infeas": 2, "unknown": 1}


def test_instanz_ohne_entladereihenfolge_bei_40_kunden_sagt_es_ausdruecklich():
    infos = [_t("feas", "skip"), _t("unknown", "skip")]
    kind, text = E.verdict_instanz(infos, infos, 0.9, False, with_l=False)
    assert kind == "info" and "ohne Reihenfolge 1 packbar, 0 nachweislich nicht packbar, 1 unbekannt" in text and "bei 40 Kunden live nicht geprüft" in text
    assert "mit Entladereihenfolge 1 packbar" not in text


def test_suche_text_nennt_basis_und_obergrenze():
    rec = {"U": {"cost": 6395}, "L": {"cost": 6710}, "area_best": {"cost": 5864}}
    kind, text = E.verdict_suche(rec)
    assert kind == "warning" and "9,1 %" in text and "4,9 %" in text and "θ = 1,00" in text and "Obergrenzen" in text
    rec2 = {"U": {"cost": 5900}, "L": {"cost": 5900}, "area_best": {"cost": 5864}}
    assert E.verdict_suche(rec2)[0] == "info"


def test_unterschrift_der_ladeflaeche_nennt_status_fuellgrad_und_teile_ohne_platz():
    t = {"u": "infeas", "l": "infeas", "fill": 0.74, "parts": 4, "u_left": [3]}
    assert E.tour_caption(t) == "nachweislich nicht packbar; Füllgrad 74 %, 4 Teile; in der einfachen Teil-Packung bleibt 1 Teil ohne Platz"
    assert E.tour_caption({**t, "u_left": [1, 3]}).endswith("bleiben 2 Teile ohne Platz")
    ok = {"u": "feas", "l": "skip", "fill": 0.9, "parts": 10, "u_left": []}
    assert E.tour_caption(ok) == "packbar; Füllgrad 90 %, 10 Teile" and E.tour_caption(ok, "l") == "nicht geprüft; Füllgrad 90 %, 10 Teile"
