"""Erzeugt data/prt_results.json aus den Rohdaten der Messreihen (Sweeps als JSONL, nicht im Repo) und der gespeicherten Suche der Presets.

  python tools/dump_results.py [--quelle ORDNER] [--out DATEI]

Die Rohdaten liegen im Ordner `tourenplanung-planung` neben dem Demo-Ordner: messreihe_packrouten (ohne Drehung: Vormessung), messreihe_packrouten_ap0 (Kontrollen ohne
Drehung), messreihe_packrouten_drehung (mit Drehung). Die Datei enthält nur Aggregate und die gespeicherten Lösungen (Routen) der M2-Instanzen und der Presets
(Größe < 300 kB). Schwellen und Zählungen sind die der Messreihen (messplan_packrouten.md, Abschnitt 5; ERGEBNIS.md je Messreihe)."""
import argparse
import json
import pathlib
import statistics as stat
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import prt_constants as K  # noqa: E402

DEFAULT_SRC = ROOT.parent / "tourenplanung-planung"
STATES = ("aus", "an")
FOLDER = {"aus": "messreihe_packrouten", "an": "messreihe_packrouten_drehung"}


def load(path):
    """Zeilen einer JSONL-Datei; bei doppeltem Schlüssel gilt die erste Zeile (wie in den Auswertungen der Messreihen)."""
    rows, seen = [], set()
    p = pathlib.Path(path)
    if not p.exists():
        return rows
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("_key") in seen:
            continue
        seen.add(r.get("_key"))
        rows.append(r)
    return rows


def rel(a, b):
    return (a - b) / b * 100.0


def rd(x, d=4):
    return None if x is None else round(x, d)


# ------------------------------------------------------------------------------------------------ M1: Zellen, Füllgrad

def m1_block(rows):
    cells = defaultdict(list)
    tours = []
    for r in rows:
        for th, d in r["theta"].items():
            cells[(r["depot"], r["n"], r["k"], r["spread"], float(th))].append(d)
            for x in d["routes"]:
                tours.append({"spread": r["spread"], **x})
    zellen = []
    for (depot, n, k, sp, th), lst in sorted(cells.items()):
        N = len(lst)
        pmin = sum(1 for d in lst if any(x["u"] == "infeas" for x in d["routes"])) / N
        pmax = sum(1 for d in lst if any(x["u"] in ("infeas", "unknown") for x in d["routes"])) / N
        lmin = sum(1 for d in lst if any(x["l"] == "infeas" for x in d["routes"])) / N
        lmax = sum(1 for d in lst if any(x["l"] in ("infeas", "unknown") for x in d["routes"])) / N
        zellen.append({"depot": depot, "n": n, "k": k, "spread": sp, "theta": th, "N": N, "pmin": rd(pmin), "pmax": rd(pmax), "lmin": rd(lmin), "lmax": rd(lmax),
                       "V": rd(stat.mean(d["V"] for d in lst), 3)})
    fuell = {}
    for sp in ("gleich", "gemischt"):
        fuell[sp] = []
        for lo, hi in K.FILL_BINS:
            g = [x for x in tours if lo <= x["fill"] < hi and x["spread"] == sp and x["u"] in ("feas", "infeas")]
            fuell[sp].append({"lo": lo, "hi": hi, "N": len(g), "infeas": sum(1 for x in g if x["u"] == "infeas")})
    hi_t = [x for x in tours if x["fill"] >= 0.85 and x["u"] in ("feas", "infeas")]

    def share(sel):
        g = [x for x in hi_t if sel(x)]
        return {"N": len(g), "infeas": sum(1 for x in g if x["u"] == "infeas")}

    m1b = {"gleich": share(lambda x: x["spread"] == "gleich"), "gemischt": share(lambda x: x["spread"] == "gemischt"),
           "teile_le10": share(lambda x: x["parts"] <= 10), "teile_ge11": share(lambda x: x["parts"] >= 11),
           "touren_gesamt": len(tours), "mit_bekanntem_status": len(hi_t),
           "unbekannt": sum(1 for x in tours if x["u"] == "unknown")}
    return {"instanzen": len(rows), "zellen": zellen, "fuell": fuell, "m1b": m1b}


def kipp_theta(zellen):
    """Je (Depot, n, k, Form): kleinstes θ des Rasters mit p_min ≥ 0,5 ('nie' = None)."""
    out = {}
    groups = defaultdict(list)
    for c in zellen:
        groups[(c["depot"], c["n"], c["k"], c["spread"])].append(c)
    for key, lst in sorted(groups.items()):
        oft = sorted(c["theta"] for c in lst if c["pmin"] >= K.M1_OFT)
        out["|".join(str(x) for x in key)] = oft[0] if oft else None
    return out


# ------------------------------------------------------------------------------------------------ M2 bis M5

def m2_zellen(rows):
    cells = defaultdict(list)
    for r in rows:
        cells[(r["depot"], r["n"], r["k"], r["spread"], r["phi"])].append(r)
    tab = []
    for (depot, n, k, sp, phi), lst in sorted(cells.items()):
        dU = [rel(r["U"]["cost"], r["area_best"]["cost"]) for r in lst]
        dL = [rel(r["L"]["cost"], r["U"]["cost"]) for r in lst]
        repU = [rel(r["repls_U"]["cost"], r["U"]["cost"]) for r in lst]
        repUV = [r["repls_U"]["V"] - r["U"]["V"] for r in lst]
        rep0U = [rel(r["rep_U"]["cost"], r["U"]["cost"]) for r in lst]
        c = {"depot": depot, "n": n, "k": k, "spread": sp, "phi": phi, "N": len(lst),
             "dU": stat.mean(dU), "dU1": sum(1 for x in dU if x >= 1) / len(dU), "dVU": stat.mean(r["U"]["V"] - r["area_best"]["V"] for r in lst),
             "dL": stat.mean(dL), "dL05": sum(1 for x in dL if x >= 0.5) / len(dL),
             "repU": stat.mean(repU), "repUV": stat.mean(repUV), "rep0U": stat.mean(rep0U),
             "keine_regel_U": sum(1 for r in lst if r["rule"]["U"] is None)}
        c["relU"] = c["dU"] >= K.M2_REL_MEAN and c["dU1"] >= K.M2_REL_SHARE1
        c["nonU"] = c["dU"] < K.M2_NON_MEAN
        c["relL"] = c["dL"] >= K.M3_REL_MEAN and c["dL05"] >= K.M3_REL_SHARE05
        c["nonL"] = c["dL"] < K.M3_NON_MEAN
        c["okU"] = c["repU"] <= K.M4_OK_REP and c["repUV"] <= K.M4_OK_DV
        c["badU"] = c["repU"] >= K.M4_BAD_REP or c["repUV"] >= K.M4_BAD_DV
        tab.append({k_: (rd(v, 4) if isinstance(v, float) else v) for k_, v in c.items()})
    return tab


def m2_gesamt(rows):
    dU = [rel(r["U"]["cost"], r["area_best"]["cost"]) for r in rows]
    dL = [rel(r["L"]["cost"], r["U"]["cost"]) for r in rows]
    out = {"N": len(rows), "dU_mean": rd(stat.mean(dU)), "dU_median": rd(stat.median(dU)), "dL_mean": rd(stat.mean(dL)), "dL_median": rd(stat.median(dL)),
           "dVU_mean": rd(stat.mean(r["U"]["V"] - r["area_best"]["V"] for r in rows)),
           "dU_ge10": sum(1 for x in dU if x >= 10), "dU_lt05": sum(1 for x in dU if x < 0.5),
           "dV_ge1": sum(1 for r in rows if r["U"]["V"] - r["area_best"]["V"] >= 1),
           "U_unter_flaeche": sum(1 for r in rows if r["U"]["cost"] < r["area_best"]["cost"]),
           "L_unter_U": sum(1 for r in rows if r["L"]["cost"] < r["U"]["cost"]),
           "verify_fehler": sum(1 for r in rows if r["verify"]["U"] or r["verify"]["L"]),
           "unbekannt_je_instanz": rd(stat.mean(r["packer"]["unknown"] for r in rows), 2),
           "exakt_je_instanz": rd(stat.mean(r["packer"]["exact"] for r in rows), 1),
           "zeit_mittel_s": rd(stat.mean(r["t"] for r in rows), 1)}
    # Reparatur gegen Suche (M4)
    for mode in ("U", "L"):
        raw = [rel(r["rep_" + mode]["cost"], r[mode]["cost"]) for r in rows]
        ls = [rel(r["repls_" + mode]["cost"], r[mode]["cost"]) for r in rows]
        out["rep_" + mode] = {"roh_mean": rd(stat.mean(raw)), "roh_median": rd(stat.median(raw)), "ls_mean": rd(stat.mean(ls)), "ls_median": rd(stat.median(ls)),
                              "ls_le1": sum(1 for x in ls if x <= 1.0), "roh_unter_suche": sum(1 for x in raw if x < 0), "ls_unter_suche": sum(1 for x in ls if x < 0), "dV_ls": rd(stat.mean(r["repls_" + mode]["V"] - r[mode]["V"] for r in rows), 3)}
        # Faustregel (M5)
        cnt = defaultdict(int)
        extra = []
        for r in rows:
            ru = r["rule"][mode]
            if ru is None:
                cnt["keine"] += 1
            else:
                cnt[str(ru["theta"])] += 1
                extra.append(rel(ru["cost"], r[mode]["cost"]))
        out["regel_" + mode] = {"verteilung": dict(cnt), "mehrkosten_mean": rd(stat.mean(extra)) if extra else None,
                                "mehrkosten_median": rd(stat.median(extra)) if extra else None, "N_mit_regel": len(extra),
                                "unter_suche": sum(1 for x in extra if x < 0), "unter_suche_min": rd(min(extra)) if extra else None}
    return out


def m2_gruppen(rows):
    """Je (n, k, Form): Mittel über die Depots, φ und Instanzen (Teile je Fahrzeug = 1,8 n / k)."""
    g = defaultdict(list)
    for r in rows:
        g[(r["n"], r["k"], r["spread"])].append(r)
    out = []
    for (n, k, sp), lst in sorted(g.items()):
        dU = [rel(r["U"]["cost"], r["area_best"]["cost"]) for r in lst]
        dL = [rel(r["L"]["cost"], r["U"]["cost"]) for r in lst]
        out.append({"n": n, "k": k, "spread": sp, "teile_je_fahrzeug": round(1.8 * n / k, 1), "N": len(lst), "dU": rd(stat.mean(dU)), "dU_median": rd(stat.median(dU)),
                    "dV": rd(stat.mean(r["U"]["V"] - r["area_best"]["V"] for r in lst), 3), "dL": rd(stat.mean(dL)),
                    "keine_regel_U": sum(1 for r in lst if r["rule"]["U"] is None)})
    return out


def stored_instances(rows):
    out = {}
    for r in rows:
        key = f"{r['depot']}|{r['n']}|{r['k']}|{r['spread']}|{r['phi']:.2f}|{r['seed']}"
        rec = {name: r[name] for name in ("area", "area_best", "rep_U", "rep_L", "repls_U", "repls_L", "U", "L")}
        rec["rule"] = r["rule"]
        rec["routes"] = r["routes"]
        out[key] = rec
    return out


# ------------------------------------------------------------------------------------------------ M6, M7, K2, Kontrollen

def m6_block(rows):
    if not rows:
        return None
    gaps = [(r["U"] - r["oracle"]) / r["oracle"] * 100.0 for r in rows]
    return {"N": len(rows), "gap_mean": rd(stat.mean(gaps), 3), "gap_max": rd(max(gaps), 3), "unter_optimum": sum(1 for r in rows if r["U"] < r["oracle"] - 1e-6 and r["unsicher"] == 0),
            "unsichere_mengen": sum(r["unsicher"] for r in rows), "flaeche_gegen_orakel": rd(stat.mean((r["area"] - r["oracle"]) / r["oracle"] * 100.0 for r in rows), 2),
            "rep_gegen_orakel": rd(stat.mean((r["rep"] - r["oracle"]) / r["oracle"] * 100.0 for r in rows), 2)}


def m7_block(rows):
    flat = [(r["spread"], x) for r in rows for x in r["rows"]]
    out = {"instanzen": len(rows)}
    for lifo, nm in ((False, "U"), (True, "L")):
        g = [x for s, x in flat if x["lifo"] == lifo]
        kn = [x for x in g if x["exact"] in ("feas", "infeas")]
        gap = [x for x in kn if (not x["heur"]) and x["exact"] == "feas"]
        blk = {"touren": len(g), "bekannt": len(kn), "heur_nein_exakt_ja": len(gap), "unbekannt": sum(1 for x in g if x["exact"] == "unknown"), "je_fuellgrad": []}
        for lo, hi in ((0.5, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)):
            kk = [x for x in kn if lo <= x["fill"] < hi]
            blk["je_fuellgrad"].append({"lo": lo, "hi": hi, "bekannt": len(kk), "gap": sum(1 for x in kk if (not x["heur"]) and x["exact"] == "feas")})
        out[nm] = blk
    return out


def k2_block(rows):
    if not rows:
        return None
    dU = [(r["k2_U"]["cost"] - r["m2"]["U"]) / r["m2"]["U"] * 100.0 for r in rows]
    dL = [(r["k2_L"]["cost"] - r["m2"]["L"]) / r["m2"]["L"] * 100.0 for r in rows]
    return {"N": len(rows), "dU_mean": rd(stat.mean(dU), 2), "dL_mean": rd(stat.mean(dL), 2), "beste_verbesserung_U": rd(-min(dU), 2), "mehr_als_05": sum(1 for x in dU if x < -0.5), "unveraendert": sum(1 for x in dU if abs(x) < 1e-9)}


def a_block(rows):
    """Güte der Suche bei 40 Kunden: Lücke der fünffach längeren Suche B zu A (Kosten U)."""
    if not rows:
        return None
    gaps = []
    for r in rows:
        a, b = r["A"]["U"]["cost"], r["B_U"]["cost"]
        gaps.append((a - b) / b * 100.0)
    return {"N": len(rows), "gap_mean": rd(stat.mean(gaps), 2), "gap_max": rd(max(gaps), 2), "gap_gt2": sum(1 for g in gaps if g > 2.0)}


def c2_beide_nie(text_path):
    """Je Layout (lang, kompakt): Gruppen mit Kipp-θ nahe der Basis, in denen Layout und Basis beide „nie im Raster“ haben (aus dem Auswertungstext der Messreihe)."""
    import re
    out = {"lang": 0, "kompakt": 0}
    for m in re.finditer(r"Kipp-θ \S+ \S+: (lang|kompakt) (\S+) gegen Basis (\S+) -> nahe: (True|False)", pathlib.Path(text_path).read_text(encoding="utf-8")):
        if m.group(2) == "None" and m.group(3) == "None" and m.group(4) == "True":
            out[m.group(1)] += 1
    return out


def pruefer_und_suche(folder_m2, folder_kontrolle):
    """Prüfer-Fehler (unabhängiger Prüfer besteht eine Lösung nicht), Lauf C gegen Lauf B und die Live-Suche (Messreihe (d), Teil v) gegen die gespeicherte Suche."""
    m2 = load(folder_m2 / "sweep_m2.jsonl")
    c1 = load(folder_kontrolle / "sweep_c1.jsonl")
    ab = {(r["k"], r["spread"], r["phi"], r["i"]): r for r in load(folder_kontrolle / "sweep_a_ab.jsonl")}
    ac = load(folder_kontrolle / "sweep_a_c.jsonl")
    vs = [r for r in load(folder_kontrolle / "sweep_d.jsonl") if r["n"] == 20 and "v" in r]
    c_gegen_b = [rel(r["C_U"]["cost"], ab[(r["k"], r["spread"], r["phi"], r["i"])]["B_U"]["cost"]) for r in ac]
    v = [rel(r["v"]["cost"], r["cost_iii"]) for r in vs]
    return {"pruefer": {"m2_n": len(m2), "m2_fehler": sum(1 for r in m2 if r["verify"]["U"] or r["verify"]["L"]), "c1_n": len(c1), "c1_fehler": sum(1 for r in c1 if r["verify"]),
                        "a_c_n": len(ac), "a_c_fehler": sum(1 for r in ac if r["C_verify"])},
            "c_gegen_b": {"N": len(c_gegen_b), "billiger": sum(1 for x in c_gegen_b if x < 0), "beste_einsparung": rd(-min(c_gegen_b), 2)},
            "v_live_gegen_gespeichert": {"N": len(v), "mean": rd(stat.mean(v), 2), "beste_einsparung": rd(-min(v), 2), "billiger_oder_gleich": sum(1 for x in v if x <= 0),
                                         "zeit_mean_s": rd(stat.mean(r["v"]["t_total"] for r in vs), 1), "zeit_max_s": rd(max(r["v"]["t_total"] for r in vs), 1)},
            "d_n40": sum(1 for r in load(folder_kontrolle / "sweep_d.jsonl") if r["n"] == 40)}


def kontrollen(src):
    """Zahlen aus den Auswertungen der Messreihen (analyse_*.json, Ampel-Texte nicht übernommen) und aus den Rohdaten der Kontrollen."""
    out = {}
    ap0 = json.loads((src / "messreihe_packrouten_ap0" / "analyse.json").read_text(encoding="utf-8"))
    dr = json.loads((src / "messreihe_packrouten_drehung" / "analyse_dr.json").read_text(encoding="utf-8"))
    quellen = {"aus": (ap0, src / "messreihe_packrouten", src / "messreihe_packrouten_ap0", src / "messreihe_packrouten_ap0" / "analyse_out.txt"),
               "an": (dr, src / "messreihe_packrouten_drehung", src / "messreihe_packrouten_drehung", src / "messreihe_packrouten_drehung" / "analyse_dr_out.txt")}
    for s, (d, f_m2, f_kon, f_txt) in quellen.items():
        out[s] = {"c1_rho": {k: rd(v, 3) for k, v in d["c1"]["rho"].items()}, "c1_n": d["c1"]["n"],
                  "c2_nie_oft": d["c2"]["nie_oft"], "c2_nahe": d["c2"]["close"], "c2_nahe_beide_nie": c2_beide_nie(f_txt),
                  "d_t40_mean": rd(d["d"]["t40_mean"], 1), "d_t_max": rd(d["d"]["t_max"], 1),
                  "e_identisch": d["e"]["identisch"], "e_zeilen": d["e"]["zeilen"], "e_status_gleich": rd(d["e"]["status_gleich"], 4), "e_wechsel": d["e"]["wechsel"]}
        out[s].update(pruefer_und_suche(f_m2, f_kon))
    out["aus"]["b_R"] = {k: rd(v, 3) for k, v in ap0["b"]["R"].items()}
    out["aus"]["b_n"] = ap0["b"]["n"]
    return out


def merge_presets(folder):
    """Alle tools/preset_suche*.json (gespeicherte Suche der Presets, tools/preset_suche.py) zu {"aus": {...}, "an": {...}} zusammenführen."""
    out = {"aus": {}, "an": {}}
    for p in sorted(pathlib.Path(folder).glob("preset_suche*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        for s in STATES:
            out[s].update(d.get(s, {}))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quelle", default=str(DEFAULT_SRC))
    ap.add_argument("--out", default=str(ROOT / "data" / "prt_results.json"))
    args = ap.parse_args()
    src = pathlib.Path(args.quelle)
    presets = merge_presets(ROOT / "tools")
    res = {"version": 1, "quelle": "Messreihen packrouten (ohne Drehung), packrouten_ap0, packrouten_drehung; Stand 2026-11-19"}
    for s in STATES:
        folder = src / FOLDER[s]
        m1 = m1_block(load(folder / "sweep_m1.jsonl"))
        m2_rows = load(folder / "sweep_m2.jsonl")
        blk = {"m1": m1, "kipp": kipp_theta(m1["zellen"]), "m2_zellen": m2_zellen(m2_rows), "m2": m2_gesamt(m2_rows), "m2_gruppen": m2_gruppen(m2_rows),
               "m6": m6_block(load(folder / "sweep_m6.jsonl")), "m7": m7_block(load(folder / "sweep_m7.jsonl")), "instanzen": stored_instances(m2_rows)}
        if s == "aus":
            blk["k2"] = k2_block(load(folder / "sweep_k2.jsonl"))
            blk["a"] = a_block(load(src / "messreihe_packrouten_ap0" / "sweep_a_ab.jsonl"))
            sub = [r for r in m2_rows if r["i"] < 3]
            blk["m2_96"] = m2_gesamt(sub)
            blk["m2_zellen_96"] = m2_zellen(sub)
            blk["m2_gruppen_96"] = m2_gruppen(sub)
        else:
            blk["a"] = a_block(load(folder / "sweep_a_ab.jsonl"))
        blk["instanzen"].update(presets.get(s, {}))
        res[s] = blk
    res["kontrollen"] = kontrollen(src)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"{out} geschrieben: {out.stat().st_size / 1000:.0f} kB")


if __name__ == "__main__":
    main()
