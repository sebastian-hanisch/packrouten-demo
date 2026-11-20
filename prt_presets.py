"""Permalink (auf gemessene Stufen einrasten), Presets, Hervorhebung des aktiven Presets und Zufalls-Seed-Knopf."""

import random
from dataclasses import dataclass

import streamlit as st

import prt_constants as C


def _pct(value):
    """θ aus der Adresszeile: Prozent (90) oder Anteil (0,9) ergibt ganze Prozent."""
    x = float(value)
    return int(round(x * 100)) if x <= 1.5 else int(round(x))


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: object            # Typ oder Funktion, die den Wert aus der Adresszeile umrechnet
    default: object
    choices: tuple | None = None      # nur diese Stufen sind gemessen: Werte aus der Adresszeile rasten auf die nächste Stufe ein
    lo: int | None = None
    hi: int | None = None


SETTING_SPECS = {
    "n_radio": SettingSpec("n", int, C.DEFAULT_N, C.N_CHOICES),
    "k_radio": SettingSpec("k", int, C.DEFAULT_K, C.K_CHOICES),
    "spread_radio": SettingSpec("form", str, C.DEFAULT_SPREAD, C.SPREAD_CHOICES),
    "phi_radio": SettingSpec("phi", float, C.DEFAULT_PHI, C.PHI_CHOICES),
    "depot_radio": SettingSpec("depot", str, C.DEFAULT_DEPOT, C.DEPOT_CHOICES),
    "theta_slider": SettingSpec("theta", _pct, int(round(100 * C.DEFAULT_THETA)), C.THETA_PCT_CHOICES),
    "rot_toggle": SettingSpec("drehen", int, int(C.DEFAULT_ROT), (0, 1)),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, None, 0, C.SEED_MAX),
}
# Schlüssel eines Presets -> Regler. Die Drehung gehört nicht zum Szenario: ein Preset gilt in beiden Stellungen des Schalters.
PRESET_KEYS = {"n": "n_radio", "k": "k_radio", "spread": "spread_radio", "phi": "phi_radio", "depot": "depot_radio", "theta": "theta_slider", "seed": "seed_input"}
PRESET_IGNORE = ("rot_toggle",)


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = bool(spec.default) if state_key == "rot_toggle" else spec.default


def snap(spec, value):
    """Wert auf die Stufen (choices) einrasten bzw. auf [lo, hi] begrenzen; ungültige Eingaben ergeben None."""
    try:
        value = spec.caster(value)
    except (ValueError, TypeError):
        return None
    if spec.choices is not None:
        if spec.caster is str:
            return value if value in spec.choices else None
        return min(spec.choices, key=lambda c: abs(c - value))
    if spec.lo is not None:
        value = max(spec.lo, value)
    if spec.hi is not None:
        value = min(spec.hi, value)
    return value


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen, auf gemessene Stufen eingerastet."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            value = snap(spec, qp[spec.url_param])
            if value is None:
                continue
            st.session_state[state_key] = bool(value) if state_key == "rot_toggle" else value
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}; die Adresszeile spiegelt die Konfiguration."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(int(value)) if state_key == "rot_toggle" else str(value)
    except Exception:
        pass


def preset_value(preset, key):
    """Wert eines Presets im Regler (θ als ganze Prozent)."""
    v = preset[key]
    return int(round(100 * v)) if key == "theta" else v


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        if key in C.PRESETS[name]:
            st.session_state[state_key] = preset_value(C.PRESETS[name], key)


def aktives_preset(values=None):
    """Name des Presets, dessen Werte GENAU den aktuellen Einstellungen entsprechen, sonst None.

    Zustandslos: verglichen wird jeder Regler aus SETTING_SPECS außer der Drehung (ein Preset gilt in beiden Stellungen) mit dem Wert des Presets (fehlt er dort,
    gilt der Standardwert). Ein später ergänzter Regler braucht nur seinen Eintrag in SETTING_SPECS (tests/test_layout.py prüft das für jeden Regler)."""
    values = st.session_state if values is None else values
    preset_key_of = {state_key: key for key, state_key in PRESET_KEYS.items()}
    for name, preset in C.PRESETS.items():
        same = True
        for state_key, spec in SETTING_SPECS.items():
            if state_key in PRESET_IGNORE:
                continue
            pk = preset_key_of.get(state_key)
            wanted = preset_value(preset, pk) if pk in preset else spec.default
            if values.get(state_key, spec.default) != wanted:
                same = False
                break
        if same:
            return name
    return None


def sidebar_presets():
    """🎯 Schnellstart: erster Block der Seitenleiste; das aktive Preset ist hervorgehoben."""
    st.header("🎯 Schnellstart")
    st.caption("Ein Beispielszenario laden (Zelle der Messreihe und Instanz mit passender Geschichte):")
    active = aktives_preset()
    for name in C.PRESETS:
        st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}",
                  type="primary" if name == active else "secondary")


def new_seed():
    st.session_state["seed_input"] = random.randint(0, C.OWN_SEED_MAX)
