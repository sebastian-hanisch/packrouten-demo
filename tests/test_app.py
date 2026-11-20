"""AppTest-Rauchtests: Standard, jedes Preset, jede Stufe jedes Reglers, die Drehung, Permalink, die Live-Suche, keine Ausnahme, Texte und Zahlen der Seite."""

import os
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import prt_constants as K
import prt_presets as P
import prt_results as R

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))      # unter Last (parallele Läufe) reichen 180 s nicht immer; Umgebungsvariable zum Anpassen


def _app(**query) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    for k, v in query.items():
        at.query_params[k] = str(v)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _texte(at):
    """Alle sichtbaren Texte der Seite (Markdown, Meldungen, Beschriftungen)."""
    out = [m.value for m in at.markdown] + [c.value for c in at.caption] + [e.value for e in at.info] + [e.value for e in at.warning] + [e.value for e in at.success]
    out += [m.label for m in at.metric] + [str(m.value) for m in at.metric] + [str(m.delta) for m in at.metric]
    return "\n".join(out)


def test_standard_laedt_ohne_ausnahme_und_zeigt_alle_abschnitte():
    at = _app()
    labels = [m.label for m in at.metric]
    assert labels[:4] == ["Fahrzeuge (Touren)", "Distanz (Längeneinheiten)", "Kosten (Länge + 250 je Tour)", "Nicht packbare Touren"]
    ueberschriften = [m.value for m in at.markdown if m.value.startswith("## ")]
    assert ueberschriften == ["## 📦 Eine Instanz", "## ❓ Kernfrage 1: Reicht die Fläche als Kapazität?", "## ❓ Kernfrage 2: Was kostet das Packen?", "## ❓ Kernfrage 3: Reparatur oder Suche?"]
    expander = [e.label for e in at.expander]
    assert "🔧 Wie wir das erreichen – Fläche, Reparatur, Suche, Faustregel" in expander and "Wie funktioniert diese Demo?" in expander and "📐 Mathematische Formulierung" in expander
    assert at.download_button[0].label == "📄 Tourenplan als PDF"


def test_standard_zeigt_die_vorgerechneten_zahlen_der_messreihe():
    text = _texte(_app())
    nie, oft, mid = R.count_classes(R.load()["aus"]["m1"]["zellen"])
    assert f"{oft} von 64" in text and f"{nie} „reicht“, {mid} dazwischen" in text
    nie2, oft2, _ = R.count_classes(R.load()["an"]["m1"]["zellen"])
    assert f"{oft2} von 64" in text
    assert "Quelle der Suche: Preset-Instanz: die Suche ist gespeichert" in text


@pytest.mark.parametrize("name", list(K.PRESETS))
def test_jedes_preset_laedt_ohne_ausnahme_und_zeigt_seine_einstellungen(name):
    at = _app()
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert not at.exception, [str(e) for e in at.exception]
    p = K.PRESETS[name]
    assert (at.sidebar.radio(key="n_radio").value, at.sidebar.radio(key="k_radio").value, at.sidebar.radio(key="spread_radio").value, at.sidebar.radio(key="depot_radio").value) == (p["n"], p["k"], p["spread"], p["depot"])
    assert at.sidebar.slider(key="theta_slider").value == round(100 * p["theta"]) and at.sidebar.number_input(key="seed_input").value == p["seed"]
    assert "Quelle der Suche: Preset-Instanz" in _texte(at)                  # die Suche des Presets ist gespeichert (beide Stellungen)


def test_drehung_an_laedt_ohne_ausnahme_und_aendert_die_meldung():
    at = _app()
    at.sidebar.toggle(key="rot_toggle").set_value(True).run()
    assert not at.exception, [str(e) for e in at.exception]
    text = _texte(at)
    assert "mit Drehung, θ = 0,90" in text and "(ohne Drehung, θ = 0,90" not in text


@pytest.mark.parametrize("key,werte", [("k_radio", K.K_CHOICES), ("spread_radio", K.SPREAD_CHOICES), ("phi_radio", K.PHI_CHOICES), ("depot_radio", K.DEPOT_CHOICES), ("theta_slider", K.THETA_PCT_CHOICES)])
def test_jede_stufe_jedes_reglers_laeuft_ohne_ausnahme(key, werte):
    at = _app()
    for w in werte:
        regler = at.sidebar.slider(key=key) if key == "theta_slider" else at.sidebar.radio(key=key)
        regler.set_value(w).run()
        assert not at.exception, (key, w, [str(e) for e in at.exception])


def test_40_kunden_laufen_ohne_ausnahme_und_bieten_keine_live_suche_an():
    at = _app(n=40, seed=7)
    assert at.sidebar.radio(key="n_radio").value == 40
    assert not [b for b in at.main.button if b.key == "live_search_btn"]
    assert [b for b in at.main.button if b.key == "base_btn"]                  # Reparatur und Faustregel bei 40 Kunden nur auf Knopfdruck
    text = _texte(at)
    assert "Bei 40 Kunden rechnet die App keine Suche live" in text and "nur auf Knopfdruck" in text and "bei 40 Kunden live nicht geprüft" in text


def test_die_live_suche_laeuft_bei_20_kunden_mit_kleinem_budget(monkeypatch):
    monkeypatch.setattr(K, "LIVE_SEARCH_ITERS", 5)                           # im Test nur wenige Iterationen (die App liest die Konstante beim Aufruf)
    at = _app(seed=7)
    knopf = [b for b in at.main.button if b.key == "live_search_btn"]
    assert len(knopf) == 1
    knopf[0].click().run()
    assert not at.exception, [str(e) for e in at.exception]
    text = _texte(at)
    assert "Suche ohne Reihenfolge (U)" in text and "Quelle der Suche: live gerechnet mit kleinem Budget" in text
    assert not [b for b in at.main.button if b.key == "live_search_btn"]


def test_permalink_rastet_ein_und_die_adresszeile_spiegelt_die_einstellungen():
    at = _app(n=33, k=5, form="gleich", phi=0.8, depot="rand", theta=0.93, drehen=1, seed=741)
    assert at.sidebar.radio(key="n_radio").value == 40 and at.sidebar.radio(key="k_radio").value == 5
    assert at.sidebar.radio(key="spread_radio").value == "gleich" and at.sidebar.radio(key="phi_radio").value == 0.75
    assert at.sidebar.radio(key="depot_radio").value == "rand" and at.sidebar.slider(key="theta_slider").value == 90
    assert at.sidebar.toggle(key="rot_toggle").value is True and at.sidebar.number_input(key="seed_input").value == 741
    assert at.query_params["n"] == "40" and at.query_params["drehen"] == "1" and at.query_params["theta"] == "90"


def test_ungueltige_permalink_werte_ergeben_die_voreinstellung():
    at = _app(form="quadrat", depot="ecke", seed="abc")
    assert at.sidebar.radio(key="spread_radio").value == K.DEFAULT_SPREAD and at.sidebar.radio(key="depot_radio").value == K.DEFAULT_DEPOT and at.sidebar.number_input(key="seed_input").value == K.DEFAULT_SEED


def test_neue_instanz_wuerfelt_einen_seed_ausserhalb_der_messreihen():
    at = _app()
    at.sidebar.button[-1].click().run()
    assert not at.exception, [str(e) for e in at.exception]
    s = at.sidebar.number_input(key="seed_input").value
    assert 0 <= s <= K.OWN_SEED_MAX


def test_keine_toten_dateilinks_und_keine_ascii_umlaute_in_den_texten():
    text = _texte(_app())
    assert not re.search(r"\]\((?!https?://)[^)]*\.(py|md|json)\)", text)
    assert not re.search(r"\b(ae|oe|ue)\b", text.replace("Zufalls-Seed", ""))            # grobe Prüfung auf ASCII-Umlaute als eigenes Wort
    assert "Saatwert" not in text


def test_expander_haengen_nicht_an_ihrer_position():
    at = _app()
    labels = {e.label for e in at.expander}
    assert {"➕ Zusatz: Welchen Preis hat die Entladereihenfolge?", "Wie funktioniert diese Demo?", "📐 Mathematische Formulierung"} <= labels
    formel = next(e for e in at.expander if e.label == "📐 Mathematische Formulierung")
    assert len(formel.latex) == 4 and any("Symbol" in m.value for m in formel.markdown)       # Lesehilfe mit Symboltabelle zuerst
    assert P.aktives_preset(at.session_state) == "Standard"
