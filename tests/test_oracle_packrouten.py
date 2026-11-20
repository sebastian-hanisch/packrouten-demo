"""Orakel-Tests (DEMO-PLAYBOOK §12): Packbarkeit und Routen gegen einen anderen Rechenweg.

1. Packbarkeit: vollständige Aufzählung (Normalmuster: jedes Rechteck liegt bei x und y gleich einer Teilsumme der Ausdehnungen der übrigen, jede Packung lässt sich so
   verschieben) gegen CP-SAT und Heuristik, ohne und mit Drehung, für bis zu fünf Rechtecke.
2. Routen: Aufzählung aller Zerlegungen und Reihenfolgen mit der Aufzählung als Packbarkeitsprüfung (Hand-Instanz mit fünf Kunden) gegen das Orakel der Demo (Partitions-DP,
   Held-Karp, exakte Packbarkeit) und gegen die Suche.
3. Die Suche gegen das Orakel bei n = 8 (Messreihe M6: Lücke 0,000 % bei 40 Instanzen); hier drei Instanzen ohne und eine mit Drehung.
Die Aufzählung ist unabhängig vom Quelltext der Demo: eigene Orientierungen, eigene Überlappungsprüfung."""

import itertools

import pytest

import prt_core as C
import prt_pack as P
import prt_rng as R


# ------------------------------------------------------------------------------------------------ Orakel 1: Aufzählung der Packung

def _orient(w, l, rot):
    o = [(w, l)]
    if rot and w != l:
        o.append((l, w))
    return [(sy, sx) for (sy, sx) in o if sy <= 40 and sx <= 100]


def _sums(extents_per_item):
    """Alle Summen, die sich aus je höchstens einer Ausdehnung je Rechteck bilden lassen."""
    out = {0}
    for exts in extents_per_item:
        out |= {s + e for s in out for e in exts}
    return out


def enumerate_feasible(items, rot):
    """Gibt es eine überschneidungsfreie Platzierung in 40 x 100? Vollständig über die Normalmuster (kein Heuristik-Anteil)."""
    n = len(items)
    ors = [_orient(w, l, rot) for (_, w, l) in items]
    if any(not o for o in ors):
        return False
    order = sorted(range(n), key=lambda i: -items[i][1] * items[i][2])
    xs = [_sums([{sx for (sy, sx) in ors[j]} for j in range(n) if j != i]) for i in range(n)]
    ys = [_sums([{sy for (sy, sx) in ors[j]} for j in range(n) if j != i]) for i in range(n)]
    placed = []

    def dfs(k):
        if k == n:
            return True
        i = order[k]
        for (sy, sx) in ors[i]:
            for x in sorted(v for v in xs[i] if v + sx <= 100):
                for y in sorted(v for v in ys[i] if v + sy <= 40):
                    if all(x + sx <= x2 or x2 + sx2 <= x or y + sy <= y2 or y2 + sy2 <= y for (x2, y2, sx2, sy2) in placed):
                        placed.append((x, y, sx, sy))
                        if dfs(k + 1):
                            return True
                        placed.pop()
        return False

    return dfs(0)


def _items(seed, n, fill):
    rng = R.SplitMix64(seed + 77)
    raw = [(0.2 + 0.8 * rng.uniform(), 0.1 + 0.5 * rng.uniform()) for _ in range(n)]
    tot = sum(a * b for a, b in raw)
    sc = (fill / tot) ** 0.5
    return [(0, max(1, min(40, int(round(a * 40 * sc)))), max(1, min(100, int(round(b * 100 * sc))))) for (a, b) in raw]


def test_handbeispiel_der_aufzaehlung_selbst():
    """Das Orakel wird erst an Handbeispielen geprüft: vier 20 x 50 passen, zwei 25 x 60 nicht, drei 30 x 35 nur mit Drehung."""
    assert enumerate_feasible([(0, 20, 50)] * 4, False) is True
    assert enumerate_feasible([(0, 25, 60)] * 2, False) is False
    assert enumerate_feasible([(0, 30, 35)] * 3, False) is False
    assert enumerate_feasible([(0, 30, 35)] * 3, True) is True
    assert enumerate_feasible([(0, 30, 60)] * 2, True) is False


@pytest.mark.parametrize("rot", [False, True])
def test_packbarkeit_gegen_vollstaendige_aufzaehlung(rot):
    n_feas = n_infeas = 0
    for s in range(60):
        n = 3 + s % 3
        items = _items(s, n, 0.55 + 0.45 * ((s * 7) % 10) / 10.0)
        truth = enumerate_feasible(items, rot)
        st, pl, _ = P.exact_pack(items, False, rot, 5.0)
        assert st in ("feas", "infeas"), (s, st)             # bei höchstens 5 Rechtecken entscheidet CP-SAT innerhalb der Zeitgrenze
        assert (st == "feas") == truth, (s, rot, items)
        if st == "feas":
            assert P.verify_packing(items, pl, False) == []
        h = P.heur_pack(items, False, rot)
        if h is not None:                                       # Heuristik: nie „packbar“, wenn die Aufzählung „nein“ sagt, und jede Packung gültig
            assert truth and P.verify_packing(items, h, False) == []
        n_feas += truth
        n_infeas += not truth
    assert n_feas >= 15 and n_infeas >= 10                    # beide Seiten kommen vor (der Test unterscheidet etwas)


def test_mit_drehung_gibt_es_faelle_die_nur_gedreht_packbar_sind():
    only_rot = [s for s in range(60) if not enumerate_feasible(_items(s, 3 + s % 3, 0.8 + 0.2 * ((s * 7) % 10) / 10.0), False)
                and enumerate_feasible(_items(s, 3 + s % 3, 0.8 + 0.2 * ((s * 7) % 10) / 10.0), True)]
    assert len(only_rot) >= 1


# ------------------------------------------------------------------------------------------------ Orakel 2: Routen mit Aufzählung

def _hand_instanz():
    """Fünf Kunden mit je einem Rechteck; große Rechtecke (25 x 60), von denen je zwei nicht in ein Fahrzeug passen, kleine, die sich ergänzen."""
    xy = [(50.0, 0.0), (20.0, 30.0), (22.0, 32.0), (80.0, 60.0), (78.0, 62.0), (80.0, 64.0)]       # Kunden 1, 2 und 3, 4, 5 liegen je dicht beieinander
    items = [[], [(25, 60)], [(25, 60)], [(15, 40)], [(30, 35)], [(30, 35)]]
    return C.Inst(xy, items, {"seed": 0, "n": 5, "k": 2, "phi": 0.5, "spread": "gemischt", "depot": (50.0, 0.0)})


def _brute_force_optimum(inst, rot, F):
    n = inst.n
    D = inst.D

    def packable(custs):
        return enumerate_feasible([(0, w, l) for c in custs for (w, l) in inst.items[c]], rot)

    def tour_cost(custs):
        best = min(C.route_len(D, list(p)) for p in itertools.permutations(custs))
        return best + F

    def partitions(lst):
        if not lst:
            yield []
            return
        first, rest = lst[0], lst[1:]
        for part in partitions(rest):
            for i in range(len(part)):
                yield part[:i] + [[first] + part[i]] + part[i + 1:]
            yield [[first]] + part

    best = None
    for part in partitions(list(range(1, n + 1))):
        if all(packable(g) for g in part):
            c = sum(tour_cost(g) for g in part)
            best = c if best is None or c < best else best
    return best


@pytest.mark.parametrize("rot", [False, True])
def test_routen_orakel_und_suche_gegen_aufzaehlung_auf_der_hand_instanz(rot):
    inst = _hand_instanz()
    truth = _brute_force_optimum(inst, rot, C.F_FIX)
    pk = C.Packer(inst, rot=rot)
    opt, unsicher = C.oracle_u(inst, pk, C.F_FIX)
    assert unsicher == 0 and abs(opt - truth) < 1e-6, (opt, truth)
    ra = C.solve(inst, None, "area", C.ITERS, 1, C.F_FIX)
    rr = C.repair(inst, pk, "U", ra, C.F_FIX, True)
    ru = C.solve(inst, pk, "U", 100, 1, C.F_FIX, starts=[rr])
    cost = C.stats(inst, ru, C.F_FIX)[2]
    assert cost >= truth - 1e-6                                 # nie unter dem Optimum
    assert cost <= truth * 1.005                                # und auf dieser kleinen Instanz bis auf 0,5 % am Optimum
    assert C.verify_routes(inst, ru, "U", rot) == []


def test_hand_instanz_hat_einen_preis_des_packens():
    """Zweig-Test: die Flächenlösung ist billiger als jede packbare Lösung (sonst würde die Instanz nichts zeigen)."""
    inst = _hand_instanz()
    flaeche = C.stats(inst, C.solve(inst, None, "area", C.ITERS, 1, C.F_FIX), C.F_FIX)[2]
    assert flaeche < _brute_force_optimum(inst, False, C.F_FIX)


# ------------------------------------------------------------------------------------------------ Orakel 3: Suche gegen das Orakel bei n = 8

@pytest.mark.parametrize("rot,seeds", [(False, (605000, 605001, 605002)), (True, (605001,))])
def test_suche_gegen_orakel_bei_n_8(rot, seeds):
    gaps = []
    for sd in seeds:
        inst = C.make_instance(8, "mitte", sd, 2, 0.95, "gemischt")
        pk = C.Packer(inst, rot=rot)
        opt, unsicher = C.oracle_u(inst, pk, C.F_FIX)
        ra = C.solve(inst, None, "area", C.ITERS, 1, C.F_FIX)
        rr = C.repair(inst, pk, "U", ra, C.F_FIX, True)
        ru = C.solve(inst, pk, "U", C.ITERS, 1, C.F_FIX, starts=[rr])
        cost = C.stats(inst, ru, C.F_FIX)[2]
        assert unsicher == 0
        assert cost >= opt - 1e-6                                # nie unter dem Optimum
        assert C.verify_routes(inst, ru, "U", rot) == []
        gaps.append((cost - opt) / opt * 100.0)
    assert sum(gaps) / len(gaps) <= 0.5                          # Messreihe M6: 0,000 % bei 40 Instanzen; hier die Schranke 0,5 %


def test_kennzahlen_der_lösung_sind_kosten_gleich_laenge_plus_fixkosten():
    inst = _hand_instanz()
    routes = [[1, 3], [2, 4], [5]]
    V, D, cost = C.stats(inst, routes, C.F_FIX)
    ln = sum(C.route_len(inst.D, r) for r in routes)
    assert V == 3 and abs(D - ln / 10) < 1e-9 and cost == ln + 3 * C.F_FIX
