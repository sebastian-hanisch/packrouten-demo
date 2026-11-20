"""Ergebnisdatei data/prt_results.json: Aufbau, Zellen-Zuordnung, Schwellen der Urteile, gespeicherte Lösungen gegen eine Neuberechnung der Kosten."""

import pytest

import prt_constants as K
import prt_core as C
import prt_results as R

RES = R.load()


def test_datei_ist_klein_und_hat_beide_stellungen():
    assert R.PATH.stat().st_size < 300_000
    assert set(RES) >= {"aus", "an", "kontrollen"}
    for s in ("aus", "an"):
        assert set(RES[s]) >= {"m1", "kipp", "m2_zellen", "m2", "m2_gruppen", "m6", "m7", "instanzen", "a"}


@pytest.mark.parametrize("s", ["aus", "an"])
def test_m1_hat_64_zellen_mit_je_12_instanzen_und_alle_kombinationen(s):
    cells = RES[s]["m1"]["zellen"]
    assert len(cells) == 64 and RES[s]["m1"]["instanzen"] == 192
    assert {(c["depot"], c["n"], c["k"], c["spread"], c["theta"]) for c in cells} == {
        (d, n, k, sp, th) for d in K.DEPOT_CHOICES for (n, k) in ((20, 3), (20, 5), (40, 3), (40, 5)) for sp in K.SPREAD_CHOICES for th in K.THETA_CHOICES}
    assert all(c["N"] == 12 for c in cells)
    assert all(0 <= c["pmin"] <= c["pmax"] <= 1 for c in cells)           # nachweislich nicht packbar <= nicht packbar oder unbekannt


@pytest.mark.parametrize("s,N,per_cell", [("aus", 192, 6), ("an", 96, 3)])
def test_m2_hat_32_zellen(s, N, per_cell):
    cells = RES[s]["m2_zellen"]
    assert len(cells) == 32 and RES[s]["m2"]["N"] == N and all(c["N"] == per_cell for c in cells)
    assert {(c["depot"], c["n"], c["k"], c["spread"], c["phi"]) for c in cells} == {
        (d, n, k, sp, phi) for d in K.DEPOT_CHOICES for (n, k) in ((20, 3), (20, 5), (40, 3), (40, 5)) for sp in K.SPREAD_CHOICES for phi in K.PHI_CHOICES}


@pytest.mark.parametrize("s", ["aus", "an"])
def test_die_gespeicherten_urteile_folgen_den_schwellen(s):
    """Die Flags in der Datei sind aus den Zahlen der Zelle mit den Schwellen der Konstanten gerechnet (nicht von Hand gesetzt)."""
    for c in RES[s]["m2_zellen"]:
        assert c["relU"] == (c["dU"] >= K.M2_REL_MEAN and c["dU1"] >= K.M2_REL_SHARE1)
        assert c["nonU"] == (c["dU"] < K.M2_NON_MEAN)
        assert c["relL"] == (c["dL"] >= K.M3_REL_MEAN and c["dL05"] >= K.M3_REL_SHARE05)
        assert c["nonL"] == (c["dL"] < K.M3_NON_MEAN)
        assert c["okU"] == (c["repU"] <= K.M4_OK_REP and c["repUV"] <= K.M4_OK_DV)
        assert c["badU"] == (c["repU"] >= K.M4_BAD_REP or c["repUV"] >= K.M4_BAD_DV)
        assert not (c["relU"] and c["nonU"]) and not (c["okU"] and c["badU"])


def test_zellen_zuordnung_und_klassen():
    c = R.m1_cell(False, "mitte", 20, 3, "gemischt", 0.9)
    assert c["N"] == 12 and c["pmin"] == pytest.approx(0.0833, abs=1e-3)
    assert R.m1_cell(False, "mitte", 20, 3, "gemischt", 0.95) is None           # nur die gemessenen Stufen
    assert R.m2_cell(True, "rand", 40, 5, "gleich", 0.75)["N"] == 3
    assert R.m2_cell(True, "rand", 30, 5, "gleich", 0.75) is None
    nie, oft, mid = R.count_classes(RES["aus"]["m1"]["zellen"])
    assert nie + oft + mid == 64
    assert R.teile_je_fahrzeug(20, 5) == pytest.approx(7.2) and R.teile_je_fahrzeug(40, 3) == pytest.approx(24.0)


def test_kipp_theta_ist_das_kleinste_theta_mit_oft():
    for s in ("aus", "an"):
        for key, th in RES[s]["kipp"].items():
            depot, n, k, sp = key.split("|")
            cells = [c for c in RES[s]["m1"]["zellen"] if (c["depot"], c["n"], c["k"], c["spread"]) == (depot, int(n), int(k), sp)]
            oft = sorted(c["theta"] for c in cells if c["pmin"] >= K.M1_OFT)
            assert th == (oft[0] if oft else None)
    assert R.kipp(False, "mitte", 20, 5, "gleich") == 0.7 and R.kipp(False, "mitte", 40, 3, "gleich") is None


@pytest.mark.parametrize("s", ["aus", "an"])
def test_gespeicherte_loesungen_stimmen_mit_den_kosten_ueberein(s):
    """Jede gespeicherte M2-Instanz mit 20 Kunden und jedes Preset: Routen decken alle Kunden genau einmal ab, und Fahrzeuge, Distanz und Kosten sind die der Routen."""
    n_checked = 0
    for key, rec in RES[s]["instanzen"].items():
        depot, n, k, sp, phi, seed = key.split("|")
        if int(n) != 20 and int(seed) < 740000:
            continue
        inst = C.make_instance(int(n), depot, int(seed), int(k), float(phi), sp)
        for mode in ("U", "L"):
            routes = rec["routes"][mode]
            assert sorted(c for r in routes for c in r) == list(range(1, inst.n + 1)), key
            V, D, cost = C.stats(inst, routes, C.F_FIX)
            assert (V, cost) == (rec[mode]["V"], rec[mode]["cost"]) and abs(D - rec[mode]["D"]) < 1e-9, (key, mode)
        n_checked += 1
    assert n_checked >= (96 if s == "aus" else 48)


@pytest.mark.parametrize("s", ["aus", "an"])
def test_konstruktionsmonotonie_der_gespeicherten_loesungen(s):
    """Fläche <= U <= L und Suche <= Reparatur gelten durch die Warmstarts (Bauart, kein Befund); hier nur festgehalten, damit niemand sie als Messergebnis liest."""
    for key, rec in RES[s]["instanzen"].items():
        assert rec["area_best"]["cost"] <= rec["U"]["cost"] <= rec["L"]["cost"], key
        assert rec["U"]["cost"] <= rec["repls_U"]["cost"] and rec["L"]["cost"] <= rec["repls_L"]["cost"], key


def test_stored_record_lookup_und_schluessel():
    rec = R.stored_record(False, "mitte", 20, 5, "gleich", 0.9, 610000)
    assert rec is not None and "U" in rec and "L" in rec and rec["routes"]["U"]
    assert R.stored_record(False, "mitte", 20, 5, "gleich", 0.9, 4711) is None
    assert R.instance_key("mitte", 20, 5, "gleich", 0.9, 610000) == "mitte|20|5|gleich|0.90|610000"
    for name, p in K.PRESETS.items():                                       # jedes Preset ist in beiden Stellungen gespeichert
        for rot in (False, True):
            assert R.stored_record(rot, p["depot"], p["n"], p["k"], p["spread"], p["phi"], p["seed"]) is not None, (name, rot)


def test_fuellgrad_klassen_sind_vollstaendig():
    for rot in (False, True):
        for form in K.SPREAD_CHOICES:
            bins = R.fill_share(rot, form)
            assert [(lo, hi) for lo, hi, _, _ in bins] == list(K.FILL_BINS)
            assert all(a is None or 0 <= a <= 1 for _, _, _, a in bins)
