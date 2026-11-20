"""Neu-Rechnen als Band, nicht bitgleich (DEMO-PLAYBOOK §5): die Flächenlösung rechnet nur mit Ganzzahlen und ist plattformfest (exakt gleich); Reparatur und Faustregel hängen
am CP-SAT-Status der Touren, der zwischen Windows und Linux zwischen „packbar“ und „unbekannt“ wechseln kann (Messreihe (e): 3 von 480 Prüfungen mit Drehung)
und nie zwischen „packbar“ und „nicht packbar“. Daher: exakt für die Fläche, ein Band für den Rest, und ein eigener Test für den Statuswechsel."""

import pytest

import prt_constants as K
import prt_core as C
import prt_live as L
import prt_results as R


def _stored(rot, depot, n, k, spread, phi, seed):
    rec = R.stored_record(rot, depot, n, k, spread, phi, seed)
    assert rec is not None
    return rec


@pytest.mark.parametrize("rot", [False, True])
def test_messreihe_instanz_20_5_gleich_flaeche_exakt_reparatur_im_band(rot):
    rec = _stored(rot, "mitte", 20, 5, "gleich", 0.9, 610000)
    neu = L.base_record(20, "mitte", 610000, 5, 0.9, "gleich", rot)
    for key in ("area",):
        assert (neu[key]["V"], neu[key]["cost"]) == (rec[key]["V"], rec[key]["cost"])           # Fläche: nur Ganzzahlen, plattformfest
        assert neu[key]["D"] == pytest.approx(rec[key]["D"], abs=1e-9)
    for key in ("rep_U", "repls_U"):                                    # der Live-Teil rechnet nur U (modes=("U",))
        assert neu[key]["cost"] == pytest.approx(rec[key]["cost"], rel=0.03), key              # Band 3 %: Status „unbekannt“ kann andere Reparatur nach sich ziehen
    for mode in ("U",):
        a, b = neu["rule"][mode], rec["rule"][mode]
        assert (a is None and b is None) or (a is not None and b is not None and abs(a["theta"] - b["theta"]) <= 0.1 + 1e-9), mode     # Faustregel: höchstens eine Stufe Abstand


def test_preset_standard_neu_gerechnet_stimmt_mit_der_gespeicherten_loesung():
    p = K.PRESETS["Standard"]
    rec = _stored(False, p["depot"], p["n"], p["k"], p["spread"], p["phi"], p["seed"])
    neu = L.base_record(p["n"], p["depot"], p["seed"], p["k"], p["phi"], p["spread"], False)
    assert (neu["area"]["V"], neu["area"]["cost"]) == (rec["area"]["V"], rec["area"]["cost"])
    assert neu["repls_U"]["cost"] == pytest.approx(rec["repls_U"]["cost"], rel=0.03)


@pytest.mark.parametrize("rot", [False, True])
def test_status_wechselt_mit_mehr_zeit_nie_zwischen_packbar_und_nicht_packbar(rot):
    """Mehr deterministische Zeit darf „unbekannt“ in „packbar“ oder „nicht packbar“ verwandeln, aber nie ein entschiedenes Ergebnis ändern."""
    inst = C.make_instance(20, "mitte", 610001, 5, 0.9, "gleich")
    pk = C.Packer(inst, rot=rot)
    n_geprueft = 0
    for theta in (0.9, 1.0):
        for r in C.solve_area(inst, theta):
            for lifo in (False, True):
                kurz = pk.exact_status(r, lifo, 0.05)[0]
                lang = pk.exact_status(r, lifo, 3.0)[0]
                n_geprueft += 1
                if kurz in ("feas", "infeas"):
                    assert lang == kurz, (theta, r, lifo, kurz, lang)
    assert n_geprueft >= 10


def test_ergebnisdatei_ist_aus_den_rohdaten_reproduzierbar_ohne_die_rohdaten_zu_brauchen():
    """Die Datei enthält nur Aggregate; ihre Quelle steht in der Datei und in tools/dump_results.py (Rohdaten liegen nicht im Repo)."""
    assert "Messreihen" in R.load()["quelle"] and R.load()["version"] == 1
