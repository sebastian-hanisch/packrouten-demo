"""Sucht für jedes Preset den kleinsten Zufalls-Seed aus 740000 bis 740199, dessen Instanz die Geschichte des Presets zeigt (Kriterien: prt_stories.py).

  python tools/find_preset_seeds.py stufe1 [--kandidaten 12] [--procs 6]      Fläche und Status der Touren (schnell), ohne und mit Drehung
  python tools/find_preset_seeds.py stufe2 NAME SEED [--procs 2]              Suche in beiden Stellungen, Kriterien mit Suche

Nicht Teil der CI (rechnet Minuten bis Stunden). Ergebnis: tools/PRESET_SWEEP.md und die Seeds in prt_constants.PRESETS; die gespeicherte Suche der Presets
schreibt tools/preset_suche.py."""
import argparse
import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import prt_constants as K  # noqa: E402
import prt_core as C  # noqa: E402
import prt_stories as S  # noqa: E402

SEED0 = 740000


def make(name, seed):
    p = K.PRESETS[name]
    return C.make_instance(p["n"], p["depot"], seed, p["k"], p["phi"], p["spread"])


def probe_job(name, seed):
    inst = make(name, seed)
    pk_aus, pk_an = C.Packer(inst, False), C.Packer(inst, True)
    probe = {"aus": {}, "an": {}, "cost": {}}
    for th in S.THETAS_NEEDED[name]:
        ra = C.solve_area(inst, th)
        probe["cost"][th] = C.stats(inst, ra, C.F_FIX)[2]
        probe["aus"][th] = [C.tour_info(inst, pk_aus, r) for r in ra]
        probe["an"][th] = [C.tour_info(inst, pk_an, r) for r in ra]
    ok, text = S.stufe1(name, probe)
    return name, seed, ok, text


def record_job(name, seed, rot):
    inst = make(name, seed)
    rec = C.run_record(inst, rot=rot, search=True)
    rec.pop("routes")
    return name, seed, rot, rec


def stufe1(args):
    names = args.presets or list(K.PRESETS)
    res = {}
    with ProcessPoolExecutor(max_workers=args.procs) as ex:
        futs = [ex.submit(probe_job, nm, SEED0 + i) for nm in names for i in range(args.kandidaten)]
        for fu in as_completed(futs):
            nm, seed, ok, text = fu.result()
            res.setdefault(nm, {})[seed] = (ok, text)
    for nm in names:
        print(f"## {nm}")
        for seed in sorted(res[nm]):
            ok, text = res[nm][seed]
            print(f"  {seed}: {'TREFFER' if ok else 'nein   '}  {text}")


def stufe2(args):
    seed = int(args.seed)
    with ProcessPoolExecutor(max_workers=args.procs) as ex:
        futs = [ex.submit(record_job, args.name, seed, rot) for rot in (False, True)]
        recs = {}
        for fu in as_completed(futs):
            nm, sd, rot, rec = fu.result()
            recs[rot] = rec
    ok, text = S.stufe2(args.name, recs[False], recs[True])
    print(json.dumps({"preset": args.name, "seed": seed, "erfuellt": ok, "text": text}, ensure_ascii=False))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("stufe1")
    a.add_argument("--kandidaten", type=int, default=12)
    a.add_argument("--procs", type=int, default=6)
    a.add_argument("--presets", nargs="*")
    b = sub.add_parser("stufe2")
    b.add_argument("name")
    b.add_argument("seed")
    b.add_argument("--procs", type=int, default=2)
    args = ap.parse_args()
    {"stufe1": stufe1, "stufe2": stufe2}[args.cmd](args)


if __name__ == "__main__":
    main()
