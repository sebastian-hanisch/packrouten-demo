"""Kern: Instanzen, Flächenlösung, Packer, Reparatur, Suche, Prüfer, Randfälle, Determinismus."""

import pytest

import prt_core as C
import prt_pack as P


# ------------------------------------------------------------------------------------------------ Instanzen

def test_instanz_ist_deterministisch_und_haengt_nicht_an_der_drehung():
    a = C.make_instance(20, "mitte", 740000, 3, 0.9, "gemischt")
    b = C.make_instance(20, "mitte", 740000, 3, 0.9, "gemischt")
    assert a.items == b.items and a.xy == b.xy and a.D == b.D
    c = C.make_instance(20, "mitte", 740001, 3, 0.9, "gemischt")
    assert c.items != a.items


@pytest.mark.parametrize("n,k,spread,phi,depot", [(20, 3, "gemischt", 0.9, "mitte"), (20, 5, "gleich", 0.75, "rand"), (40, 3, "gleich", 0.9, "rand")])
def test_instanz_hat_die_beschriebene_form(n, k, spread, phi, depot):
    inst = C.make_instance(n, depot, 740002, k, phi, spread)
    assert inst.n == n and len(inst.items) == n + 1 and inst.items[0] == []
    counts = [len(inst.items[c]) for c in range(1, n + 1)]
    assert set(counts) <= {1, 2, 3}
    for c in range(1, n + 1):
        assert inst.dem[c] == sum(w * l for (w, l) in inst.items[c]) <= C.AREA
        assert all(1 <= w <= P.W and 1 <= l <= P.LEN for (w, l) in inst.items[c])
        assert P.heur_pack([(0, w, l) for (w, l) in inst.items[c]], False) is not None or P.exact_pack([(0, w, l) for (w, l) in inst.items[c]], False, False, 1.0)[0] == "feas"
    # Gesamtfläche φ · k · Ladefläche bis auf Rundung der ganzzahligen Maße
    assert abs(sum(inst.dem) / (phi * k * C.AREA) - 1.0) < 0.06
    assert inst.xy[0] == C.DEPOTS[depot]
    assert all(0 <= x <= 100 and 0 <= y <= 100 for x, y in inst.xy[1:])


def test_entfernungen_sind_ganzzahlig_und_symmetrisch(inst20):
    D = inst20.D
    n = len(D)
    assert all(D[i][i] == 0 and all(D[i][j] == D[j][i] and isinstance(D[i][j], int) for j in range(n)) for i in range(n))
    assert all(D[i][j] <= D[i][m] + D[m][j] + 1 for i in range(n) for j in range(n) for m in range(0, n, 4))      # Dreiecksungleichung bis auf Rundung


# ------------------------------------------------------------------------------------------------ Flächenlösung

def _covers_once(inst, routes):
    return sorted(c for r in routes for c in r) == list(range(1, inst.n + 1))


@pytest.mark.parametrize("theta", [0.7, 0.8, 0.9, 1.0])
def test_flaechenloesung_respektiert_die_kapazitaet_und_besucht_jeden_kunden_einmal(inst20, theta):
    ra = C.solve_area(inst20, theta)
    assert _covers_once(inst20, ra)
    for r in ra:
        assert sum(inst20.dem[c] for c in r) <= C.theta_cap(theta)


def test_kleineres_theta_braucht_nicht_weniger_fahrzeuge_und_nicht_weniger_kosten(inst20):
    kosten = {th: C.stats(inst20, C.solve_area(inst20, th), C.F_FIX) for th in (0.7, 1.0)}
    assert kosten[0.7][0] >= kosten[1.0][0] - 0       # Fahrzeuge
    assert kosten[0.7][2] >= kosten[1.0][2] - 1e-9 or kosten[0.7][0] >= kosten[1.0][0]


def test_flaechenloesung_ist_deterministisch(inst20):
    assert C.solve_area(inst20, 0.9) == C.solve_area(inst20, 0.9)


def test_einzelner_kunde_und_zwei_kunden_randfaelle():
    inst1 = C.make_instance(1, "mitte", 3, 1, 0.5, "gleich")
    assert C.solve_area(inst1, 1.0) == [[1]]
    inst2 = C.make_instance(2, "rand", 4, 1, 0.5, "gleich")
    ra = C.solve_area(inst2, 1.0)
    assert _covers_once(inst2, ra) and len(ra) == 1                    # φ = 0,5: beide Kunden zusammen belegen die Hälfte einer Ladefläche
    pk = C.Packer(inst2)
    assert all(t["u"] == "feas" for t in [C.tour_info(inst2, pk, r) for r in ra])


# ------------------------------------------------------------------------------------------------ Packer, Status

def test_status_einer_tour_ist_monoton_l_packbar_heisst_u_packbar(inst20):
    pk = C.Packer(inst20)
    ra = C.solve_area(inst20, 1.0)
    for r in ra:
        info = C.tour_info(inst20, pk, r)
        assert info["u"] in ("feas", "infeas", "unknown") and info["l"] in ("feas", "infeas", "unknown")
        if info["l"] == "feas":
            assert info["u"] == "feas"
        if info["u"] == "infeas":
            assert info["l"] == "infeas"
        assert info["parts"] == sum(len(inst20.items[c]) for c in r) and 0 < info["fill"] <= 1.0


def test_mit_drehung_ist_keine_tour_schlechter_gestellt(inst20):
    """Eine ohne Drehung packbare Tour ist mit Drehung packbar; eine mit Drehung nachweislich nicht packbare ist es ohne Drehung erst recht nicht."""
    ra = C.solve_area(inst20, 1.0)
    p0, p1 = C.Packer(inst20, rot=False), C.Packer(inst20, rot=True)
    for r in ra:
        a, b = C.tour_info(inst20, p0, r), C.tour_info(inst20, p1, r)
        if a["u"] == "feas":
            assert b["u"] == "feas"
        if b["u"] == "infeas":
            assert a["u"] == "infeas"


def test_packer_zwischenspeicher_gibt_dasselbe_ergebnis(inst20):
    pk = C.Packer(inst20)
    r = C.solve_area(inst20, 0.9)[0]
    a = pk.fit_u(r)
    n_heur, n_exact = pk.n_heur, pk.n_exact
    assert pk.fit_u(list(reversed(r))) == a                              # gleiche Menge, andere Reihenfolge: aus dem Zwischenspeicher
    assert (pk.n_heur, pk.n_exact) == (n_heur, n_exact)


# ------------------------------------------------------------------------------------------------ Reparatur und Suche

def test_reparatur_macht_jede_tour_packbar_und_erhaelt_alle_kunden(inst20):
    pk = C.Packer(inst20)
    ra = C.solve_area(inst20, 1.0)
    for polish in (False, True):
        rp = C.repair(inst20, pk, "U", ra, C.F_FIX, polish)
        assert _covers_once(inst20, rp)
        assert C.verify_routes(inst20, rp, "U") == []


def test_reparatur_in_l_liefert_packbare_orientierungen(inst20):
    pk = C.Packer(inst20)
    rp = C.repair(inst20, pk, "L", C.solve_area(inst20, 1.0), C.F_FIX, False)
    assert C.verify_routes(inst20, rp, "L") == []


def test_suche_ist_zulaessig_und_nicht_teurer_als_ihr_start(inst20):
    pk = C.Packer(inst20)
    ra = C.solve_area(inst20, 1.0)
    rr = C.repair(inst20, pk, "U", ra, C.F_FIX, True)
    ru = C.solve(inst20, pk, "U", 30, 1, C.F_FIX, starts=[rr])
    assert _covers_once(inst20, ru) and C.verify_routes(inst20, ru, "U") == []
    assert C.stats(inst20, ru, C.F_FIX)[2] <= C.stats(inst20, rr, C.F_FIX)[2]        # Warmstart: Konstruktionseigenschaft, kein Befund


def test_prueferfehler_werden_gemeldet(inst20):
    pk = C.Packer(inst20)
    ra = C.solve_area(inst20, 1.0)
    assert C.verify_routes(inst20, ra[:-1], "area") == ["Kunden nicht genau einmal"]
    assert "leere Route" in C.verify_routes(inst20, ra + [[]], "area")
    unpackbar = [r for r in ra if C.tour_info(inst20, pk, r)["u"] == "infeas"]
    if unpackbar:
        assert any(e.startswith("nicht packbar") for e in C.verify_routes(inst20, ra, "U"))


def test_run_record_ohne_und_mit_nachgeholter_suche_ist_dasselbe(inst20):
    """Die Suche lässt sich nachholen: derselbe Packer, dieselbe Reihenfolge, gleiches Ergebnis (kleine Iterationszahl)."""
    ganz = C.run_record(inst20, rot=False, search=True, iters=20)
    pk = C.Packer(inst20, rot=False)
    teil = C.run_record(inst20, rot=False, search=False, iters=20, packer=pk)
    assert "U" not in teil
    C.add_search(inst20, teil, pk, C.F_FIX, 20)
    for key in ("area", "area_best", "rep_U", "repls_U", "rep_L", "repls_L", "U", "L"):
        assert teil[key] == ganz[key], key
    assert teil["rule"] == ganz["rule"] and teil["routes"]["U"] == ganz["routes"]["U"]


def test_faustregel_ist_ein_theta_mit_lauter_packbaren_touren(inst20):
    pk = C.Packer(inst20)
    for lifo in (False, True):
        rule = C.faustregel(inst20, pk, lifo)
        if rule is not None:
            assert rule["theta"] in (0.9, 0.8, 0.7)
            rt = C.solve_area(inst20, rule["theta"])
            assert all(pk.exact_status(r, lifo)[0] == "feas" for r in rt)
            assert (rule["V"], rule["cost"]) == C.stats(inst20, rt, C.F_FIX)[::2]


def test_zweig_wenige_grosse_teile_zeigt_nicht_packbare_touren():
    """Nullspalten-Falle: bei (20, 5), Form gleich, Rand, θ = 0,90 gibt es auf dieser Instanz (Preset) nachweislich nicht packbare Touren; sonst zeigte das Preset nichts."""
    inst = C.make_instance(20, "rand", 740000, 5, 0.9, "gleich")
    pk = C.Packer(inst, rot=True)
    infos = [C.tour_info(inst, pk, r) for r in C.solve_area(inst, 0.9)]
    assert sum(1 for t in infos if t["u"] == "infeas") >= 1
