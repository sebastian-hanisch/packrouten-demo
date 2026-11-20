"""Jede Zahl der README wird hier aus data/prt_results.json nachgerechnet (DEMO-PLAYBOOK §11a). Die Spalte „Test“ der README nennt den Test.

Das Format der Zahlen (Dezimalkomma, Stellen) ist das der README; ein Test schlägt fehl, wenn die README eine andere Zahl nennt als die Datei."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

import prt_constants as K
import prt_results as R
import prt_texts as T

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
RES = R.load()
A, N = RES["aus"], RES["an"]


def de(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def pct(x, d=0):
    """Anteil 0 bis 1 als Prozent ohne Leerzeichen-Zeichen (Zahl)."""
    return de(x * 100.0, d)


def enthalten(*teile):
    fehlt = [t for t in teile if t not in README]
    assert not fehlt, f"nicht in der README: {fehlt}"


def zellen_klassen(cells):
    return R.count_classes(cells)


# ------------------------------------------------------------------------------------------------ Frage 1: Fläche

def test_claim_flaeche_zellenklassen():
    na, oa, da = zellen_klassen(A["m1"]["zellen"])
    nb, ob, db = zellen_klassen(N["m1"]["zellen"])
    assert (na, oa, da, nb, ob, db) == (25, 27, 12, 35, 10, 19)
    assert len(A["m1"]["zellen"]) == len(N["m1"]["zellen"]) == 64 and all(c["N"] == 12 for c in A["m1"]["zellen"] + N["m1"]["zellen"])
    enthalten("Von den 64 Zellen", "je 12 Instanzen, φ = 0,90", f"sind ohne Drehung {na} „Fläche reicht“", f"{oa} „Fläche reicht oft nicht“", f"und {da} Grenzfälle; mit Drehung {nb}, {ob} und {db}")
    ua, un = R.count_unsicher(A["m1"]["zellen"]), R.count_unsicher(N["m1"]["zellen"])
    assert (ua, un) == (30, 18) and ua >= oa and un >= ob                       # „unbekannt“ als Problem mitgezählt: Obergrenze zu „oft nicht“
    enthalten(f"sind es ohne Drehung {ua} und mit Drehung {un} Zellen")


def test_claim_flaeche_theta_und_nk():
    for cells, anteil_theta, anteil_nk in ((A["m1"]["zellen"], "2 / 4 / 9 / 12", "6 / 14 / 0 / 7"), (N["m1"]["zellen"], "0 / 2 / 3 / 5", "1 / 9 / 0 / 0")):
        je_theta = [sum(1 for c in cells if abs(c["theta"] - th) < 1e-9 and c["pmin"] >= K.M1_OFT) for th in K.THETA_CHOICES]
        assert " / ".join(str(x) for x in je_theta) == anteil_theta and all(sum(1 for c in cells if abs(c["theta"] - th) < 1e-9) == 16 for th in K.THETA_CHOICES)
        je_nk = [sum(1 for c in cells if (c["n"], c["k"]) == nk and c["pmin"] >= K.M1_OFT) for nk in ((20, 3), (20, 5), (40, 3), (40, 5))]
        assert " / ".join(str(x) for x in je_nk) == anteil_nk and all(sum(1 for c in cells if (c["n"], c["k"]) == nk) == 16 for nk in ((20, 3), (20, 5), (40, 3), (40, 5)))
        enthalten(anteil_theta, anteil_nk)
    assert [round(R.teile_je_fahrzeug(n, k), 1) for n, k in ((20, 3), (20, 5), (40, 3), (40, 5))] == [12.0, 7.2, 24.0, 14.4]
    enthalten("Teile je Fahrzeug im Erwartungswert 12,0 / 7,2 / 24,0 / 14,4")


def test_claim_flaeche_fuellgrad_form_und_teile():
    ba, bb = A["m1"]["m1b"], N["m1"]["m1b"]
    aus = (ba["gleich"], ba["gemischt"], ba["teile_le10"], ba["teile_ge11"])
    assert [(x["N"]) for x in aus] == [480, 461, 293, 648]
    enthalten(f"sind {de(100 * ba['gleich']['infeas'] / ba['gleich']['N'])} % der Touren der Form „gleich“ (480 Touren)", f"und {de(100 * ba['gemischt']['infeas'] / ba['gemischt']['N'])} % der Form „gemischt“ (461)",
              f"{de(100 * ba['teile_le10']['infeas'] / ba['teile_le10']['N'])} % (293)", f"{de(100 * ba['teile_ge11']['infeas'] / ba['teile_ge11']['N'])} % (648)")
    mit = [pct(bb[k]["infeas"] / bb[k]["N"]) for k in ("gleich", "gemischt", "teile_le10", "teile_ge11")]
    assert mit == ["34", "19", "66", "5"] and [bb[k]["N"] for k in ("gleich", "gemischt", "teile_le10", "teile_ge11")] == [389, 467, 293, 563]
    enthalten("mit Drehung 34 % (389) und 19 % (467), 66 % (293) und 5 % (563)")
    assert ba["mit_bekanntem_status"] == 941 and ba["touren_gesamt"] == 3739
    # Deutung: Anteil der Rechtecke der Form „gleich“, die breiter als die halbe Ladefläche sind (Zufalls-Seeds 610000 bis 610005, Depot Mitte, φ = 0,90)
    import prt_core as C
    def breiter(n, k):
        ws = [w for seed in range(610000, 610006) for c in C.make_instance(n, "mitte", seed, k, 0.90, "gleich").items[1:] for (w, _l) in c]
        return sum(1 for w in ws if w > K.W / 2), len(ws)
    b205 = breiter(20, 5)
    assert round(100 * b205[0] / b205[1]) == 69
    assert breiter(40, 3) == (0, 449) and breiter(40, 5) == (0, 449)
    gr = {(g["n"], g["k"], g["spread"]): g for g in A["m2_gruppen"]}
    assert gr[(40, 5, "gleich")]["dU"] > gr[(40, 5, "gemischt")]["dU"] and gr[(40, 3, "gleich")]["dU"] > gr[(40, 3, "gemischt")]["dU"]      # die Form zählt auch bei 40 Kunden
    enthalten("(69 % der Rechtecke bei φ = 0,90), bei 40 Kunden gar nicht (0 von 449 Rechtecken)")
    import re
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "(69 % der Rechtecke bei φ = 0,90)" in app and re.search(r"gar nicht", app)
    # Angaben zur Form „gleich“ nach der Skalierung in der Annahmentabelle (Breite / 40)
    def spanne(n, k):
        ws = [w for phi in (0.75, 0.90) for seed in range(610000, 610006) for c in C.make_instance(n, "mitte", seed, k, phi, "gleich").items[1:] for (w, _l) in c]
        return min(ws) / K.W, max(ws) / K.W
    lo5, hi5 = spanne(20, 5)
    lo3, hi3 = spanne(40, 3)
    assert (lo5 * K.W, hi5 * K.W) == (16, 28) and (lo3 * K.W, hi3 * K.W) == (9, 15)       # 0,40 bis 0,70 bzw. 0,225 bis 0,375 der Breite 40, beide φ
    assert "zwischen 0,40 und 0,70 der Ladefläche" in T.ASSUMPTIONS_MARKDOWN and "zwischen 0,23 und 0,38" in T.ASSUMPTIONS_MARKDOWN


def test_claim_kipp_theta():
    assert R.kipp(False, "mitte", 20, 5, "gleich") == 0.7 and R.kipp(False, "rand", 20, 5, "gleich") == 0.7
    assert R.kipp(True, "mitte", 20, 5, "gleich") == 0.8 and R.kipp(True, "rand", 20, 5, "gleich") == 0.8
    for rot in (False, True):
        for depot in K.DEPOT_CHOICES:
            for sp in K.SPREAD_CHOICES:
                assert R.kipp(rot, depot, 40, 3, sp) is None
    enthalten("bei 20 Kunden, 5 Ladungen, Form gleich ohne Drehung ab 0,70 (Depot Mitte und Rand), mit Drehung ab 0,80", "bei 40 Kunden und 3 Ladungen (24 Teile je Fahrzeug) in keiner Gruppe im Raster")
    assert R.kipp_gruppen(False) == (12, 16) and R.kipp_gruppen(True) == (5, 16)
    assert R.kipp_bereich(False, 20, 5) == (0.7, 0.8) and R.kipp_bereich(True, 20, 5) == (0.8, 1.0)
    assert all(key.split("|")[1] == "20" for key, v in N["kipp"].items() if v is not None)          # mit Drehung nur bei 20 Kunden
    enthalten("ohne Drehung 12 von 16, mit Drehung 5 von 16 (alle bei 20 Kunden)", "ohne Drehung ab 0,70 bis 0,80, mit Drehung ab 0,80 bis 1,00",
              "Ohne Drehung gibt es in 12 von 16 Gruppen", "nur in 5 von 16 Gruppen (bei 20 Kunden und 5 Ladungen ab 0,80 bis 1,00)")


# ------------------------------------------------------------------------------------------------ Frage 2 und 3

def test_claim_preis_des_packens():
    m, m96, mn = A["m2"], A["m2_96"], N["m2"]
    assert (m["N"], m96["N"], mn["N"]) == (192, 96, 96)
    enthalten(f"ohne Drehung im Mittel {de(m['dU_mean'])} % (Median {de(m['dU_median'])} %) über 192 Instanzen", f"ΔV +{de(m['dVU_mean'], 2)} Fahrzeuge",
              f"auf denselben 96 Instanzen ohne Drehung {de(m96['dU_mean'])} % (Median {de(m96['dU_median'])} %), mit Drehung {de(mn['dU_mean'])} % (Median {de(mn['dU_median'])} %)")
    assert m["U_unter_flaeche"] == 0 and mn["U_unter_flaeche"] == 0            # Konstruktion (Warmstarts), kein Befund


def test_claim_preis_nach_gruppen():
    ga = A["m2_gruppen"]
    lo, hi = min(ga, key=lambda g: g["dU"]), max(ga, key=lambda g: g["dU"])
    assert (lo["n"], lo["k"], lo["spread"], hi["n"], hi["k"], hi["spread"]) == (40, 3, "gemischt", 20, 5, "gleich") and lo["N"] == hi["N"] == 24
    gn = N["m2_gruppen"]
    lo2, hi2 = min(gn, key=lambda g: g["dU"]), max(gn, key=lambda g: g["dU"])
    assert (lo2["n"], lo2["k"], lo2["spread"], hi2["n"], hi2["k"], hi2["spread"]) == (20, 3, "gemischt", 20, 5, "gleich") and lo2["N"] == hi2["N"] == 12
    enthalten(f"von {de(lo['dU'])} % ((40, 3), gemischt, {de(lo['teile_je_fahrzeug'])} Teile je Fahrzeug) bis {de(hi['dU'])} % ((20, 5), gleich, {de(hi['teile_je_fahrzeug'])} Teile je Fahrzeug)",
              f"von {de(lo2['dU'])} % ((20, 3), gemischt) bis {de(hi2['dU'])} % ((20, 5), gleich)")
    za, zn = A["m2_zellen"], N["m2_zellen"]
    assert (sum(c["relU"] for c in za), sum(c["nonU"] for c in za), sum(c["relU"] for c in zn), sum(c["nonU"] for c in zn)) == (26, 1, 16, 2) and len(za) == len(zn) == 32
    z96 = A["m2_zellen_96"]
    assert (sum(c["relU"] for c in z96), sum(c["nonU"] for c in z96)) == (25, 1)
    enthalten("ohne Drehung auf 192 Instanzen 26 „spürbar“ und 1 „kaum“, auf denselben 96 Instanzen wie mit Drehung 25 und 1, mit Drehung 16 und 2",
              "in 25 von 32 Zellen ohne Drehung und in 16 von 32 Zellen mit Drehung spürbar (beide auf denselben 96 Instanzen; mit allen 192 Instanzen ohne Drehung 26;")


def test_claim_preis_der_reihenfolge():
    m, mn = A["m2"], N["m2"]
    enthalten(f"ohne Drehung im Mittel {de(m['dL_mean'])} % (Median {de(m['dL_median'])} %, 192 Instanzen)", f"mit Drehung {de(mn['dL_mean'])} % (Median {de(mn['dL_median'])} %, 96 Instanzen)")
    za, zn = A["m2_zellen"], N["m2_zellen"]
    assert (sum(c["relL"] for c in za), sum(c["nonL"] for c in za), sum(c["relL"] for c in zn), sum(c["nonL"] for c in zn)) == (20, 2, 12, 8)
    z96 = A["m2_zellen_96"]
    assert (sum(c["relL"] for c in z96), sum(c["nonL"] for c in z96)) == (20, 1)
    m96 = A["m2_96"]
    enthalten("ohne Drehung 20 / 2 (auf den 96 Instanzen 20 / 1), mit Drehung 12 / 8 (von 32)",
              f"auf denselben 96 Instanzen wie mit Drehung {de(m96['dL_mean'])} % (Median {de(m96['dL_median'])} %)")
    assert m["L_unter_U"] == 0 and mn["L_unter_U"] == 0                       # Konstruktion, kein Befund


def test_claim_reparatur_gegen_suche():
    a, n = A["m2"]["rep_U"], N["m2"]["rep_U"]
    enthalten(f"roh im Mittel {de(a['roh_mean'])} %, mit lokaler Suche {de(a['ls_mean'])} % (Median {de(a['ls_median'])} %), höchstens 1 % in {a['ls_le1']} von 192 Instanzen",
              f"mit Drehung {de(n['roh_mean'])} % und {de(n['ls_mean'])} % (Median {de(n['ls_median'])} %), {n['ls_le1']} von 96")
    assert a["roh_unter_suche"] == a["ls_unter_suche"] == n["roh_unter_suche"] == n["ls_unter_suche"] == 0          # Konstruktion: die Suche startet aus der Reparatur
    ru, rn = A["m2"]["regel_U"], N["m2"]["regel_U"]
    assert (ru["unter_suche"], ru["N_mit_regel"], rn["unter_suche"], rn["N_mit_regel"]) == (8, 168, 3, 96)
    enthalten("die Lücke der Reparatur ist nie negativ (0 von 192 Instanzen ohne, 0 von 96 mit Drehung)",
              "die Faustregel liegt in 8 von 168 Instanzen ohne Drehung und in 3 von 96 mit Drehung unter der Suche")


def test_claim_faustregel():
    a, n = A["m2"]["regel_U"], N["m2"]["regel_U"]
    va, vn = a["verteilung"], n["verteilung"]
    assert sum(va.values()) == 192 and sum(vn.values()) == 96 and a["N_mit_regel"] == 168
    enthalten(f"ohne Drehung θ = 0,9 in {va['0.9']} von 192 Instanzen, 0,8 in {va['0.8']}, 0,7 in {va['0.7']}, keine Regel in {va['keine']}",
              f"Mehrkosten gegen die Suche im Mittel {de(a['mehrkosten_mean'])} % (Median {de(a['mehrkosten_median'])} %, {a['N_mit_regel']} Instanzen mit Regel)",
              f"Mit Drehung (96 Instanzen): {vn['0.9']}, {vn['0.8']}, {vn['0.7']} und keine Regel in {vn.get('keine', 0)}; Mehrkosten {de(n['mehrkosten_mean'])} % (Median {de(n['mehrkosten_median'])} %)")
    v96 = A["m2_96"]["regel_U"]["verteilung"]
    enthalten(f"Auf denselben 96 Instanzen ohne Drehung: θ = 0,9 in {v96['0.9']}, keine Regel in {v96['keine']}")


# ------------------------------------------------------------------------------------------------ Kontrollen

def test_claim_guete_der_suche():
    ma, mn = A["m6"], N["m6"]
    assert ma["N"] == mn["N"] == 40 and ma["gap_mean"] == mn["gap_mean"] == 0.0 and ma["unter_optimum"] == mn["unter_optimum"] == 0
    enthalten("(40 Instanzen): mittlere Lücke ohne und mit Drehung je 0,000 %, nie unter dem Optimum",
              f"{de(-ma['flaeche_gegen_orakel'])} % (ohne Drehung) bzw. {de(-mn['flaeche_gegen_orakel'])} % (mit Drehung) unter dem Optimum")
    aa, an = A["a"], N["a"]
    enthalten(f"im Mittel {de(aa['gap_mean'], 2)} % billiger ({aa['N']} Instanzen ohne Drehung, {aa['gap_gt2']} über 2 %)", f"bzw. {de(an['gap_mean'], 2)} % ({an['N']} Instanzen mit Drehung, {an['gap_gt2']} über 2 %)")
    k2 = A["k2"]
    assert k2["N"] == 32
    enthalten(f"(Nachmessung, 32 Instanzen, ohne Drehung) die Kosten im Mittel um {de(-k2['dU_mean'], 2)} % (bei {k2['unveraendert']} Instanzen unverändert, bei {k2['mehr_als_05']} um mehr als 0,5 %)")
    ko_a, ko_n = RES["kontrollen"]["aus"], RES["kontrollen"]["an"]
    va, vn, cba, cbn = ko_a["v_live_gegen_gespeichert"], ko_n["v_live_gegen_gespeichert"], ko_a["c_gegen_b"], ko_n["c_gegen_b"]
    enthalten(f"die Live-Suche (100 Iterationen, {va['N']} Instanzen) lag im Mittel {de(-va['mean'], 2)} % (ohne Drehung; größte Einsparung {de(va['beste_einsparung'], 2)} %) bzw. {de(-vn['mean'], 2)} % (mit Drehung)",
              f"unterbot diese Suche in {cba['billiger']} von {cba['N']} Instanzen ohne Drehung (bis {de(cba['beste_einsparung'], 2)} %) und in {cbn['billiger']} von {cbn['N']} mit Drehung (bis {de(cbn['beste_einsparung'], 2)} %)")


def test_claim_heuristik_gegen_exakt():
    ua, la, un, ln = A["m7"]["U"], A["m7"]["L"], N["m7"]["U"], N["m7"]["L"]
    assert ua["touren"] == la["touren"] == un["touren"] == ln["touren"] == 360
    p = lambda x: de(100 * x["heur_nein_exakt_ja"] / x["bekannt"])  # noqa: E731
    enthalten(f"ohne Drehung U {ua['heur_nein_exakt_ja']} von {ua['bekannt']} ({p(ua)} %) und L {la['heur_nein_exakt_ja']} von {la['bekannt']} ({p(la)} %)",
              f"mit Drehung U {un['heur_nein_exakt_ja']} von {un['bekannt']} ({p(un)} %) und L {ln['heur_nein_exakt_ja']} von {ln['bekannt']} ({p(ln)} %)")
    hi_a, hi_n = ua["je_fuellgrad"][-1], un["je_fuellgrad"][-1]
    assert (hi_a["lo"], hi_n["lo"]) == (0.9, 0.9)
    enthalten(f"bei Füllgrad ab 0,9 U {hi_a['gap']} von {hi_a['bekannt']} ({pct(hi_a['gap'] / hi_a['bekannt'])} %)", f"bei Füllgrad ab 0,9 U {hi_n['gap']} von {hi_n['bekannt']} ({pct(hi_n['gap'] / hi_n['bekannt'])} %)")
    unter = ua["je_fuellgrad"][0], ua["je_fuellgrad"][1]
    assert sum(x["gap"] for x in unter) == 0 and sum(x["bekannt"] for x in unter) == 164
    enthalten("unter Füllgrad 0,8 U 0 von 164 (ohne Drehung)")


def test_claim_unbekannt():
    ba, bb = A["m1"]["m1b"], N["m1"]["m1b"]
    assert (ba["unbekannt"], bb["unbekannt"], ba["touren_gesamt"], bb["touren_gesamt"]) == (66, 151, 3739, 3739)
    enthalten("66 von 3 739 ohne Drehung, 151 von 3 739 mit Drehung")
    m96, mn = A["m2_96"], N["m2"]
    tausend = lambda x: f"{int(round(x)):,}".replace(",", " ")  # noqa: E731
    enthalten(f"im Mittel {tausend(m96['exakt_je_instanz'])}, davon {tausend(m96['unbekannt_je_instanz'])} unbekannt (ohne Drehung, 96 Instanzen), {tausend(mn['exakt_je_instanz'])} und {tausend(mn['unbekannt_je_instanz'])} (mit Drehung)")


def test_claim_robustheit():
    ka, kn = RES["kontrollen"]["aus"], RES["kontrollen"]["an"]
    enthalten(f"ohne Drehung −{de(abs(ka['c1_rho']['gleich']), 2)} (gleich) und −{de(abs(ka['c1_rho']['gemischt']), 2)} (gemischt), mit Drehung −{de(abs(kn['c1_rho']['gleich']), 2)} und −{de(abs(kn['c1_rho']['gemischt']), 2)}")
    assert ka["c1_n"] == kn["c1_n"] == 64                                   # 64 Instanzen; die Zahl der Zellen (12 je Form) steht im Bericht der Messreihe, nicht in der Datei
    for lay in ("lang", "kompakt", "palette"):
        assert ka["c2_nie_oft"][lay][0] >= 1 and ka["c2_nie_oft"][lay][1] >= 1 and kn["c2_nie_oft"][lay][0] >= 1 and kn["c2_nie_oft"][lay][1] >= 1
    enthalten(f"bei lang in {ka['c2_nahe']['lang']} (ohne Drehung) bzw. {kn['c2_nahe']['lang']} (mit Drehung) von 8 Gruppen, bei kompakt in {ka['c2_nahe']['kompakt']} bzw. {kn['c2_nahe']['kompakt']} von 8; darunter sind ohne Drehung {ka['c2_nahe_beide_nie']['lang']} und {ka['c2_nahe_beide_nie']['kompakt']}, mit Drehung {kn['c2_nahe_beide_nie']['lang']} und {kn['c2_nahe_beide_nie']['kompakt']} Gruppen, in denen beide „nie im Raster“ haben")
    assert (ka["c2_nahe_beide_nie"], kn["c2_nahe_beide_nie"]) == ({"lang": 2, "kompakt": 1}, {"lang": 2, "kompakt": 6})


def test_claim_plattform():
    ka, kn = RES["kontrollen"]["aus"], RES["kontrollen"]["an"]
    assert (ka["e_identisch"], ka["e_zeilen"], kn["e_identisch"], kn["e_zeilen"], ka["e_wechsel"], kn["e_wechsel"]) == (12, 12, 12, 12, 0, 0)
    enthalten("12 von 12 Zeilen mit denselben Kosten", f"in {pct(ka['e_status_gleich'])} % (ohne Drehung) bzw. {de(100 * kn['e_status_gleich'])} % (mit Drehung) von 480 Prüfungen gleich", "nie ein Wechsel zwischen packbar und nicht packbar")


def test_claim_rechenzeit():
    ka, kn = RES["kontrollen"]["aus"], RES["kontrollen"]["an"]
    m96, mn = A["m2_96"], N["m2"]
    enthalten(f"im Mittel {de(kn['d_t40_mean'])} s, größter Wert {de(kn['d_t_max'])} s (mit Drehung; {de(ka['d_t40_mean'])} s und {de(ka['d_t_max'])} s ohne Drehung unter fremder Last)",
              f"im Mittel {m96['zeit_mittel_s']:.0f} s ohne und {mn['zeit_mittel_s']:.0f} s mit Drehung")
    assert ka["d_n40"] == kn["d_n40"] == 10
    enthalten(f"bei 40 Kunden ({kn['d_n40']} Instanzen, Form gemischt, Depot Rand) im Mittel")
    # Live-Suche bei 20 Kunden (Prüflauf beim Bau, nicht im Test): die Angabe der App und der README ist ein und derselbe Text
    assert "30 bis 80 Sekunden ohne und 90 bis 105 Sekunden mit Drehung" in K.LIVE_SUCHE_ZEIT
    enthalten("lokal gemessen etwa 30 bis 80 Sekunden ohne und 90 bis 105 Sekunden mit Drehung (Wanduhr, unter Last, acht Läufe)")


def test_claim_pruefer_fehler_stehen_in_readme_und_app():
    ka, kn = RES["kontrollen"]["aus"]["pruefer"], RES["kontrollen"]["an"]["pruefer"]
    assert (ka["m2_fehler"], ka["m2_n"], kn["m2_fehler"], kn["m2_n"]) == (0, 192, 5, 96)
    assert (ka["c1_fehler"], ka["c1_n"], kn["c1_fehler"], kn["c1_n"]) == (2, 64, 2, 64) and (ka["a_c_fehler"], kn["a_c_fehler"], kn["a_c_n"]) == (0, 1, 8)
    enthalten("in der Frage 2 ohne Drehung 0 von 192 Lösungen, mit Drehung 5 von 96, dazu 2 von 64 in der Kontrolle der Teile je Kunde (ohne wie mit Drehung) und 1 von 8 beim kalten Lauf mit Drehung",
              "in den 6 Fällen mit gespeicherter Tour fand CP-SAT mit mehr Zeit eine bestätigte Packung")
    zeile = next(r for r in T.METHODS_ROWS if r[0] == "Unabhängiger Prüfer")[1]
    assert "0 von 192 Lösungen, mit Drehung 5 von 96" in zeile and "2 von 64" in zeile and "1 von 8" in zeile


def test_beispiel_mit_drei_kunden_in_der_app_passt_zur_gezeichneten_packung():
    """Die Erklärung unter der Zeichnung (app.py) nennt die tatsächlich verletzte Stelle: C (später besucht) steht vor B (früher besucht)."""
    import prt_pack as P
    ex = [(0, 25, 30), (1, 30, 60), (2, 15, 40)]                                          # A, B, C in der Reihenfolge des Besuchs
    status, place, _ = P.exact_pack(ex, False, False, 2.0)
    assert status == "feas"
    rects = {i: (x, y, l, w) for (i, w, l), (x, y) in zip(ex, place)}                    # x = Längsrichtung (Tür bei x = 100), y = Breite
    def verletzt(frueh, spaet):                                                           # später besuchter Kunde steht vor (näher an der Tür) dem früher besuchten, y-Bereiche überlappen
        xf, yf, lf, wf = rects[frueh]
        xs, ys, ls, ws = rects[spaet]
        return xs + ls > xf and min(yf + wf, ys + ws) > max(yf, ys)
    assert [verletzt(a, b) for a, b in ((0, 1), (0, 2), (1, 2))] == [False, False, True]    # A–B frei, A–C ohne Überlappung der Breite, nur B–C verletzt
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "B liegt hinten, A und C liegen nebeneinander vor der Tür" in app and "blockiert dann C, das erst nach B beliefert wird, das Teil B" in app
    assert P.exact_pack(ex, True, False, 2.0)[0] == "infeas" and P.exact_pack([(0, 15, 40), (1, 30, 60), (2, 25, 30)], True, False, 2.0)[0] == "infeas"


def test_keine_alten_formulierungen_in_app_und_readme():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    for alt in ("kann keine 2D-Packung", "der Löser kann keine", "wenige Dutzend Sekunden", "etwa 20 bis 90 Sekunden", "die Lücke ist deshalb nie negativ", "kennt keinen Löser",
                "Hook-Aussage", "Ampel", "Vormessung", "fliegt"):
        assert alt not in README and alt not in app and alt not in "".join(" ".join(r) for r in T.METHODS_ROWS), alt
    assert "Die Preise sind Obergrenzen" not in app and "Preise sind Obergrenzen" not in README


# ------------------------------------------------------------------------------------------------ Text der App gleich Text der README, Testzahl

def test_annahmen_tabelle_der_app_steht_wortgleich_in_der_readme():
    assert T.ASSUMPTIONS_MARKDOWN in README


def test_die_testzahl_der_readme_stimmt_mit_der_suite_ueberein():
    """`pytest --collect-only` zählt die Tests der Suite (ein Unterprozess; die Zählung steht in der README: „Die Suite hat N Tests“)."""
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", str(ROOT / "tests")], capture_output=True, text=True, timeout=600, cwd=str(ROOT))
    zeile = next(line for line in out.stdout.splitlines() if " tests collected" in line or " test collected" in line)
    anzahl = int(zeile.split()[0])
    assert f"Die Suite hat {anzahl} Tests." in README, f"README nennt eine andere Testzahl als die Suite ({anzahl})"


def test_readme_nennt_den_test_zu_jeder_befund_zeile():
    namen = {n.name for n in ast.walk(ast.parse(Path(__file__).read_text(encoding="utf-8"))) if isinstance(n, ast.FunctionDef)}
    zeilen = [z for z in README.split("## Befunde (gemessen, keine Behauptungen)")[1].split("## Befunde und Korrekturen")[0].splitlines() if z.startswith("| ") and "`test_claim" in z]
    assert len(zeilen) >= 15
    for z in zeilen:
        test = z.split("`")[-2]
        assert test in namen, f"{test} steht in der README, aber nicht in tests/test_claims.py"


def test_readme_nennt_keine_umgangssprache_und_keine_plan_begriffe():
    for wort in ("Saatwert", "Phase 0", " trägt ", " tragen ", "AP 0", "Hook-Aussage"):
        assert wort not in README, wort
    assert "Zufalls-Seed" in README
