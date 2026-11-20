"""Packbarkeit: Handbeispiele (von Hand nachgerechnet), Prüfer, Monotonie, Drehung, Teil-Packung."""

import pytest

import prt_pack as P
import prt_rng as R


def _random_items(seed, n, fill):
    """Zufällige Rechtecke (Form „gemischt“), so skaliert, dass ihre Gesamtfläche etwa `fill` der Ladefläche beträgt; Besuchsposition i // 2."""
    rng = R.SplitMix64(seed + 1)
    raw = [(0.1 + 0.9 * rng.uniform(), 0.05 + 0.55 * rng.uniform()) for _ in range(n)]
    tot = sum(a * b for a, b in raw)
    sc = (fill / tot) ** 0.5
    return [(i // 2, max(1, min(P.W, int(round(a * P.W * sc)))), max(1, min(P.LEN, int(round(b * P.LEN * sc))))) for i, (a, b) in enumerate(raw)]


# ------------------------------------------------------------------------------------------------ Handbeispiele ohne Drehung

def test_perfekte_packung_vier_mal_20_mal_50():
    items = [(0, 20, 50)] * 4          # 4 x 1000 = 4000 = Ladefläche: zwei Spalten mal zwei Zeilen
    h = P.heur_pack(items, False)
    assert h is not None and P.verify_packing(items, h, False) == []
    st, pl, _ = P.exact_pack(items, False, False, 2.0)
    assert st == "feas" and P.verify_packing(items, pl, False) == []


def test_flaeche_reicht_aber_zwei_mal_25_mal_60_sind_nicht_packbar():
    zwei = [(0, 25, 60), (0, 25, 60)]  # 2 x 1500 = 3000 <= 4000, aber 25 + 25 > 40 in der Breite und 60 + 60 > 100 in der Länge
    assert sum(w * l for _, w, l in zwei) <= P.AREA
    assert P.heur_pack(zwei, False) is None
    assert P.quick_infeasible(zwei) is True
    assert P.exact_pack(zwei, False, False, 2.0)[0] == "infeas"


def test_entladereihenfolge_beispiel_mit_drei_kunden():
    """A 25 x 30 (zuerst), B 30 x 60, C 15 x 40 (zuletzt): ohne Reihenfolge packbar (B hinten, A neben C vor der Tür), mit Reihenfolge in keiner Richtung."""
    ex = [(0, 25, 30), (1, 30, 60), (2, 15, 40)]
    flat = [(0, w, l) for _, w, l in ex]
    st, pl, _ = P.exact_pack(flat, False, False, 2.0)
    assert st == "feas" and P.verify_packing(flat, pl, False) == []
    assert P.exact_pack(ex, True, False, 2.0)[0] == "infeas"
    assert P.exact_pack([(2 - v, w, l) for v, w, l in ex], True, False, 2.0)[0] == "infeas"      # Umkehrung der Tour


def test_zwei_kunden_nebeneinander_erfuellen_die_entladereihenfolge():
    items = [(0, 20, 50), (1, 20, 50)]
    h = P.heur_pack(items, True)
    assert h is not None and P.verify_packing(items, h, True) == []


# ------------------------------------------------------------------------------------------------ Prüfer

def test_pruefer_erkennt_ueberlappung_ausserhalb_und_reihenfolge():
    its = [(0, 20, 50), (1, 20, 50)]
    assert "Ueberlappung" in P.verify_packing(its, [(0, 0), (10, 10)], False)
    assert "ausserhalb" in P.verify_packing(its, [(60, 0), (0, 20)], False)
    assert "Anzahl" in P.verify_packing(its, [(0, 0)], False)
    its2 = [(0, 40, 30), (1, 40, 30)]
    assert "LIFO" in P.verify_packing(its2, [(0, 0), (30, 0)], True)          # früher besuchter Kunde (x 0..30) steht hinter dem späteren (x 30..60)
    assert P.verify_packing(its2, [(0, 0), (30, 0)], False) == []              # ohne Reihenfolge zulässig
    assert P.verify_packing(its2, [(30, 0), (0, 0)], True) == []


def test_pruefer_kennt_die_orientierung():
    # 50 x 30 (y-Ausdehnung 50 > 40): ungedreht außerhalb, gedreht (y 30, x 50) passt
    assert "ausserhalb" in P.verify_packing([(0, 50, 30)], [(0, 0, 0)], False)
    assert P.verify_packing([(0, 50, 30)], [(0, 0, 1)], False) == []
    # 30 x 70: ungedreht passt, gedreht (y 70 > 40) liegt außerhalb
    assert P.verify_packing([(0, 30, 70)], [(0, 0, 0)], False) == []
    assert "ausserhalb" in P.verify_packing([(0, 30, 70)], [(0, 0, 1)], False)
    assert "Orientierung" in P.verify_packing([(0, 20, 20)], [(0, 0, 2)], False)


# ------------------------------------------------------------------------------------------------ Drehung

def test_drei_rechtecke_30_mal_35_nur_mit_drehung_packbar():
    """Drei 30 x 35 (y 30, x 35): ohne Drehung brauchen sie nebeneinander y 90 > 40 und hintereinander x 105 > 100; gedreht (y 35, x 30) stehen sie in einer Reihe,
    3 x 30 = 90 <= 100 in der Länge bei Breite 35 <= 40."""
    items = [(0, 30, 35)] * 3
    assert P.exact_pack(items, False, False, 2.0)[0] == "infeas"
    assert P.heur_pack(items, False, False) is None
    h = P.heur_pack(items, False, True)
    assert h is not None and P.verify_packing(items, h, False) == []
    st, pl, _ = P.exact_pack(items, False, True, 2.0)
    assert st == "feas" and P.verify_packing(items, pl, False) == []
    assert any(p[2] == 1 for p in pl)                                            # mindestens ein Rechteck ist gedreht


def test_zwei_rechtecke_30_mal_60_sind_auch_mit_drehung_nicht_packbar():
    items = [(0, 30, 60)] * 2          # gedreht wäre y 60 > 40 (nicht erlaubt); ungedreht 30 + 30 > 40 und 60 + 60 > 100
    assert P.exact_pack(items, False, True, 2.0)[0] == "infeas"
    assert P.heur_pack(items, False, True) is None


def test_opts_nur_erlaubte_orientierungen():
    assert P.opts(30, 35) == [(30, 35, 0), (35, 30, 1)]
    assert P.opts(20, 20) == [(20, 20, 0)]                       # quadratisch: nur eine
    assert P.opts(30, 60) == [(30, 60, 0)]                       # gedreht y 60 > 40
    assert P.opts(50, 30) == [(30, 50, 1)]                       # ungedreht y 50 > 40 passt nicht, gedreht schon
    assert P.opts(45, 150) == []


def test_ohne_drehung_packbar_heisst_mit_drehung_nie_nicht_packbar():
    """Monotonie über 60 Zufallsmengen (feste Zufalls-Seeds): was ohne Drehung packbar ist, ist mit Drehung packbar (Heuristik und exakt)."""
    n_feas = 0
    for s in range(60):
        items = _random_items(s, 4 + s % 5, 0.55 + 0.4 * ((s * 7) % 10) / 10.0)
        if P.heur_pack(items, False, False) is not None:
            n_feas += 1
            hp = P.heur_pack(items, False, True)
            assert hp is not None and P.verify_packing(items, hp, False) == []
            assert P.exact_pack(items, False, True, 0.5)[0] != "infeas"
    assert n_feas >= 20                                           # der Test prüft etwas: genug packbare Fälle


@pytest.mark.parametrize("rot", [False, True])
@pytest.mark.parametrize("lifo", [False, True])
def test_jede_gefundene_packung_besteht_den_pruefer(rot, lifo):
    n_ok = 0
    for s in range(40):
        items = _random_items(100 + s, 5 + s % 6, 0.5 + 0.35 * ((s * 3) % 10) / 10.0)
        h = P.heur_pack(items, lifo, rot)
        if h is not None:
            n_ok += 1
            assert P.verify_packing(items, h, lifo) == [], (s, lifo, rot)
        st, pl, _ = P.exact_pack(items, lifo, rot, 0.3)
        if st == "feas":
            assert P.verify_packing(items, pl, lifo) == [], (s, lifo, rot)
    assert n_ok >= 10


def test_l_packbar_heisst_u_packbar():
    n = 0
    for s in range(30):
        items = _random_items(300 + s, 6 + s % 4, 0.5 + 0.3 * ((s * 3) % 10) / 10.0)
        flat = [(0, w, l) for _, w, l in items]
        if P.heur_pack(items, True) is not None:
            n += 1
            assert P.heur_pack(flat, False) is not None or P.exact_pack(flat, False, False, 0.5)[0] != "infeas"
    assert n >= 5


# ------------------------------------------------------------------------------------------------ Teil-Packung für die Zeichnung

@pytest.mark.parametrize("rot", [False, True])
def test_teil_packung_ist_gueltig_und_nennt_die_rechtecke_ohne_platz(rot):
    items = [(0, 25, 60), (0, 25, 60), (0, 20, 30)]                 # nicht alle passen (zwei 25 x 60 gehen nicht zusammen)
    place, left = P.partial_pack(items, rot)
    placed = [(i, p) for i, p in enumerate(place) if p is not None]
    assert len(left) >= 1 and sorted(i for i, _ in placed) == sorted(set(range(3)) - set(left))
    assert P.verify_packing([items[i] for i, _ in placed], [p for _, p in placed], False) == []


def test_teil_packung_einer_packbaren_menge_laesst_nichts_aus():
    items = [(0, 20, 50)] * 4
    place, left = P.partial_pack(items, False)
    assert left == [] and P.verify_packing(items, [(p[0], p[1]) for p in place], False) == []
