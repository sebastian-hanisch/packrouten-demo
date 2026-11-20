"""Presets: Aufbau, Zufalls-Seeds außerhalb der belegten Bereiche, Hervorhebung, Einrasten der Permalink-Werte, und die Geschichte jedes Presets
(Kriterien in prt_stories.py, festgelegt vor der Suche der Zufalls-Seeds): an künstlichen Werten, an der Neuberechnung und an der gespeicherten Suche."""

import pytest

import prt_constants as K
import prt_core as C
import prt_presets as PR
import prt_results as R
import prt_stories as S

# Zufalls-Seed-Bereiche der Messreihen (Vormessung, AP 0, Drehung): die Preset-Seeds liegen außerhalb
BELEGT = [(1000, 1010), (100000, 100004), (600000, 600011), (605000, 605009), (609000, 609014), (610000, 610005), (700000, 700002), (710000, 710003),
          (711000, 711005), (712000, 712007), (720000, 720004), (730000, 730001), (731000, 731019), (795000, 795009)]


def test_fuenf_presets_mit_hilfetext_und_gemessenen_stufen():
    assert list(K.PRESETS) == ["Standard", "Wenige große Teile", "Viele kleine Teile", "Grenzfall bei voller Auslastung", "Reihenfolge kostet"]
    assert set(K.PRESET_HELP) == set(K.PRESETS) and all(len(h) > 40 for h in K.PRESET_HELP.values())
    for name, p in K.PRESETS.items():
        assert set(p) == {"n", "k", "spread", "phi", "depot", "theta", "seed"}, name
        assert p["n"] in K.N_CHOICES and p["k"] in K.K_CHOICES and p["spread"] in K.SPREAD_CHOICES and p["phi"] in K.PHI_CHOICES and p["depot"] in K.DEPOT_CHOICES and p["theta"] in K.THETA_CHOICES


def test_grenzfall_preset_sagt_im_hilfetext_dass_der_name_die_instanz_meint():
    """Ohne Drehung meldet die App für die Zelle des Presets „Fläche reicht oft nicht“; der Name meint die Instanz (Prüfer-Befund B18)."""
    from prt_evaluation import m1_class
    p = K.PRESETS["Grenzfall bei voller Auslastung"]
    cell = R.m1_cell(False, p["depot"], p["n"], p["k"], p["spread"], p["theta"])
    assert m1_class(cell) == "oft"
    assert "ohne Drehung meldet die App für die Zelle dieser Einstellung „Fläche reicht oft nicht“" in K.PRESET_HELP["Grenzfall bei voller Auslastung"]
    assert m1_class(R.m1_cell(True, p["depot"], p["n"], p["k"], p["spread"], p["theta"])) == "dazwischen"


def test_preset_seeds_liegen_in_der_suche_und_ausserhalb_aller_belegten_bereiche():
    for name, p in K.PRESETS.items():
        assert 740000 <= p["seed"] <= 740199, name
        assert not any(lo <= p["seed"] <= hi for lo, hi in BELEGT), name
    assert all(not (lo <= s <= hi) for s in K.MESSREIHE_SEEDS for lo, hi in BELEGT if (lo, hi) != (610000, 610005))
    assert all(p["seed"] > K.OWN_SEED_MAX for p in K.PRESETS.values())                   # „Neue Instanz“ würfelt 0 bis 299: nie ein Preset


def test_voreinstellung_ist_das_erste_preset_und_drehung_standard_aus():
    p = K.PRESETS["Standard"]
    assert (K.DEFAULT_N, K.DEFAULT_K, K.DEFAULT_SPREAD, K.DEFAULT_PHI, K.DEFAULT_DEPOT, K.DEFAULT_THETA, K.DEFAULT_SEED) == (p["n"], p["k"], p["spread"], p["phi"], p["depot"], p["theta"], p["seed"])
    assert K.DEFAULT_ROT is False
    assert PR.SETTING_SPECS["rot_toggle"].default == 0


# ------------------------------------------------------------------------------------------------ Hervorhebung

def _values(name=None, **change):
    vals = {sk: spec.default for sk, spec in PR.SETTING_SPECS.items()}
    if name:
        for key, state_key in PR.PRESET_KEYS.items():
            vals[state_key] = PR.preset_value(K.PRESETS[name], key)
    vals.update(change)
    return vals


@pytest.mark.parametrize("name", list(K.PRESETS))
def test_aktives_preset_ist_zustandslos_und_ignoriert_die_drehung(name):
    assert PR.aktives_preset(_values(name)) == name
    assert PR.aktives_preset(_values(name, rot_toggle=True)) == name                      # die Drehung gehört nicht zum Szenario
    for state_key in PR.PRESET_KEYS.values():
        spec = PR.SETTING_SPECS[state_key]
        current = _values(name)[state_key]
        other = next(c for c in spec.choices if c != current) if spec.choices else current + 1
        assert PR.aktives_preset(_values(name, **{state_key: other})) != name, state_key   # jede Änderung hebt die Markierung auf


def test_preset_schluessel_decken_alle_regler_ausser_der_drehung_ab():
    assert set(PR.PRESET_KEYS.values()) | set(PR.PRESET_IGNORE) == set(PR.SETTING_SPECS)


# ------------------------------------------------------------------------------------------------ Einrasten

def test_permalink_werte_rasten_auf_gemessene_stufen_ein():
    sp = PR.SETTING_SPECS
    assert PR.snap(sp["theta_slider"], "0.93") == 90 and PR.snap(sp["theta_slider"], "0.99") == 100 and PR.snap(sp["theta_slider"], "0.1") == 70 and PR.snap(sp["theta_slider"], "80") == 80 and PR.snap(sp["theta_slider"], "x") is None
    assert PR.snap(sp["n_radio"], "33") == 40 and PR.snap(sp["n_radio"], "26") == 20 and PR.snap(sp["k_radio"], "4") in (3, 5)
    assert PR.snap(sp["phi_radio"], "0.8") == 0.75 and PR.snap(sp["phi_radio"], "0.86") == 0.9
    assert PR.snap(sp["spread_radio"], "gleich") == "gleich" and PR.snap(sp["spread_radio"], "quadrat") is None
    assert PR.snap(sp["depot_radio"], "mitte") == "mitte" and PR.snap(sp["depot_radio"], "ecke") is None
    assert PR.snap(sp["seed_input"], "-5") == 0 and PR.snap(sp["seed_input"], "99999999") == K.SEED_MAX and PR.snap(sp["seed_input"], "abc") is None
    assert PR.snap(sp["rot_toggle"], "1") == 1 and PR.snap(sp["rot_toggle"], "0") == 0


# ------------------------------------------------------------------------------------------------ Geschichten: künstliche Werte an den Schwellen

def _t(u="feas", l="feas"):
    return {"u": u, "l": l}


def _probe(aus=None, an=None, cost=None):
    return {"aus": aus or {}, "an": an or {}, "cost": cost or {}}


def test_stufe1_standard_kippt_bei_einer_nicht_packbaren_oder_unbekannten_tour():
    ok = _probe(aus={0.9: [_t(), _t()]})
    assert S.stufe1("Standard", ok)[0] is True
    assert S.stufe1("Standard", _probe(aus={0.9: [_t(), _t("unknown")]}))[0] is False
    assert S.stufe1("Standard", _probe(aus={0.9: [_t(), _t("infeas")]}))[0] is False


def test_stufe1_wenige_grosse_teile_braucht_beide_theta():
    two = {0.9: [_t("infeas")], 0.8: [_t("infeas")]}
    assert S.stufe1("Wenige große Teile", _probe(an=two))[0] is True
    assert S.stufe1("Wenige große Teile", _probe(an={0.9: [_t("infeas")], 0.8: [_t("unknown"), _t()]}))[0] is False
    assert S.stufe1("Wenige große Teile", _probe(an={0.9: [_t()], 0.8: [_t("infeas")]}))[0] is False


def test_stufe1_viele_kleine_teile_kostenverhaeltnis_an_der_schwelle():
    aus = {0.9: [_t()]}
    assert S.stufe1("Viele kleine Teile", _probe(aus=aus, cost={0.9: 1005, 1.0: 1000}))[0] is True        # 0,5 % genau: erlaubt
    assert S.stufe1("Viele kleine Teile", _probe(aus=aus, cost={0.9: 1006, 1.0: 1000}))[0] is False
    assert S.stufe1("Viele kleine Teile", _probe(aus={0.9: [_t("unknown")]}, cost={0.9: 1000, 1.0: 1000}))[0] is False


def test_stufe1_grenzfall_braucht_beides():
    assert S.stufe1("Grenzfall bei voller Auslastung", _probe(aus={0.9: [_t()]}, an={1.0: [_t(), _t("infeas")]}))[0] is True
    assert S.stufe1("Grenzfall bei voller Auslastung", _probe(aus={0.9: [_t("infeas")]}, an={1.0: [_t("infeas")]}))[0] is False
    assert S.stufe1("Grenzfall bei voller Auslastung", _probe(aus={0.9: [_t()]}, an={1.0: [_t("unknown")]}))[0] is False


def test_stufe1_reihenfolge_kostet_braucht_dieselbe_tour_in_beiden_stellungen():
    aus = {0.9: [_t("feas"), _t("infeas")]}
    assert S.stufe1("Reihenfolge kostet", _probe(aus=aus, an={0.9: [_t("feas", "infeas"), _t("infeas", "infeas")]}))[0] is True
    assert S.stufe1("Reihenfolge kostet", _probe(aus=aus, an={0.9: [_t("feas", "feas"), _t("infeas", "infeas")]}))[0] is False     # ohne die Tour, die in L fehlt
    assert S.stufe1("Reihenfolge kostet", _probe(aus=aus, an={0.9: [_t("feas", "unknown"), _t("infeas", "infeas")]}))[0] is False


def _rec(u, area, l=None):
    return {"U": {"cost": u}, "L": {"cost": l if l is not None else u}, "area_best": {"cost": area}}


def test_stufe2_schwellen_je_preset():
    assert S.stufe2("Wenige große Teile", _rec(1100, 1000), _rec(1030, 1000))[0] is True               # 10 % und 3 % genau
    assert S.stufe2("Wenige große Teile", _rec(1099, 1000), _rec(1030, 1000))[0] is False
    assert S.stufe2("Wenige große Teile", _rec(1100, 1000), _rec(1029, 1000))[0] is False
    assert S.stufe2("Viele kleine Teile", _rec(1020, 1000), _rec(1020, 1000))[0] is True
    assert S.stufe2("Viele kleine Teile", _rec(1021, 1000), _rec(1000, 1000))[0] is False
    assert S.stufe2("Reihenfolge kostet", _rec(1000, 900, 1010), _rec(1000, 900))[0] is True            # Δ_L ohne Drehung genau 1 %
    assert S.stufe2("Reihenfolge kostet", _rec(1000, 900, 1009), _rec(1000, 900))[0] is False
    assert S.stufe2("Standard", _rec(1000, 900), _rec(1000, 900))[0] is True and S.stufe2("Grenzfall bei voller Auslastung", _rec(1000, 900), _rec(1000, 900))[0] is True


# ------------------------------------------------------------------------------------------------ Geschichten: Neuberechnung und gespeicherte Suche

def _probe_live(name):
    p = K.PRESETS[name]
    inst = C.make_instance(p["n"], p["depot"], p["seed"], p["k"], p["phi"], p["spread"])
    pk_aus, pk_an = C.Packer(inst, False), C.Packer(inst, True)
    probe = {"aus": {}, "an": {}, "cost": {}}
    for th in S.THETAS_NEEDED[name]:
        ra = C.solve_area(inst, th)
        probe["cost"][th] = C.stats(inst, ra, C.F_FIX)[2]
        probe["aus"][th] = [C.tour_info(inst, pk_aus, r) for r in ra]
        probe["an"][th] = [C.tour_info(inst, pk_an, r) for r in ra]
    return probe


@pytest.mark.parametrize("name", list(K.PRESETS))
def test_jedes_preset_zeigt_seine_geschichte_bei_neuberechnung(name):
    ok, text = S.stufe1(name, _probe_live(name))
    assert ok, text


@pytest.mark.parametrize("name", list(K.PRESETS))
def test_jedes_preset_erfuellt_die_kriterien_mit_suche_auf_der_gespeicherten_loesung(name):
    p = K.PRESETS[name]
    recs = [R.stored_record(rot, p["depot"], p["n"], p["k"], p["spread"], p["phi"], p["seed"]) for rot in (False, True)]
    assert all(r is not None for r in recs)
    ok, text = S.stufe2(name, recs[0], recs[1])
    assert ok, text
    assert recs[0]["verify"] == {"U": [], "L": []} and recs[1]["verify"] == {"U": [], "L": []}      # der unabhängige Prüfer findet keinen Fehler


def test_die_zufalls_seeds_sind_die_in_preset_sweep_dokumentierten():
    """Je Preset der kleinste Kandidat ab 740000, der Stufe 1 und Stufe 2 erfüllt (Suche: tools/find_preset_seeds.py, Bericht tools/PRESET_SWEEP.md)."""
    erste = {"Standard": 740000, "Wenige große Teile": 740000, "Viele kleine Teile": 740003, "Grenzfall bei voller Auslastung": 740003, "Reihenfolge kostet": 740005}
    assert {nm: p["seed"] for nm, p in K.PRESETS.items()} == erste
