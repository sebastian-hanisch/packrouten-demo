"""Kern der Demo: Instanzen, Packbarkeit mit Zwischenspeicher, Suche, Reparatur, Prüfer, Orakel.

Kunde c hat 1 bis 3 Rechtecke (w, l) für die Ladefläche W x L = 40 x 100 (prt_pack). Fläche des Kunden a_c = Summe w*l. Das CVRP mit Kapazität AREA = 4000 und
Nachfrage a_c ist die „Flächen-Relaxation“ (Auslastungsgrenze θ: Kapazität θ · AREA). Kosten einer Tour: Länge + F (F = 250 Entfernungseinheiten,
1 Längeneinheit = 10 Entfernungseinheiten). Modi der Suche: 'area' (nur Fläche), 'U' (ohne Reihenfolge), 'L' (mit Entladereihenfolge). Zulässig heißt in U und L: packbar
nach der Heuristik, sonst (solange das Budget reicht) nach CP-SAT; „unbekannt“ zählt als nicht packbar. Die Drehung (rot) ist ein Merkmal des Packers.

Die Suche (Ruin-and-Recreate mit Relocate, Swap, 2-opt, 2-opt*, Verschmelzen) ist wörtlich die der Messreihen (messreihe_packrouten/pr_core.py), nur ohne
Importe aus Nachbarordnern; Instanzen werden immer ohne Drehung erzeugt (identisch mit den Instanzen der Messreihen).

API:
  make_instance(n, depot, seed, k, phi, spread) -> Inst
  Packer(inst, rot=False)   fit_u(set) / fit_l(order) mit Zwischenspeicher, exact_status(route, lifo, det)
  solve(inst, packer, mode, iters, seed, F, starts=None, cap=AREA) -> routes
  repair(inst, packer, mode, routes, F, polish) -> routes
  stats(inst, routes, F) -> (V, D in Längeneinheiten, Kosten)
  verify_routes(inst, routes, mode, rot) -> Liste von Fehlern
  oracle_u(inst, packer, F) -> (Kosten, unsicher)     (n <= 9)
"""
from __future__ import annotations

import math

import prt_pack as P
from prt_rng import SplitMix64

SCALE = 10
AREA = P.AREA
EPS = 1e-9
SPREADS = ("gleich", "gemischt")
F_FIX = 250                    # Fixkosten je Fahrzeug in Entfernungseinheiten (25 Längeneinheiten)
ITERS = 400                    # Iterationen der Suche (wie in den Messreihen)
DET_STATUS = {False: 0.3, True: 1.0}   # CP-SAT-Zeit (deterministisch) für den Status einer Tour: ohne Drehung 0,3, mit Drehung 1,0 (wie in den Messreihen)
DEPOTS = {"mitte": (50.0, 50.0), "rand": (50.0, 0.0)}


def route_len(D, r):
    if not r:
        return 0
    s = D[0][r[0]] + D[r[-1]][0]
    for a, b in zip(r, r[1:]):
        s += D[a][b]
    return s


# ------------------------------------------------------------------------------------------------ Instanzen

class Inst:
    def __init__(self, xy, items, meta):
        self.xy = xy
        self.n = len(xy) - 1
        self.items = items          # items[c] = [(w, l), ...], items[0] = []
        self.dem = [0] + [sum(w * l for (w, l) in items[c]) for c in range(1, self.n + 1)]
        self.meta = meta
        self.D = [[0] * len(xy) for _ in range(len(xy))]
        for i in range(len(xy)):
            for j in range(i + 1, len(xy)):
                d = int(round(SCALE * math.hypot(xy[i][0] - xy[j][0], xy[i][1] - xy[j][1])))
                self.D[i][j] = self.D[j][i] = d
        self._nbr = {}

    def neighbors(self, K=10):
        if K not in self._nbr:
            nb = [[]]
            for i in range(1, self.n + 1):
                order = sorted((j for j in range(1, self.n + 1) if j != i), key=lambda j: (self.D[i][j], j))
                nb.append(order[:K])
            self._nbr[K] = nb
        return self._nbr[K]


def _raw_item(rs, spread):
    if spread == "gleich":
        a = 0.40 + 0.20 * rs.uniform()
        b = 0.15 + 0.10 * rs.uniform()
    else:
        a = 0.10 + 0.90 * rs.uniform()
        b = 0.05 + 0.55 * rs.uniform()
    return a * P.W, b * P.LEN


def make_instance(n, depot, seed, k, phi, spread):
    """n Kunden gleichverteilt im 100 x 100-Gebiet, je Kunde 1 bis 3 Rechtecke (40 %, 40 %, 20 %), Form nach `spread`; alle Maße werden mit einem gemeinsamen
    Faktor so skaliert, dass die Gesamtfläche = phi * k * AREA (ganzzahlig gerundet). Ein Kunde, der allein (ohne Drehung) nicht in ein Fahrzeug passt, wird
    verworfen und die Instanz mit dem nächsten Zweig des Zufalls-Seeds neu gezogen (meta['versuche'])."""
    if isinstance(depot, str):
        depot = DEPOTS[depot]
    for attempt in range(50):
        sd = seed + attempt * 1000003
        rx = SplitMix64(sd * 8 + 1)
        rc = SplitMix64(sd * 8 + 2)
        rs = SplitMix64(sd * 8 + 3)
        xy = [depot]
        raw = [[]]
        for _ in range(n):
            u1, u2 = rx.uniform(), rx.uniform()
            xy.append((100.0 * u1, 100.0 * u2))
            u = rc.uniform()
            cnt = 1 if u < 0.4 else (2 if u < 0.8 else 3)
            raw.append([_raw_item(rs, spread) for _ in range(cnt)])
        tot = sum(w * l for c in raw for (w, l) in c)
        sc = math.sqrt(phi * k * AREA / tot)
        items = [[]]
        for c in raw[1:]:
            items.append([(max(1, min(P.W, int(round(w * sc)))), max(1, min(P.LEN, int(round(l * sc))))) for (w, l) in c])
        inst = Inst(xy, items, {"n": n, "depot": depot, "seed": seed, "k": k, "phi": phi, "spread": spread, "versuche": attempt + 1})
        inst.meta["fill"] = sum(inst.dem) / (k * AREA)
        ok = True
        for c in range(1, n + 1):
            if inst.dem[c] > AREA:
                ok = False
                break
            its = [(0, w, l) for (w, l) in items[c]]
            if P.heur_pack(its, False) is None and P.exact_pack(its, False, False, 1.0)[0] != "feas":
                ok = False
                break
        if ok:
            return inst
    raise RuntimeError("keine zulässige Instanz")


# ------------------------------------------------------------------------------------------------ Packbarkeit mit Zwischenspeicher

class Packer:
    def __init__(self, inst, rot=False, exact_det=0.1, exact_budget=2000, exact_det_max=12.0, exact_units_max=3000.0, det_status=None):
        self.inst = inst
        self.rot = bool(rot)
        self.det_status = det_status        # CP-SAT-Zeit für den Status einer Tour (Anzeige); None: die der Messreihen (DET_STATUS)
        self.cu = {}            # frozenset(Kunden) -> ("feas"|"infeas"|"unknown", via)
        self.cl = {}            # kanonische Reihenfolge -> (status, orientierte Reihenfolge oder None)
        self.exact_det = exact_det
        self.exact_budget = exact_budget     # höchstens so viele CP-SAT-Aufrufe in der Suche
        self.exact_det_max = exact_det_max   # und höchstens so viel deterministische CP-SAT-Zeit je Packer (reproduzierbar, nicht wanduhrabhängig)
        self.exact_detsum = 0.0
        self.exact_units_max = exact_units_max   # Rechenaufwand-Einheiten: je Aufruf (Zahl der Rechtecke / 20)^2
        self.exact_units = 0.0
        self.n_heur = self.n_exact = self.n_unknown = 0

    def _items(self, route, lifo):
        its = []
        for pos, c in enumerate(route):
            for (w, l) in self.inst.items[c]:
                its.append((pos if lifo else 0, w, l))
        return its

    def _budget_ok(self):
        return self.n_exact < self.exact_budget and self.exact_detsum < self.exact_det_max and self.exact_units < self.exact_units_max

    def fit_u(self, cust):
        """Suche: packbar nach Heuristik oder (solange Budget) CP-SAT. `unknown` -> False."""
        key = frozenset(cust)
        r = self.cu.get(key)
        if r is not None:
            return r[0] == "feas"
        its = self._items(sorted(key), False)
        if P.heur_pack(its, False, self.rot) is not None:
            self.cu[key] = ("feas", "heur")
            self.n_heur += 1
            return True
        if self._budget_ok():
            self.exact_units += (len(its) / 20.0) ** 2
            st, _, det = P.exact_pack(its, False, self.rot, self.exact_det)
            self.exact_detsum += det
            self.n_exact += 1
            if st == "unknown":
                self.n_unknown += 1
            self.cu[key] = (st, "exact")
            return st == "feas"
        self.cu[key] = ("infeas", "heur-nur")
        return False

    def fit_l(self, route):
        """Suche: Rückgabe die packbare Orientierung (Tupel) oder None."""
        t = tuple(route)
        rv = t[::-1]
        key = min(t, rv)
        r = self.cl.get(key)
        if r is None:
            res = None
            for cand in (key, key[::-1]):
                if P.heur_pack(self._items(cand, True), True, self.rot) is not None:
                    res = ("feas", cand)
                    self.n_heur += 1
                    break
            if res is None and self._budget_ok():
                sts = []
                for cand in (key, key[::-1]):
                    self.exact_units += (len(self._items(cand, True)) / 20.0) ** 2
                    st, _, det = P.exact_pack(self._items(cand, True), True, self.rot, self.exact_det)
                    self.exact_detsum += det
                    self.n_exact += 1
                    sts.append(st)
                    if st == "feas":
                        res = ("feas", cand)
                        break
                if res is None:
                    if "unknown" in sts:
                        self.n_unknown += 1
                    res = ("unknown" if "unknown" in sts else "infeas", None)
            if res is None:
                res = ("infeas", None)
            self.cl[key] = res
            r = res
        if r[0] != "feas":
            return None
        cand = r[1]
        return list(cand) if (cand == t or cand == rv) else None

    def status_det(self):
        return self.det_status if self.det_status is not None else DET_STATUS[self.rot]

    def exact_status(self, route, lifo, det=None):
        """Vollständige Prüfung einer Tour (Anzeige und Messung): ("feas"|"infeas"|"unknown", Platzierung oder None, Reihenfolge)."""
        if det is None:
            det = self.status_det()
        route = list(route)
        orients = (route, route[::-1]) if lifo else (route,)
        its0 = self._items(orients[0], lifo)
        h = P.heur_pack(its0, lifo, self.rot)
        if h is not None:
            return "feas", h, orients[0]
        stat = []
        for o in orients:
            its = self._items(o, lifo)
            if o is not orients[0]:
                h = P.heur_pack(its, lifo, self.rot)
                if h is not None:
                    return "feas", h, o
            st, pl, _ = P.exact_pack(its, lifo, self.rot, det)
            if st == "feas":
                return "feas", pl, o
            stat.append(st)
        return ("unknown" if "unknown" in stat else "infeas"), None, orients[0]


# ------------------------------------------------------------------------------------------------ Suche (wörtlich aus pr_core.py)

def _ins_cost(D, r, q, c):
    p = r[q - 1] if q > 0 else 0
    nx = r[q] if q < len(r) else 0
    return D[p][c] + D[c][nx] - D[p][nx]


def _rem_gain(D, r, idx):
    c = r[idx]
    p = r[idx - 1] if idx > 0 else 0
    nx = r[idx + 1] if idx + 1 < len(r) else 0
    return D[p][c] + D[c][nx] - D[p][nx]


class _St:
    def __init__(self, inst, routes, F, cap=AREA):
        self.inst, self.F, self.cap = inst, F, cap
        self.routes = [list(r) for r in routes if r]
        self.load, self.len, self.where = [], [], {}
        for ri in range(len(self.routes)):
            self.load.append(0)
            self.len.append(0)
            self.refresh(ri)

    def refresh(self, ri):
        inst = self.inst
        r = self.routes[ri]
        self.load[ri] = sum(inst.dem[c] for c in r)
        self.len[ri] = route_len(inst.D, r)
        for idx, c in enumerate(r):
            self.where[c] = (ri, idx)

    def add_route(self):
        self.routes.append([])
        self.load.append(0)
        self.len.append(0)
        return len(self.routes) - 1

    def compact(self):
        keep = [r for r in self.routes if r]
        self.__init__(self.inst, keep, self.F, self.cap)

    def cost(self):
        return sum(self.len[i] + self.F for i in range(len(self.routes)) if self.routes[i])


def make_fit(inst, packer, mode, cap=AREA):
    """fit(route) -> orientierte Route (Liste) oder None. Fläche zuerst, dann Packbarkeit je Modus."""
    dem = inst.dem

    if mode == "area":
        def fit(r):
            return list(r) if sum(dem[c] for c in r) <= cap else None
    elif mode == "U":
        def fit(r):
            if sum(dem[c] for c in r) > AREA:
                return None
            return list(r) if packer.fit_u(r) else None
    else:
        def fit(r):
            if sum(dem[c] for c in r) > AREA:
                return None
            if len(r) == 1:
                return list(r)
            return packer.fit_l(r)
    return fit


def _local_search(st, fit, mode):
    inst, D, F = st.inst, st.inst.D, st.F
    nbr = inst.neighbors(10)
    custs = list(range(1, inst.n + 1))
    dem = inst.dem
    improved = True
    guard = 0
    order_free = mode != "L"      # in U und area hängt Zulässigkeit nur von der Menge ab
    while improved and guard < 200:
        guard += 1
        improved = False
        # --- Relocate: alle verbessernden Kandidaten, nach Gewinn sortiert, erster zulässiger gewinnt
        for c in custs:
            ri, idx = st.where[c]
            r = st.routes[ri]
            d = dem[c]
            gain = _rem_gain(D, r, idx)
            cands = []
            for v in nbr[c]:
                rj, jdx = st.where[v]
                if rj == ri:
                    tmp = r[:idx] + r[idx + 1:]
                    pv = jdx if jdx < idx else jdx - 1
                    for q in (pv, pv + 1):
                        if q == idx:
                            continue
                        delta = (-gain + _ins_cost(D, tmp, q, c))
                        if delta < -EPS:
                            cands.append((delta, rj, q))
                else:
                    if st.load[rj] + d > st.cap:
                        continue
                    rv = st.routes[rj]
                    for q in (jdx, jdx + 1):
                        delta = _ins_cost(D, rv, q, c) - gain - (F if len(r) == 1 else 0)
                        if delta < -EPS:
                            cands.append((delta, rj, q))
            if len(r) > 1:
                delta = (2 * D[0][c] + F) - gain
                if delta < -EPS:
                    cands.append((delta, -1, 0))
            cands.sort()
            done = False
            for delta, rj, q in cands[:6]:
                if rj == ri:
                    newr = (r[:idx] + r[idx + 1:])
                    newr.insert(q, c)
                    fr = newr if order_free else fit(newr)
                    if fr is None:
                        continue
                    st.routes[ri] = list(fr)
                    st.refresh(ri)
                elif rj == -1:
                    st.routes[ri] = r[:idx] + r[idx + 1:]
                    nr = st.add_route()
                    st.routes[nr].append(c)
                    st.refresh(nr)
                    st.refresh(ri)
                else:
                    rv = st.routes[rj][:]
                    rv.insert(q, c)
                    fr = fit(rv)
                    if fr is None:
                        continue
                    st.routes[ri] = r[:idx] + r[idx + 1:]
                    st.routes[rj] = list(fr)
                    st.refresh(ri)
                    st.refresh(rj)
                done = True
                break
            if done:
                improved = True
                if not st.routes[ri]:
                    st.compact()
                    break
        # --- Swap
        for c in custs:
            for v in nbr[c]:
                ri, idx = st.where[c]
                rj, jdx = st.where[v]
                if rj == ri:
                    continue
                r, rv = st.routes[ri], st.routes[rj]
                nli, nlj = st.load[ri] - dem[c] + dem[v], st.load[rj] - dem[v] + dem[c]
                if nli > st.cap or nlj > st.cap:
                    continue
                p1 = r[idx - 1] if idx > 0 else 0
                n1 = r[idx + 1] if idx + 1 < len(r) else 0
                p2 = rv[jdx - 1] if jdx > 0 else 0
                n2 = rv[jdx + 1] if jdx + 1 < len(rv) else 0
                di = D[p1][v] + D[v][n1] - D[p1][c] - D[c][n1]
                dj = D[p2][c] + D[c][n2] - D[p2][v] - D[v][n2]
                if di + dj < -EPS:
                    a = r[:]
                    b = rv[:]
                    a[idx], b[jdx] = v, c
                    fa, fb = fit(a), fit(b)
                    if fa is None or fb is None:
                        continue
                    st.routes[ri], st.routes[rj] = list(fa), list(fb)
                    st.refresh(ri)
                    st.refresh(rj)
                    improved = True
                    break
        # --- 2-opt innerhalb einer Route
        for ri in range(len(st.routes)):
            r = st.routes[ri]
            if len(r) < 2:
                continue
            changed = True
            while changed:
                changed = False
                for i in range(len(r) - 1):
                    a = r[i - 1] if i > 0 else 0
                    for j in range(i + 1, len(r)):
                        b = r[j + 1] if j + 1 < len(r) else 0
                        delta = D[a][r[j]] + D[r[i]][b] - D[a][r[i]] - D[r[j]][b]
                        if delta < 0:
                            new = r[:i] + r[i:j + 1][::-1] + r[j + 1:]
                            fr = new if order_free else fit(new)
                            if fr is None:
                                continue
                            r = list(fr)
                            st.routes[ri] = r
                            changed = improved = True
                            break
                    if changed:
                        break
            st.refresh(ri)
        # --- 2-opt* (Endstücke tauschen)
        for c in custs:
            for v in nbr[c]:
                ri, idx = st.where[c]
                rj, jdx = st.where[v]
                if ri == rj:
                    continue
                r1, r2 = st.routes[ri], st.routes[rj]
                a, b = idx + 1, jdx
                n1 = r1[:a] + r2[b:]
                n2 = r2[:b] + r1[a:]
                delta = route_len(D, n1) + route_len(D, n2) - st.len[ri] - st.len[rj]
                if delta < -EPS and n1 and n2:
                    f1, f2 = fit(n1), fit(n2)
                    if f1 is None or f2 is None:
                        continue
                    st.routes[ri], st.routes[rj] = list(f1), list(f2)
                    st.refresh(ri)
                    st.refresh(rj)
                    improved = True
                    break
        # --- Verschmelzen zweier Routen
        merged = False
        R = len(st.routes)
        for i in range(R):
            if merged:
                break
            for j in range(i + 1, R):
                if st.load[i] + st.load[j] > st.cap:
                    continue
                ri_, rj_ = st.routes[i], st.routes[j]
                opts = []
                for a in (ri_, ri_[::-1]):
                    for b in (rj_, rj_[::-1]):
                        cand = a + b
                        opts.append((route_len(D, cand), cand))
                opts.sort(key=lambda t: t[0])
                if opts[0][0] - F >= st.len[i] + st.len[j] - EPS:
                    continue
                for ln, cand in opts:
                    if ln - F >= st.len[i] + st.len[j] - EPS:
                        break
                    fr = fit(cand)
                    if fr is not None:
                        st.routes[i] = list(fr)
                        st.routes[j] = []
                        st.refresh(i)
                        st.compact()
                        improved = merged = True
                        break
                if merged:
                    break
    st.compact()
    return st


def _recreate(st, removed, rng, noise, fit):
    inst, D, F = st.inst, st.inst.D, st.F
    dem = inst.dem
    for c in removed:
        cands = []
        for ri, r in enumerate(st.routes):
            if st.load[ri] + dem[c] > st.cap:
                continue
            for q in range(len(r) + 1):
                delta = _ins_cost(D, r, q, c)
                key = delta * (1.0 + noise * (rng.uniform() - 0.5))
                cands.append((key, ri, q))
        cands.sort()
        new_key = (2 * D[0][c] + F) * (1.0 + noise * (rng.uniform() - 0.5))
        placed = False
        tested = 0
        for key, ri, q in cands:
            if key >= new_key or tested >= 8:
                break
            nr = st.routes[ri][:]
            nr.insert(q, c)
            tested += 1
            fr = fit(nr)
            if fr is not None:
                st.routes[ri] = list(fr)
                st.refresh(ri)
                placed = True
                break
        if not placed:
            ri = st.add_route()
            st.routes[ri].append(c)
            st.refresh(ri)


def _savings(inst, fit, F, cap=AREA):
    D = inst.D
    n = inst.n
    cust = list(range(1, n + 1))
    rt = {c: [c] for c in cust}
    rid = {c: c for c in cust}
    pairs = sorted((-(D[0][i] + D[0][j] - D[i][j]), i, j) for i in cust for j in cust if i < j)
    for _, i, j in pairs:
        ri, rj = rid[i], rid[j]
        if ri == rj:
            continue
        a, b = rt[ri], rt[rj]
        if a[-1] == i and b[0] == j:
            new = a + b
        elif a[0] == i and b[-1] == j:
            new = b + a
        elif a[-1] == i and b[-1] == j:
            new = a + b[::-1]
        elif a[0] == i and b[0] == j:
            new = a[::-1] + b
        else:
            continue
        if sum(inst.dem[c] for c in new) > cap:
            continue
        fr = fit(new)
        if fr is None:
            continue
        rt[ri] = list(fr)
        del rt[rj]
        for c in b:
            rid[c] = ri
    return [r[:] for r in rt.values()]


def _ils(inst, fit, mode, iters, seed, start, F, cap=AREA):
    rng = SplitMix64(seed * 1000003 + 29)
    st = _local_search(_St(inst, start, F, cap), fit, mode)
    best = [r[:] for r in st.routes]
    best_c = st.cost()
    cur = [r[:] for r in best]
    stale = 0
    n = inst.n
    for _ in range(iters):
        s2 = _St(inst, cur, F, cap)
        kmax = max(4, n // 3)
        k = min(n, 2 + rng.below(kmax - 1))
        u = rng.uniform()
        if u < 0.34:
            pool = list(range(1, n + 1))
            removed = [pool.pop(rng.below(len(pool))) for _j in range(k)]
        elif u < 0.67:
            seed_c = 1 + rng.below(n)
            removed = [seed_c] + inst.neighbors(10)[seed_c][:k - 1]
        else:
            ri0 = rng.below(len(s2.routes))
            removed = s2.routes[ri0][:]
            if rng.uniform() < 0.5 and len(s2.routes) > 1:
                c0 = removed[rng.below(len(removed))]
                for v in inst.neighbors(10)[c0]:
                    if s2.where[v][0] != ri0:
                        removed += s2.routes[s2.where[v][0]]
                        break
        for c in removed:
            ri, _ = s2.where[c]
            s2.routes[ri].remove(c)
            s2.refresh(ri)
        s2.compact()
        order = removed[:]
        for i in range(len(order) - 1, 0, -1):
            j = rng.below(i + 1)
            order[i], order[j] = order[j], order[i]
        _recreate(s2, order, rng, 0.3, fit)
        s2.compact()
        _local_search(s2, fit, mode)
        c2 = s2.cost()
        if c2 < best_c - EPS:
            best_c = c2
            best = [r[:] for r in s2.routes]
            stale = 0
        else:
            stale += 1
        if c2 <= best_c * 1.004:
            cur = [r[:] for r in s2.routes]
        if stale >= 80:
            cur = [r[:] for r in best]
            stale = 0
    return best


def stats(inst, routes, F):
    D = inst.D
    ln = sum(route_len(D, r) for r in routes if r)
    V = sum(1 for r in routes if r)
    return V, ln / SCALE, ln + F * V


def solve(inst, packer, mode, iters, seed, F, starts=None, cap=AREA):
    """Beste Suche aus Startlösungen (Savings mit Zulässigkeit, plus Warmstarts), danach ILS."""
    fit = make_fit(inst, packer, mode, cap)
    cands = []
    sv = _savings(inst, fit, F, cap)
    cands.append((stats(inst, sv, F)[2], sv))
    for s in (starts or []):
        s2 = [r for r in s if r]
        cands.append((stats(inst, s2, F)[2], s2))
    cands.sort(key=lambda t: t[0])
    return _ils(inst, fit, mode, iters, seed, cands[0][1], F, cap)


def verify_routes(inst, routes, mode, rot=False):
    """Unabhängiger Prüfer: jeder Kunde genau einmal, Fläche, und je Modus Packung durch erneuten Aufruf von Heuristik/CP-SAT mit Platzierungsprüfung
    (kennt die Orientierung)."""
    errs = []
    seen = []
    for r in routes:
        if not r:
            errs.append("leere Route")
            continue
        seen.extend(r)
        if sum(inst.dem[c] for c in r) > AREA:
            errs.append("Fläche")
        if mode in ("U", "L"):
            lifo = mode == "L"
            its = []
            for pos, c in enumerate(r):
                for (w, l) in inst.items[c]:
                    its.append((pos if lifo else 0, w, l))
            h = P.heur_pack(its, lifo, rot)
            if h is None:
                st, h, _ = P.exact_pack(its, lifo, rot, 2.0)
                if st != "feas":
                    errs.append(f"nicht packbar ({st})")
                    continue
            if P.verify_packing(its, h, lifo):
                errs.append("Packung ungültig")
    if sorted(seen) != list(range(1, inst.n + 1)):
        errs.append("Kunden nicht genau einmal")
    return errs


# ------------------------------------------------------------------------------------------------ Reparatur (wörtlich aus pr_core.py)

def repair(inst, packer, mode, routes, F, polish=False, seed=1):
    """Reparatur der Flächenlösung: je nicht packbarer Tour wird der Kunde mit der größten Fläche entfernt, bis sie packbar ist; die Entfernten
    werden (größte Fläche zuerst) am billigsten zulässig eingefügt, sonst eigene Tour. polish: danach eine lokale Suche ohne Neustarts."""
    fit = make_fit(inst, packer, mode)
    D = inst.D
    out, removed = [], []
    for r in routes:
        cur = list(r)
        while True:
            fr = fit(cur)
            if fr is not None:
                out.append(fr)
                break
            if len(cur) == 1:      # allein nicht packbar (kommt nicht vor, Instanz geprüft)
                out.append(cur)
                break
            big = max(cur, key=lambda c: (inst.dem[c], c))
            cur.remove(big)
            removed.append(big)
    removed.sort(key=lambda c: (-inst.dem[c], c))
    for c in removed:
        placed = False
        # alle Kandidaten sortiert prüfen
        cands = []
        for ri, r in enumerate(out):
            if sum(inst.dem[x] for x in r) + inst.dem[c] > AREA:
                continue
            for q in range(len(r) + 1):
                cands.append((_ins_cost(D, r, q, c), ri, q))
        cands.sort()
        newcost = 2 * D[0][c] + F
        for delta, ri, q in cands[:12]:
            if delta >= newcost:
                break
            cand = out[ri][:]
            cand.insert(q, c)
            fr = fit(cand)
            if fr is not None:
                out[ri] = list(fr)
                placed = True
                break
        if not placed:
            out.append([c])
    if polish:
        st = _local_search(_St(inst, out, F), fit, mode)
        out = [r[:] for r in st.routes]
    return out


# ------------------------------------------------------------------------------------------------ Orakel (n <= 9, nur U)

def oracle_u(inst, packer, F, det=2.0):
    """Exaktes Optimum für U: Partitions-DP über Mengen, Tourlänge per Held-Karp, Packbarkeit exakt (Heuristik, dann CP-SAT det Sekunden).
    Rückgabe (Kosten, unsicher): unsicher > 0, wenn eine Menge mit Status `unknown` als nicht packbar gezählt wurde."""
    n = inst.n
    D = inst.D
    dem = inst.dem
    INF = float("inf")
    dp = [[INF] * n for _ in range(1 << n)]
    for j in range(n):
        dp[1 << j][j] = D[0][j + 1]
    for S in range(1, 1 << n):
        for j in range(n):
            if not (S >> j) & 1 or dp[S][j] == INF:
                continue
            base = dp[S][j]
            for k in range(n):
                if (S >> k) & 1:
                    continue
                T = S | (1 << k)
                v = base + D[j + 1][k + 1]
                if v < dp[T][k]:
                    dp[T][k] = v
    unsicher = 0
    tour = [INF] * (1 << n)
    for S in range(1, 1 << n):
        cs = [j + 1 for j in range(n) if (S >> j) & 1]
        if sum(dem[c] for c in cs) > AREA:
            continue
        st, _, _ = packer.exact_status(cs, False, det)
        if st == "unknown":
            unsicher += 1
        if st != "feas":
            continue
        best = min(dp[S][j] + D[j + 1][0] for j in range(n) if (S >> j) & 1)
        tour[S] = best + F
    best = [INF] * (1 << n)
    best[0] = 0.0
    for S in range(1, 1 << n):
        low = S & -S
        T = S
        while T:
            if T & low and tour[T] < INF:
                v = tour[T] + best[S ^ T]
                if v < best[S]:
                    best[S] = v
            T = (T - 1) & S
    return best[(1 << n) - 1], unsicher


# ------------------------------------------------------------------------------------------------ Bausteine der Anzeige und der Messreihen

def theta_cap(theta):
    return int(round(theta * AREA))


def solve_area(inst, theta=1.0, F=F_FIX, iters=ITERS, starts=None):
    """Flächenlösung (CVRP mit Kapazität θ · Ladefläche); deterministisch, ohne Packbarkeitsprüfung."""
    pk = None
    return solve(inst, pk, "area", iters, 1, F, starts=starts, cap=theta_cap(theta))


def tour_info(inst, packer, r):
    """Fläche (Anteil der Ladefläche), Zahl der Teile, Status U und (nur wenn U packbar) L je Tour; `u`/`l` = "feas" | "infeas" | "unknown"."""
    det = packer.status_det()
    area = sum(inst.dem[c] for c in r) / AREA
    parts = sum(len(inst.items[c]) for c in r)
    su, _, _ = packer.exact_status(r, False, det)
    if su == "feas":
        sl = packer.exact_status(r, True, det)[0]
    else:
        sl = "infeas" if su == "infeas" else "unknown"       # L packbar => U packbar
    return {"fill": round(area, 4), "parts": parts, "len": len(r), "u": su, "l": sl}


def faustregel(inst, packer, lifo, F=F_FIX, iters=ITERS, areas=None):
    """Größtes θ in (0,9; 0,8; 0,7), dessen Flächenlösung nur packbare Touren enthält (je Modus), mit den Kennzahlen dieser Lösung; sonst None.
    `areas`: Zwischenspeicher {θ: Routen} der Flächenlösungen (deterministisch, daher teilbar zwischen U und L)."""
    areas = {} if areas is None else areas
    det = packer.status_det()
    for th in (0.9, 0.8, 0.7):
        if th not in areas:
            areas[th] = solve_area(inst, th, F, iters)
        rt = areas[th]
        if all(packer.exact_status(r, lifo, det)[0] == "feas" for r in rt):
            V, D, cost = stats(inst, rt, F)
            return {"theta": th, "V": V, "D": D, "cost": cost}
    return None


def _rec(inst, F, out, name, routes):
    V, D, cost = stats(inst, routes, F)
    out[name] = {"V": V, "D": D, "cost": cost}
    return routes


def run_record(inst, rot=False, search=True, F=F_FIX, iters=ITERS, packer=None, search_iters=None, modes=("U", "L")):
    """Die Rechnung einer Instanz wie in der Messreihe M2: Fläche (θ = 1,00), Faustregel, Reparatur (roh und mit lokaler Suche), und mit `search` die Suche
    L und U (Start: Reparatur) und die Fläche erneut mit Start aus U („area_best“). Ohne `search` nur die ersten drei Schritte (Live-Teil der App; `modes=("U",)`
    lässt Faustregel und Reparatur für L weg, das spart Rechenzeit; mit `search` müssen beide Modi gerechnet sein);
    die Suche lässt sich danach mit `add_search` nachholen (derselbe Packer, dieselbe Reihenfolge, gleiches Ergebnis).
    Rückgabe: Dict mit Kennzahlen und, für die Anzeige, den Routen (`routes`: area, rep_U, repls_U, rep_L, repls_L, U, L)."""
    pk = packer or Packer(inst, rot=rot)
    out = {"n": inst.n, "seed": inst.meta["seed"], "fill": round(inst.meta["fill"], 4), "rot": bool(rot)}
    routes = {}
    ra = _rec(inst, F, out, "area", solve_area(inst, 1.0, F, iters))
    routes["area"] = ra
    areas = {}
    rule = {}
    for mode, lifo in (("U", False), ("L", True)):
        if mode in modes:
            rule[mode] = faustregel(inst, pk, lifo, F, iters, areas)
    out["rule"] = rule
    for mode in modes:
        rp = repair(inst, pk, mode, ra, F, False)
        _rec(inst, F, out, "rep_" + mode, rp)
        rpl = repair(inst, pk, mode, ra, F, True)
        _rec(inst, F, out, "repls_" + mode, rpl)
        routes["rep_" + mode] = rp
        routes["repls_" + mode] = rpl
    out["routes"] = routes
    if search:
        add_search(inst, out, pk, F, iters if search_iters is None else search_iters)
    out["packer"] = {"heur": pk.n_heur, "exact": pk.n_exact, "unknown": pk.n_unknown, "det": round(pk.exact_detsum, 1)}
    return out


def add_search(inst, out, pk, F=F_FIX, iters=ITERS):
    """Die Suche L und U mit Start aus der Reparatur (und die Fläche erneut mit Start aus U) an einen Datensatz ohne Suche anhängen."""
    routes = out["routes"]
    rl = _rec(inst, F, out, "L", solve(inst, pk, "L", iters, 1, F, starts=[routes["repls_L"]]))
    ru = _rec(inst, F, out, "U", solve(inst, pk, "U", iters, 1, F, starts=[rl, routes["repls_U"]]))
    ab = solve(inst, None, "area", iters, 1, F, starts=[ru], cap=AREA)
    ra = routes["area"]
    ab = ab if stats(inst, ab, F)[2] <= stats(inst, ra, F)[2] else ra
    _rec(inst, F, out, "area_best", ab)
    routes["U"], routes["L"] = ru, rl
    out["verify"] = {"U": verify_routes(inst, ru, "U", pk.rot), "L": verify_routes(inst, rl, "L", pk.rot)}
    out["packer"] = {"heur": pk.n_heur, "exact": pk.n_exact, "unknown": pk.n_unknown, "det": round(pk.exact_detsum, 1)}
    return out
