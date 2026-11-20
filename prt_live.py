"""Live-Rechnung der App: Flächenlösung mit Status und Ladeflächen je Tour, Reparatur und Faustregel, optional die kleine Live-Suche (n ≤ 20).

Alles ist eine reine Funktion der Einstellungen (Zwischenspeicher mit lru_cache über die Argumente). Der Zufall ist SplitMix64, die CP-SAT-Zeiten sind deterministisch.
Messung der Rechenzeit (Messreihe (d), Wanduhr, unter Last, lokal; auf Streamlit Cloud nicht gemessen): Fläche bei θ = 0,90 mit Prüfung plus Reparatur bei n = 40 im Mittel
6,9 s, größter Wert 13,0 s."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import prt_constants as K
import prt_core as C
import prt_pack as P


@dataclass(frozen=True)
class Settings:
    n: int
    k: int
    spread: str
    phi: float
    depot: str
    theta: float
    rot: bool
    seed: int

    def inst_args(self):
        return (self.n, self.depot, self.seed, self.k, self.phi, self.spread)


def live_det(n, rot):
    """CP-SAT-Zeit je Tour für den Status live: bis 20 Kunden die der Messreihen (ohne Drehung 0,3, mit 1,0), bei 40 Kunden kleiner (0,3)."""
    return K.LIVE_DET_N40 if n > 20 else C.DET_STATUS[rot]


@lru_cache(maxsize=8)
def instance(n, depot, seed, k, phi, spread):
    return C.make_instance(n, depot, seed, k, phi, spread)


def tour_draw(inst, pk, r, with_l=True):
    """Status (U und, mit `with_l`, L) und Platzierungen einer Tour für die Zeichnung. Nicht packbare oder unbekannte Touren zeigen die einfache Teil-Packung (partial_pack)."""
    rot = pk.rot
    det = pk.status_det()
    su, plu, _ = pk.exact_status(r, False, det)
    cust_u = [c for c in r for _ in inst.items[c]]
    rect_u = [(w, l) for c in r for (w, l) in inst.items[c]]
    out = {"route": list(r), "fill": round(sum(inst.dem[c] for c in r) / C.AREA, 4), "parts": len(rect_u), "u": su,
           "cust": cust_u, "rect": rect_u, "u_place": None, "u_left": [], "l": None, "l_place": None, "l_order": None, "l_cust": None, "l_rect": None}
    if su == "feas":
        out["u_place"] = [tuple(p) for p in plu]
        sl, pll, order = pk.exact_status(r, True, det) if with_l else ("skip", None, None)
        out["l"] = sl
        if sl == "feas":
            out["l_order"] = list(order)
            out["l_cust"] = [c for c in order for _ in inst.items[c]]
            out["l_rect"] = [(w, l) for c in order for (w, l) in inst.items[c]]
            out["l_place"] = [tuple(p) for p in pll]
    else:
        out["l"] = "skip" if not with_l else ("infeas" if su == "infeas" else "unknown")
        place, left = P.partial_pack([(0, w, l) for (w, l) in rect_u], rot)
        out["u_place"] = place
        out["u_left"] = left
    return out


@lru_cache(maxsize=12)
def area_view(n, depot, seed, k, phi, spread, rot, theta):
    """Flächenlösung bei θ mit Status und Zeichnung je Tour (die Hauptansicht)."""
    inst = instance(n, depot, seed, k, phi, spread)
    pk = C.Packer(inst, rot=rot, det_status=live_det(n, rot))
    ra = C.solve_area(inst, theta)
    V, D, cost = C.stats(inst, ra, C.F_FIX)
    with_l = n <= K.LIVE_L_MAX_N
    return {"xy": inst.xy, "n": n, "fill": round(inst.meta["fill"], 4), "versuche": inst.meta["versuche"], "routes": [list(r) for r in ra], "V": V, "D": D, "cost": cost,
            "with_l": with_l, "det": pk.status_det(), "tours": [tour_draw(inst, pk, r, with_l) for r in ra]}


@lru_cache(maxsize=12)
def base_record(n, depot, seed, k, phi, spread, rot):
    """Fläche (θ = 1,00), Faustregel, Reparatur roh und mit lokaler Suche, nur für U (wie die Messreihe M2, ohne Suche und ohne die Schritte für L)."""
    inst = instance(n, depot, seed, k, phi, spread)
    rec = C.run_record(inst, rot=rot, search=False, packer=C.Packer(inst, rot=rot, det_status=live_det(n, rot)), modes=("U",))
    rec["xy"] = inst.xy
    return rec


@lru_cache(maxsize=6)
def search_record(n, depot, seed, k, phi, spread, rot):
    """Live-Suche (n ≤ 20): kleines Budget (100 Iterationen, CP-SAT-Zeit 2 je Instanz), kalter Packer; Messreihe (d), Teil (v)."""
    if n > K.LIVE_SEARCH_MAX_N:
        raise ValueError("Live-Suche nur bis 20 Kunden")
    inst = instance(n, depot, seed, k, phi, spread)
    pk = C.Packer(inst, rot=rot, exact_det_max=K.LIVE_SEARCH_DET_MAX)
    rec = C.run_record(inst, rot=rot, search=True, packer=pk, search_iters=K.LIVE_SEARCH_ITERS)
    rec["xy"] = inst.xy
    return rec


def as_record(rec):
    """Ein Datensatz in der Form der gespeicherten Instanzen (Kennzahlen und Routen der Suche) aus einem live gerechneten."""
    out = {k: rec[k] for k in ("area", "area_best", "rep_U", "rep_L", "repls_U", "repls_L", "U", "L") if k in rec}
    out["rule"] = rec["rule"]
    out["routes"] = {k: rec["routes"][k] for k in ("U", "L") if k in rec["routes"]}
    return out


def clear_caches():
    for fn in (instance, area_view, base_record, search_record):
        fn.cache_clear()
