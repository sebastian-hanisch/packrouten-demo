"""Rechnet die Suche der fünf Presets (beide Stellungen der Drehung) und schreibt tools/preset_suche.json: die gespeicherten Lösungen, die die App zeigt.

  python tools/preset_suche.py [--presets NAME ...] [--procs 6]

Dieselbe Rechnung wie in der Messreihe M2 (prt_core.run_record: Fläche, Faustregel, Reparatur, Suche L und U mit 400 Iterationen; Zufalls-Seed der Suche 1).
Danach prüft das Skript die Kriterien mit Suche (prt_stories.stufe2). tools/dump_results.py mischt die Datei in data/prt_results.json ein.
Nicht Teil der CI (n = 40 braucht je Stellung Minuten bis über eine Viertelstunde)."""
import argparse
import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import prt_constants as K  # noqa: E402
import prt_core as C  # noqa: E402
import prt_results as R  # noqa: E402
import prt_stories as S  # noqa: E402

OUT = ROOT / "tools" / "preset_suche.json"


def job(name, rot):
    p = K.PRESETS[name]
    inst = C.make_instance(p["n"], p["depot"], p["seed"], p["k"], p["phi"], p["spread"])
    rec = C.run_record(inst, rot=rot, search=True)
    return name, rot, rec


def store(rec, p):
    """Gespeicherte Form wie in data/prt_results.json (Instanzen der Messreihe M2)."""
    out = {k: rec[k] for k in ("area", "area_best", "rep_U", "rep_L", "repls_U", "repls_L", "U", "L")}
    out["rule"] = rec["rule"]
    out["routes"] = {"U": rec["routes"]["U"], "L": rec["routes"]["L"]}
    out["verify"] = rec["verify"]
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--presets", nargs="*")
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--out", default=str(OUT), help="Ausgabedatei (Standard: tools/preset_suche.json); dump_results.py mischt alle tools/preset_suche*.json ein")
    args = ap.parse_args()
    out_path = pathlib.Path(args.out)
    names = args.presets or list(K.PRESETS)
    old = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {"aus": {}, "an": {}}
    recs = {}
    with ProcessPoolExecutor(max_workers=args.procs) as ex:
        futs = [ex.submit(job, nm, rot) for nm in names for rot in (False, True)]
        for fu in as_completed(futs):
            nm, rot, rec = fu.result()
            p = K.PRESETS[nm]
            key = R.instance_key(p["depot"], p["n"], p["k"], p["spread"], p["phi"], p["seed"])
            old["an" if rot else "aus"][key] = store(rec, p)
            recs[(nm, rot)] = rec
            out_path.write_text(json.dumps(old, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
            print(f"fertig: {nm} ({'mit' if rot else 'ohne'} Drehung), Kosten Fläche {rec['area_best']['cost']}, U {rec['U']['cost']}, L {rec['L']['cost']}, Prüfer {rec['verify']}", flush=True)
    for nm in names:
        ok, text = S.stufe2(nm, recs[(nm, False)], recs[(nm, True)])
        print(f"{nm}: {'erfüllt' if ok else 'NICHT erfüllt'}: {text}")


if __name__ == "__main__":
    main()
