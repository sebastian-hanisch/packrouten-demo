"""Plattformfester Zufall: SplitMix64 mit Ganzzahlen. Die ersten Ausgaben für den Zufalls-Seed 0 sind die Referenzwerte des SplitMix64-Verfahrens
(0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4); der Rest steht hier als feste Folge."""

import ast
from pathlib import Path

import prt_rng as R


def test_referenzwerte_von_splitmix64_fuer_seed_0():
    r = R.SplitMix64(0)
    assert r.next() == 0xE220A8397B1DCDAF == 16294208416658607535
    assert r.next() == 0x6E789E6AA1B965F4 == 7960286522194355700


def test_feste_folge_fuer_andere_zufalls_seeds():
    r = R.SplitMix64(1)
    assert [r.next() for _ in range(3)] == [10451216379200822465, 13757245211066428519, 17911839290282890590]
    r = R.SplitMix64(740000 * 8 + 1)
    assert [r.uniform() for _ in range(3)] == [0.5349848546082483, 0.8224795499560326, 0.2921813934396944]


def test_uniform_liegt_im_halboffenen_intervall_und_below_im_bereich():
    r = R.SplitMix64(12345)
    xs = [r.uniform() for _ in range(2000)]
    assert all(0.0 <= x < 1.0 for x in xs)
    assert abs(sum(xs) / len(xs) - 0.5) < 0.03          # Mittel 0,5 mit Standardfehler 0,29 / sqrt(2000) = 0,0065: Band über rund 4 Standardfehler
    assert {R.SplitMix64(s).below(7) for s in range(200)} == set(range(7))
    assert all(0 <= R.SplitMix64(s).below(1) < 1 for s in range(20))


def test_kein_python_hash_und_keine_c_bibliothek_im_zufall():
    """Der Zufall ruft weder hash() noch math oder random auf (Plattformabweichung, pro Prozess gesalzene Hashwerte); geprüft am Syntaxbaum, nicht am Text."""
    tree = ast.parse(Path(R.__file__).read_text(encoding="utf-8"))
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert "hash" not in calls and not imports & {"math", "random", "numpy"}
