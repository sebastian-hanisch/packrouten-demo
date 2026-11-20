"""Packbarkeit einer Tour: Rechtecke in einer Ladefläche, ohne und mit Drehung um 90°.

Ladefläche W x L = 40 x 100 (Breite y, Länge x, Tür bei x = L), ganzzahlige Maße. Ein Rechteck ist (visit, w, l) mit w = Ausdehnung in y und
l = Ausdehnung in x. Eine Tour besucht die Kunden in der Reihenfolge der Liste (visit 0 = zuerst beliefert = zuerst entladen).
  U  (ohne Reihenfolge): Rechtecke überschneidungsfrei in der Fläche.
  L  (mit Entladereihenfolge, vereinfachte Fassung): zusätzlich darf kein Rechteck eines später besuchten Kunden j vor einem eines früher besuchten
     Kunden i stehen: überlappen sich ihre y-Bereiche, muss x_j + l_j <= x_i gelten. Kein Umladen. Eine Tour und ihre Umkehrung sind gleich lang;
     in L gilt eine Tour als packbar, wenn sie oder ihre Umkehrung packbar ist.
Drehung (rot=True): jedes Rechteck wird einzeln gedreht oder nicht, nur wenn die gedrehte Lage in die Ladefläche passt. Platzierung dann (x, y, rot).

API (ohne globalen Zustand; `rot` ist immer ein Argument):
  heur_pack(items, lifo, rot=False)               -> Platzierung oder None (schnell, hinreichend, nicht notwendig)
  exact_pack(items, lifo, rot=False, det_time=1)  -> (Status, Platzierung, deterministische Zeit); Status "feas" | "infeas" | "unknown"
  verify_packing(items, placement, lifo)          -> Liste von Fehlern (unabhängiger Prüfer, kennt die Orientierung)
  quick_infeasible(items, rot=False)              -> True = sicher nicht packbar (notwendige Bedingungen)
  partial_pack(items, rot=False)                  -> (Platzierung der passenden Teile, Indizes der nicht passenden): Zeichnung für nicht packbare Touren
Die Heuristik ist deterministisch (SplitMix64 aus den Rechtecken), CP-SAT läuft mit einem Arbeiter, festem Zufalls-Seed und max_deterministic_time."""

from __future__ import annotations

W, LEN = 40, 100
AREA = W * LEN
_MASK = (1 << 64) - 1


def opts(w, l):
    """Erlaubte Orientierungen als (sy, sx, rot): y-Ausdehnung, x-Ausdehnung, gedreht?"""
    o = []
    if w <= W and l <= LEN:
        o.append((w, l, 0))
    if w != l and l <= W and w <= LEN:
        o.append((l, w, 1))
    return o


# ------------------------------------------------------------------------------------------------ Prüfer und notwendige Bedingungen

def verify_packing(items, placement, lifo):
    """Unabhängiger Prüfer: Außerhalb, Überlappung, Entladereihenfolge. Platzierung (x, y) oder (x, y, rot); rot = 1 vertauscht w und l."""
    if len(items) != len(placement):
        return ["Anzahl"]
    errs = []
    oriented = []
    for (v, w, l), pl in zip(items, placement):
        rot = pl[2] if len(pl) > 2 else 0
        if rot not in (0, 1):
            errs.append("Orientierung")
            rot = 0
        oriented.append((v, l, w) if rot else (v, w, l))
    for (v, w, l), pl in zip(oriented, placement):
        x, y = pl[0], pl[1]
        if x < 0 or y < 0 or x + l > LEN or y + w > W:
            errs.append("ausserhalb")
    n = len(oriented)
    for i in range(n):
        vi, wi, li = oriented[i]
        xi, yi = placement[i][0], placement[i][1]
        for j in range(i + 1, n):
            vj, wj, lj = oriented[j]
            xj, yj = placement[j][0], placement[j][1]
            xo = xi < xj + lj and xj < xi + li
            yo = yi < yj + wj and yj < yi + wi
            if xo and yo:
                errs.append("Ueberlappung")
            if lifo and vi != vj and yo:
                if vi < vj and not (xj + lj <= xi):
                    errs.append("LIFO")
                if vj < vi and not (xi + li <= xj):
                    errs.append("LIFO")
    return errs


def quick_infeasible(items, rot=False):
    """Notwendige Bedingungen (für U und L): Gesamtfläche; Rechtecke, die in jeder erlaubten Lage breiter als W/2 sind, liegen paarweise hintereinander
    (Summe der Längen <= L); Rechtecke, die in jeder Lage länger als L/2 sind, liegen paarweise nebeneinander (Summe der Breiten <= W)."""
    if sum(w * l for _, w, l in items) > AREA:
        return True
    if not rot:
        if sum(l for _, w, l in items if 2 * w > W) > LEN:
            return True
        if sum(w for _, w, l in items if 2 * l > LEN) > W:
            return True
        return False
    a1 = a2 = 0
    for _, w, l in items:
        o = opts(w, l)
        if not o:
            return True
        if all(2 * sy > W for sy, sx, _ in o):
            a1 += min(sx for sy, sx, _ in o)
        if all(2 * sx > LEN for sy, sx, _ in o):
            a2 += min(sy for sy, sx, _ in o)
    return a1 > LEN or a2 > W


# ------------------------------------------------------------------------------------------------ Heuristik ohne Drehung

def _maxrects(items, order, score):
    free = [(0, 0, LEN, W)]
    pos = [None] * len(items)
    for idx in order:
        _, w, l = items[idx]
        best = None
        for (fx, fy, fl, fw) in free:
            if l <= fl and w <= fw:
                if score == 0:      # Best Short Side Fit
                    s = (min(fl - l, fw - w), max(fl - l, fw - w), fx, fy)
                elif score == 1:    # Best Area Fit
                    s = (fl * fw - l * w, min(fl - l, fw - w), fx, fy)
                else:               # Bottom-Left
                    s = (fx, fy, 0, 0)
                if best is None or s < best[0]:
                    best = (s, fx, fy)
        if best is None:
            return None
        _, px, py = best
        pos[idx] = (px, py)
        free = _split_free(free, px, py, l, w)
    return pos


def _split_free(free, px, py, sx, sy):
    nf = []
    for (fx, fy, fl, fw) in free:
        if px >= fx + fl or px + sx <= fx or py >= fy + fw or py + sy <= fy:
            nf.append((fx, fy, fl, fw))
            continue
        if px > fx:
            nf.append((fx, fy, px - fx, fw))
        if px + sx < fx + fl:
            nf.append((px + sx, fy, fx + fl - (px + sx), fw))
        if py > fy:
            nf.append((fx, fy, fl, py - fy))
        if py + sy < fy + fw:
            nf.append((fx, py + sy, fl, fy + fw - (py + sy)))
    nf.sort(key=lambda r: -(r[2] * r[3]))
    keep = []
    for r in nf:
        cont = False
        for k in keep:
            if r[0] >= k[0] and r[1] >= k[1] and r[0] + r[2] <= k[0] + k[2] and r[1] + r[3] <= k[1] + k[3]:
                cont = True
                break
        if not cont:
            keep.append(r)
    return keep


def _skyline(items, order, tie=0):
    """Skyline in y-Richtung diskret (W Positionen). tie 0: kleinstes (x, y); 1: kleinstes x, größtes y; 2: kleinstes x, dann kleinste Hohlraumfläche."""
    h = [0] * W
    pos = [None] * len(items)
    for idx in order:
        _, w, l = items[idx]
        best = None
        for y in range(0, W - w + 1):
            seg = h[y:y + w]
            x = max(seg)
            if x + l > LEN:
                continue
            if tie == 0:
                key = (x, y)
            elif tie == 1:
                key = (x, -y)
            else:
                key = (x, x * w - sum(seg), y)
            if best is None or key < best[0]:
                best = (key, x, y)
        if best is None:
            return None
        _, x, y = best
        pos[idx] = (x, y)
        for t in range(y, y + w):
            h[t] = x + l
    return pos


def _seed_of(items):
    z = 1469598103934665603
    for v, w, l in items:
        z = ((z ^ (v * 7919 + w * 131 + l)) * 1099511628211) & _MASK
    return z


def _shuffled(n, items, rounds):
    """Deterministische Zufallsreihenfolgen (SplitMix64, Zufalls-Seed aus den Rechtecken)."""
    st = _seed_of(items)
    out = []
    for _ in range(rounds):
        od = list(range(n))
        for i in range(n - 1, 0, -1):
            st = (st + 0x9E3779B97F4A7C15) & _MASK
            z = st
            z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
            z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
            z ^= z >> 31
            j = z % (i + 1)
            od[i], od[j] = od[j], od[i]
        out.append(od)
    return out


def _heur_plain(items, lifo, rounds, quick_rot):
    """Heuristik ohne Drehung; die notwendigen Bedingungen laufen mit oder ohne Drehung (quick_rot), wie in der Messreihe."""
    n = len(items)
    if n == 0:
        return []
    if quick_infeasible(items, quick_rot):
        return None
    if not lifo:
        orders = (
            sorted(range(n), key=lambda i: (-items[i][1] * items[i][2], i)),
            sorted(range(n), key=lambda i: (-items[i][2], -items[i][1], i)),
            sorted(range(n), key=lambda i: (-items[i][1], -items[i][2], i)),
        )
        for od in orders:
            for sc in (0, 1, 2):
                p = _maxrects(items, od, sc)
                if p is not None:
                    return p
        for od in orders:
            for tie in (0, 2):
                p = _skyline(items, od, tie)
                if p is not None:
                    return p
        for od in _shuffled(n, items, rounds):
            for sc in (0, 1):
                p = _maxrects(items, od, sc)
                if p is not None:
                    return p
        return None
    keys = ((lambda i: (-items[i][0], -items[i][1] * items[i][2], i)),
            (lambda i: (-items[i][0], -items[i][2], -items[i][1], i)),
            (lambda i: (-items[i][0], -items[i][1], -items[i][2], i)))
    for key in keys:
        od = sorted(range(n), key=key)
        for tie in (0, 1, 2):
            p = _skyline(items, od, tie)
            if p is not None:
                return p
    for od in _shuffled(n, items, rounds):
        od = sorted(od, key=lambda i, od=od: (-items[i][0], od.index(i)))
        for tie in (0, 2):
            p = _skyline(items, od, tie)
            if p is not None:
                return p
    return None


# ------------------------------------------------------------------------------------------------ Heuristik mit Drehung

def _maxrects_rot(items, order, score):
    free = [(0, 0, LEN, W)]
    pos = [None] * len(items)
    for idx in order:
        _, w, l = items[idx]
        o = opts(w, l)
        best = None
        for (fx, fy, fl, fw) in free:
            for (sy, sx, rot) in o:
                if sx <= fl and sy <= fw:
                    if score == 0:
                        s = (min(fl - sx, fw - sy), max(fl - sx, fw - sy), fx, fy, rot)
                    elif score == 1:
                        s = (fl * fw - sx * sy, min(fl - sx, fw - sy), fx, fy, rot)
                    else:
                        s = (fx, fy, rot, 0, 0)
                    if best is None or s < best[0]:
                        best = (s, fx, fy, sy, sx, rot)
        if best is None:
            return None
        _, px, py, sy, sx, rot = best
        pos[idx] = (px, py, rot)
        free = _split_free(free, px, py, sx, sy)
    return pos


def _skyline_rot(items, order, tie, policy):
    """Skyline in y-Richtung. policy 0: kleinstes (x, ...) über beide Orientierungen; policy 1: kleinste Oberkante x + sx zuerst."""
    h = [0] * W
    pos = [None] * len(items)
    for idx in order:
        _, w, l = items[idx]
        best = None
        for (sy, sx, rot) in opts(w, l):
            for y in range(0, W - sy + 1):
                seg = h[y:y + sy]
                x = max(seg)
                if x + sx > LEN:
                    continue
                if tie == 0:
                    key = (x, y)
                elif tie == 1:
                    key = (x, -y)
                else:
                    key = (x, x * sy - sum(seg), y)
                key = ((x + sx,) + key if policy else key) + (rot,)
                if best is None or key < best[0]:
                    best = (key, x, y, sy, sx, rot)
        if best is None:
            return None
        _, x, y, sy, sx, rot = best
        pos[idx] = (x, y, rot)
        for t in range(y, y + sy):
            h[t] = x + sx
    return pos


def heur_pack(items, lifo, rot=False, rounds=10):
    """Schnelle hinreichende Prüfung. Rückgabe Platzierung (Liste (x, y) bzw. (x, y, rot) je Rechteck) oder None."""
    if not rot:
        return _heur_plain(items, lifo, rounds, False)
    n = len(items)
    if n == 0:
        return []
    r = _heur_plain(items, lifo, rounds, True)        # ohne Drehung packbar => mit Drehung packbar
    if r is not None:
        return [(x, y, 0) for x, y in r]
    if quick_infeasible(items, True):
        return None
    if not lifo:
        orders = (
            sorted(range(n), key=lambda i: (-items[i][1] * items[i][2], i)),
            sorted(range(n), key=lambda i: (-max(items[i][1], items[i][2]), -min(items[i][1], items[i][2]), i)),
            sorted(range(n), key=lambda i: (-items[i][2], -items[i][1], i)),
            sorted(range(n), key=lambda i: (-items[i][1], -items[i][2], i)),
        )
        for od in orders:
            for sc in (0, 1, 2):
                p = _maxrects_rot(items, od, sc)
                if p is not None:
                    return p
        for od in orders:
            for tie in (0, 2):
                for pol in (0, 1):
                    p = _skyline_rot(items, od, tie, pol)
                    if p is not None:
                        return p
        for od in _shuffled(n, items, rounds):
            for sc in (0, 1):
                p = _maxrects_rot(items, od, sc)
                if p is not None:
                    return p
        return None
    keys = ((lambda i: (-items[i][0], -items[i][1] * items[i][2], i)),
            (lambda i: (-items[i][0], -max(items[i][1], items[i][2]), -min(items[i][1], items[i][2]), i)),
            (lambda i: (-items[i][0], -items[i][2], -items[i][1], i)),
            (lambda i: (-items[i][0], -items[i][1], -items[i][2], i)))
    for key in keys:
        od = sorted(range(n), key=key)
        for tie in (0, 1, 2):
            for pol in (0, 1):
                p = _skyline_rot(items, od, tie, pol)
                if p is not None:
                    return p
    for od in _shuffled(n, items, rounds):
        od = sorted(od, key=lambda i, od=od: (-items[i][0], od.index(i)))
        for tie in (0, 2):
            for pol in (0, 1):
                p = _skyline_rot(items, od, tie, pol)
                if p is not None:
                    return p
    return None


# ------------------------------------------------------------------------------------------------ exakt: CP-SAT

def exact_pack(items, lifo, rot=False, det_time=1.0, seed=1):
    """CP-SAT (NoOverlap2D, deterministische Zeitgrenze). Rückgabe (Status, Platzierung oder None, deterministische Zeit)."""
    from ortools.sat.python import cp_model
    n = len(items)
    if n == 0:
        return "feas", [], 0.0
    if quick_infeasible(items, rot):
        return "infeas", None, 0.0
    m = cp_model.CpModel()
    xs, ys, ix, iy, dx, dy, ox = [], [], [], [], [], [], []
    sy_e, sx_e = [], []
    for k, (v, w, l) in enumerate(items):
        o = opts(w, l) if rot else [(w, l, 0)]
        x = m.NewIntVar(0, LEN - min(sx for _, sx, _ in o), f"x{k}")
        y = m.NewIntVar(0, W - min(sy for sy, _, _ in o), f"y{k}")
        xs.append(x)
        ys.append(y)
        if len(o) == 1:
            sy, sx, r = o[0]
            if rot:             # ohne Drehung stehen die Grenzen schon im Wertebereich (Modell der Vormessung unverändert)
                m.Add(x + sx <= LEN)
                m.Add(y + sy <= W)
            ix.append(m.NewFixedSizeIntervalVar(x, sx, f"ix{k}"))
            iy.append(m.NewFixedSizeIntervalVar(y, sy, f"iy{k}"))
            dx.append(sy)
            dy.append(sx)
            sy_e.append(sy)
            sx_e.append(sx)
            ox.append([(r, None, sy, sx)])
        else:
            lits, ey, ex, lst = [], 0, 0, []
            for (sy, sx, r) in o:
                lit = m.NewBoolVar(f"r{k}_{r}")
                m.Add(x + sx <= LEN).OnlyEnforceIf(lit)
                m.Add(y + sy <= W).OnlyEnforceIf(lit)
                ix.append(m.NewOptionalFixedSizeIntervalVar(x, sx, lit, f"ix{k}_{r}"))
                iy.append(m.NewOptionalFixedSizeIntervalVar(y, sy, lit, f"iy{k}_{r}"))
                dx.append(sy)
                dy.append(sx)
                lits.append(lit)
                ey = ey + sy * lit
                ex = ex + sx * lit
                lst.append((r, lit, sy, sx))
            m.AddExactlyOne(lits)
            sy_e.append(ey)
            sx_e.append(ex)
            ox.append(lst)
    m.AddNoOverlap2D(ix, iy)
    m.AddCumulative(ix, dx, W)
    m.AddCumulative(iy, dy, LEN)
    k0 = max(range(n), key=lambda k: items[k][1] * items[k][2])
    if lifo:
        for i in range(n):
            for j in range(n):
                if items[i][0] < items[j][0]:
                    a = m.NewBoolVar("")
                    b = m.NewBoolVar("")
                    c = m.NewBoolVar("")
                    m.Add(ys[j] + sy_e[j] <= ys[i]).OnlyEnforceIf(a)
                    m.Add(ys[i] + sy_e[i] <= ys[j]).OnlyEnforceIf(b)
                    m.Add(xs[j] + sx_e[j] <= xs[i]).OnlyEnforceIf(c)
                    m.AddBoolOr([a, b, c])
        for r, lit, sy, sx in ox[k0]:           # nur die Spiegelung in y erhält die Entladereihenfolge
            if lit is None:
                m.Add(2 * ys[k0] <= W - sy)
            else:
                m.Add(2 * ys[k0] <= W - sy).OnlyEnforceIf(lit)
    else:
        for r, lit, sy, sx in ox[k0]:
            if lit is None:
                m.Add(2 * ys[k0] <= W - sy)
                m.Add(2 * xs[k0] <= LEN - sx)
            else:
                m.Add(2 * ys[k0] <= W - sy).OnlyEnforceIf(lit)
                m.Add(2 * xs[k0] <= LEN - sx).OnlyEnforceIf(lit)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.random_seed = seed
    s.parameters.max_deterministic_time = det_time
    st = s.Solve(m)
    det = s.deterministic_time
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        pl = []
        for k in range(n):
            r0 = ox[k][0][0]
            for r, lit, _, _ in ox[k]:
                if lit is not None and s.Value(lit):
                    r0 = r
            pl.append((s.Value(xs[k]), s.Value(ys[k]), r0) if rot else (s.Value(xs[k]), s.Value(ys[k])))
        return "feas", pl, det
    if st == cp_model.INFEASIBLE:
        return "infeas", None, det
    return "unknown", None, det


# ------------------------------------------------------------------------------------------------ Zeichnung nicht packbarer Touren

def partial_pack(items, rot=False):
    """Beste einfache Teil-Packung für die Zeichnung einer nicht packbaren Tour: MaxRects (größte Fläche zuerst); was nicht mehr passt, wird nicht
    gesetzt. Rückgabe (Platzierung je Rechteck oder None, Liste der Indizes ohne Platz). Keine Aussage über die bestmögliche Teil-Packung."""
    free = [(0, 0, LEN, W)]
    pos = [None] * len(items)
    left = []
    for idx in sorted(range(len(items)), key=lambda i: (-items[i][1] * items[i][2], i)):
        _, w, l = items[idx]
        best = None
        for (fx, fy, fl, fw) in free:
            for (sy, sx, r) in (opts(w, l) if rot else [(w, l, 0)]):
                if sx <= fl and sy <= fw:
                    s = (min(fl - sx, fw - sy), max(fl - sx, fw - sy), fx, fy, r)
                    if best is None or s < best[0]:
                        best = (s, fx, fy, sy, sx, r)
        if best is None:
            left.append(idx)
            continue
        _, px, py, sy, sx, r = best
        pos[idx] = (px, py, r)
        free = _split_free(free, px, py, sx, sy)
    return pos, sorted(left)
