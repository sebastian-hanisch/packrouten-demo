"""Packen und Routen: reicht die Fläche als Kapazität? - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Wann genügt es, die Fläche der Teile zu addieren, und was kostet es, wenn die Teile wirklich in die Ladefläche passen müssen (vereinfachte 2L-CVRP, mit und ohne
Drehung der Rechtecke)? Eine Instanz live, die Aussagen aus vorgerechneten Messreihen (data/prt_results.json).

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import modul_frisch
import prt_constants as K
import prt_evaluation as E
import prt_layout as LAY
import prt_live as L
import prt_pack as P
import prt_pdf_export as PDF
import prt_presets as PR
import prt_results as R
import prt_texts as T
import prt_visualization as V

modul_frisch.aktualisieren(__file__)      # geänderte Hilfsmodule nach einem Update neu laden (die Cloud behält sie sonst bis zum Neustart)

st.set_page_config(page_title="Packen und Routen – Sebastian Hanisch", layout="wide")

RES = R.load()
DEPOT_LABEL = {"rand": "Rand", "mitte": "Mitte"}
LIVE_NOTE = "Die Rechenzeit ist lokal gemessen (Wanduhr, unter Last), auf Streamlit Cloud nicht."


def _res(label, value):
    return f"{label}: {value}"


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in prt_layout.py).
st.html(LAY.kopf_css(LAY.dunkles_design()))
with st.container(key="kopf"):
    st.title("📦 Packen und Routen: reicht die Fläche als Kapazität?")
KG_A, KG_N = R.kipp_gruppen(False), R.kipp_gruppen(True)
BER_A, BER_N = R.kipp_bereich(False, 20, 5), R.kipp_bereich(True, 20, 5)
st.markdown(
    f"""
Ein Fahrzeug fasst nicht „Mengen“, sondern **Teile mit Maßen**. Wann genügt es, die **Fläche** der Teile zu addieren, und was kostet es, wenn sie **wirklich nebeneinander in die Ladefläche passen** müssen?
Die Demo zeigt an einer Instanz und an vorgerechneten Messreihen: **Ohne Drehung** gibt es in {KG_A[0]} von {KG_A[1]} Gruppen (Depot × Kunden × Ladungen × Form) eine **Auslastungsgrenze θ**, ab der bei mindestens der Hälfte der Instanzen eine Tour nachweislich nicht packbar ist, bei 20 Kunden und 5 Ladungen schon ab {E.theta_text(BER_A[0])} bis {E.theta_text(BER_A[1])}. Mit **Drehung** der Rechtecke um 90° gibt es sie nur in {KG_N[0]} von {KG_N[1]} Gruppen (bei 20 Kunden und 5 Ladungen ab {E.theta_text(BER_N[0])} bis {E.theta_text(BER_N[1])}): die Drehung entschärft das Problem, löst es nicht.
Es ist eine **vereinfachte Fassung** (feste Ladefläche, Zufallsinstanzen, keine Praxisdaten).

Weiter unten: die **Kernfragen** („Reicht die Fläche?“, „Was kostet das Packen?“, „Reparatur oder Suche?“) und die Expander **🔧 Wie wir das erreichen**, **Wie funktioniert diese Demo?** und **📐 Mathematische Formulierung**.
"""
)

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

PR.load_permalink_settings()
PR.init_session_state_defaults()

with st.sidebar:
    PR.sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Instanz**")
    n = st.radio("Kunden n", K.N_CHOICES, key="n_radio", horizontal=True, help="Instanzgröße. Bei 40 Kunden rechnet die App die Flächenlösung und den Status der Touren live (lokal gemessen bis etwa 12 Sekunden), Reparatur und Faustregel nur auf Knopfdruck (lokal gemessen bis etwa 27 Sekunden); auf Streamlit Cloud sind die Zeiten nicht gemessen. Die Suche ist nur für die Instanzen der Messreihe und die Presets gespeichert.")
    k = st.radio("Ladungen k", K.K_CHOICES, key="k_radio", horizontal=True, help="Wie viele Ladeflächen die Teile zusammen belegen könnten: ihre Gesamtfläche ist φ · k Ladeflächen (φ siehe unten); mit n bestimmt k die Zahl der Teile je Fahrzeug (1,8 · n / k im Erwartungswert).")
    spread = st.radio("Form der Teile", K.SPREAD_CHOICES, key="spread_radio", horizontal=True,
                      help="gleich: ähnlich große, ungefähr quadratische Teile; gemischt: sehr verschieden große Teile.")
    phi = st.radio("Gesamtfläche der Teile", K.PHI_CHOICES, key="phi_radio", horizontal=True, format_func=lambda x: E.fshare(x),
                   help="Anteil der Ladefläche aller k Fahrzeuge, den die Teile zusammen belegen: wie voll die Flotte im Mittel ist.")
    depot = st.radio("Depot", K.DEPOT_CHOICES, key="depot_radio", horizontal=True, format_func=lambda x: DEPOT_LABEL[x],
                     help="Lage des Depots im 100 × 100-Gebiet. In der Messreihe trennt es die Zellen nicht.")
    st.markdown("**Packen**")
    theta_pct = st.slider("Auslastungsgrenze θ (% der Ladefläche)", min(K.THETA_PCT_CHOICES), max(K.THETA_PCT_CHOICES), key="theta_slider", step=10, format="%d %%",
                          help="Die Flächenlösung belegt je Tour höchstens θ der Ladefläche (θ = Prozent / 100). 100 % ist die volle Fläche (klassisches CVRP mit der Fläche als Kapazität).")
    theta = theta_pct / 100.0
    rot = st.toggle("Rechtecke drehen (90°)", key="rot_toggle",
                    help="Aus: jedes Rechteck liegt, wie es ist. An: jedes Rechteck darf einzeln um 90° gedreht werden. Wirkt auf die Packbarkeit, die Zellenmeldung und die Zeichnung.")
    st.markdown("**Zufalls-Seed**")
    seed = st.number_input("Zufalls-Seed der Instanz", 0, K.SEED_MAX, key="seed_input", step=1,
                           help="Bestimmt die Instanz. Ohne Drehung sind die Zufalls-Seeds 610000 bis 610005 die Instanzen der Messreihe (Suche gespeichert), mit Drehung nur 610000 bis 610002.")
    st.button("🎲 Neue Instanz generieren", width="stretch", on_click=PR.new_seed)

PR.sync_query_params({"n_radio": int(n), "k_radio": int(k), "spread_radio": spread, "phi_radio": float(phi), "depot_radio": depot, "theta_slider": int(theta_pct),
                   "rot_toggle": bool(rot), "seed_input": int(seed)})
settings = L.Settings(int(n), int(k), spread, float(phi), depot, float(theta), bool(rot), int(seed))
S = settings
est = "lokal gemessen bis etwa 12 Sekunden" if S.n >= 40 else "wenige Sekunden"

# --- Eine Instanz --------------------------------------------------------------------------------------------------------------------------

st.markdown("## 📦 Eine Instanz")
st.info("**Eine Instanz belegt nichts:** sie streut. Die Meldungen der Kernfragen stützen sich auf vorgerechnete Zellen der Messreihen (12 Instanzen je Zelle in der Frage „Reicht die Fläche?“, 3 bis 6 in der Frage „Was kostet das Packen?“).", icon="ℹ️")
with st.spinner(f"Rechne die Flächenlösung bei θ = {E.theta_text(S.theta)} und prüfe die Touren ({est}) …"):
    view = L.area_view(S.n, S.depot, S.seed, S.k, S.phi, S.spread, S.rot, S.theta)
infos = view["tours"]
cu = E.count_status(infos, "u")
m_a, m_b = st.columns(2)
m_a.metric("Fahrzeuge (Touren)", view["V"], delta=f"Ladefläche je Fahrzeug {K.W} × {K.LEN}", delta_color="off")
m_b.metric("Distanz (Längeneinheiten)", E.fz(view["D"], 1), delta=f"Füllgrad der Flotte {E.fshare(view['fill'])}", delta_color="off")
m_c, m_d = st.columns(2)
m_c.metric("Kosten (Länge + 250 je Tour)", view["cost"], delta="Entfernungseinheiten", delta_color="off")
m_d.metric("Nicht packbare Touren", f"{cu['infeas']} von {view['V']}", delta=f"{cu['feas']} packbar, {cu['unknown']} unbekannt", delta_color="off")

m1c = R.m1_cell(S.rot, S.depot, S.n, S.k, S.spread, S.theta)
kind, text = E.verdict_instanz(infos, infos, S.theta, S.rot, view["with_l"])
getattr(st, kind)(text)

col_map, col_tab = st.columns([1, 1])
with col_map:
    st.plotly_chart(V.fig_routes(view["xy"], infos, f"Flächenlösung bei θ = {E.theta_text(S.theta)}"), width="stretch", key="main_routes")
with col_tab:
    rows = []
    for i, t in enumerate(infos):
        rows.append({"Tour": i + 1, "Kunden": len(t["route"]), "Teile": t["parts"], "Füllgrad": E.fshare(t["fill"]), "ohne Reihenfolge": V.STATUS_TEXT[t["u"]], "mit Reihenfolge": V.STATUS_TEXT[t["l"]]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("Status je Tour: packbar, nachweislich nicht packbar oder unbekannt (CP-SAT in der Zeitgrenze weder gepackt noch widerlegt). Mit Reihenfolge wird nur geprüft, wenn die Tour ohne Reihenfolge packbar ist"
               + ("." if view["with_l"] else ", und bei 40 Kunden live gar nicht (Rechenzeit).")
               + f" Die Prüfung läuft live mit {E.fz(view['det'], 1)} deterministischer CP-SAT-Zeit je Tour (die Messreihen: 0,3 ohne und 1,0 mit Drehung)"
               + ("; bei 40 Kunden mit Drehung bleiben deshalb mehr Touren „unbekannt“ als in der Messreihe." if (S.n > K.LIVE_SEARCH_MAX_N and S.rot) else "."))

st.markdown("**Ladeflächen der Touren** (Länge in x, Tür rechts; Farbe je Kunde, gedrehte Rechtecke mit ↻; bei nicht packbaren Touren eine einfache Teil-Packung, keine bestmögliche)")
grid = st.columns(2)
for i, t in enumerate(infos):
    with grid[i % 2]:
        st.plotly_chart(V.fig_loading(t, "u", i + 1), width="stretch", key=f"load_{i}")
        st.caption(E.tour_caption(t))
pdf_slot = st.container()      # der PDF-Knopf steht direkt unter der Hauptansicht; er wird unten gefüllt, wenn die Suche (gespeichert oder live) bekannt ist


# --- Datensatz mit Suche (gespeichert oder live) -------------------------------------------------------------------------------------------

def get_record(s):
    """(Datensatz, Quelle): gespeicherte Suche der Messreihe oder des Presets, sonst live (ohne oder mit kleiner Live-Suche)."""
    stored = R.stored_record(s.rot, s.depot, s.n, s.k, s.spread, s.phi, s.seed)
    if stored is not None:
        if s.seed in K.MESSREIHE_SEEDS:
            return stored, "Instanz der Messreihe (Frage 2): die Suche ist gespeichert (400 Iterationen)"
        return stored, "Preset-Instanz: die Suche ist gespeichert (400 Iterationen, wie in der Messreihe)"
    key = (s.n, s.depot, s.seed, s.k, s.phi, s.spread, s.rot)
    if st.session_state.get("live_search_for") == key:
        return L.as_record(L.search_record(*key)), "live gerechnet mit kleinem Budget (100 Iterationen, CP-SAT-Zeit 2): kann schlechter oder besser sein als die gespeicherte Suche"
    return None, ""


rec, source = get_record(S)
base = None
base_key = (S.n, S.depot, S.seed, S.k, S.phi, S.spread, S.rot)
if rec is None and (S.n <= K.LIVE_SEARCH_MAX_N or st.session_state.get("base_for") == base_key):
    with st.spinner("Rechne Fläche, Faustregel und Reparatur dieser Instanz (bei 40 Kunden lokal gemessen bis etwa 27 Sekunden) …" if S.n > 20 else "Rechne Fläche, Faustregel und Reparatur dieser Instanz (wenige Sekunden) …"):
        base = L.base_record(*base_key)
m2c = R.m2_cell(S.rot, S.depot, S.n, S.k, S.spread, S.phi)

st.markdown("---")

# --- Kernfrage 1 ---------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage 1: Reicht die Fläche als Kapazität?")
kind, text = E.verdict_flaeche(m1c, S.theta, S.rot, S.phi)
getattr(st, kind)(text)
hint = E.zelle_phi_hinweis(S.phi)
if hint:
    st.caption(hint)
cells_a, cells_b = RES["aus"]["m1"]["zellen"], RES["an"]["m1"]["zellen"]
na, oa, da = R.count_classes(cells_a)
nb, ob, db = R.count_classes(cells_b)
c1, c2 = st.columns(2)
c1.metric("Zellen „Fläche reicht oft nicht“ ohne Drehung", f"{oa} von {len(cells_a)}", delta=f"{na} „reicht“, {da} dazwischen", delta_color="off")
c2.metric("Zellen „Fläche reicht oft nicht“ mit Drehung", f"{ob} von {len(cells_b)}", delta=f"{nb} „reicht“, {db} dazwischen", delta_color="off")
st.caption(f"„Reicht oft nicht“ heißt: in mindestens der Hälfte der Instanzen eine nachweislich nicht packbare Tour. Mit Drehung ist der Nachweis schwerer (mehr Touren bleiben „unbekannt“), die Zahl ist dort eine Untergrenze: "
           f"zählt man „unbekannt“ als Problem mit, sind es ohne Drehung {R.count_unsicher(cells_a)} und mit Drehung {R.count_unsicher(cells_b)} von {len(cells_a)} Zellen.")
col_a, col_b = st.columns(2)
with col_a:
    st.plotly_chart(V.fig_zellenkarte(RES[R.state(S.rot)]["m1"]["zellen"], S.rot), width="stretch", key="zellenkarte")
with col_b:
    fills = {(False, "gleich"): R.fill_share(False, "gleich"), (False, "gemischt"): R.fill_share(False, "gemischt"),
             (True, "gleich"): R.fill_share(True, "gleich"), (True, "gemischt"): R.fill_share(True, "gemischt")}
    st.plotly_chart(V.fig_fuellgrad(fills), width="stretch", key="fuellgrad")
kp = R.kipp(S.rot, S.depot, S.n, S.k, S.spread)
st.caption(f"Zelle dieser Einstellung ({E.rot_text(S.rot)}, Depot {DEPOT_LABEL[S.depot]}, {S.n} Kunden, {S.k} Ladungen, Form {S.spread}): "
           + (f"„Fläche reicht oft nicht“ ab θ = {E.theta_text(kp)}." if kp is not None else "im Raster nie „Fläche reicht oft nicht“ (bei θ = 1,00 teils nur „unbekannt“).")
           + f" Erwartete Teile je Fahrzeug 1,8 · n / k = {E.fz(R.teile_je_fahrzeug(S.n, S.k), 1)} (Erwartungswert, keine Messgröße je Lösung).")
b1 = RES["aus"]["m1"]["m1b"]
b2 = RES["an"]["m1"]["m1b"]
st.markdown(
    f"**Deutung (aus Zählungen, nicht gesondert gemessen):** Teile, die breiter als die halbe Ladefläche sind, können nicht nebeneinander stehen; das trifft die Form „gleich“ bei 20 Kunden mit 5 Ladungen (69 % der Rechtecke bei φ = 0,90), bei 40 Kunden gar nicht. "
    f"Ob die Form bei 40 Kunden einen anderen Grund hat, ist nicht geklärt. "
    f"Bei gleichem Füllgrad (Touren ab 0,85, Status bekannt) sind ohne Drehung {E.fshare(b1['gleich']['infeas'] / b1['gleich']['N'])} der Touren der Form „gleich“ nachweislich nicht packbar "
    f"({b1['gleich']['N']} Touren), bei „gemischt“ {E.fshare(b1['gemischt']['infeas'] / b1['gemischt']['N'])} ({b1['gemischt']['N']} Touren), "
    f"bei höchstens 10 Teilen je Tour {E.fshare(b1['teile_le10']['infeas'] / b1['teile_le10']['N'])} ({b1['teile_le10']['N']} Touren), bei mindestens 11 {E.fshare(b1['teile_ge11']['infeas'] / b1['teile_ge11']['N'])} ({b1['teile_ge11']['N']} Touren); "
    f"mit Drehung {E.fshare(b2['gleich']['infeas'] / b2['gleich']['N'])} und {E.fshare(b2['gemischt']['infeas'] / b2['gemischt']['N'])}."
)

# --- Kernfrage 2 ---------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage 2: Was kostet das Packen?")
kind, text = E.verdict_packen(m2c, S.rot)
getattr(st, kind)(text)
if rec is not None and "U" in rec:
    cost_flaeche, cost_u, cost_l = rec["area_best"]["cost"], rec["U"]["cost"], rec["L"]["cost"]
    d1, d2, d3 = st.columns(3)
    d1.metric("Fläche (θ = 1,00)", cost_flaeche, delta=f"{rec['area_best']['V']} Fahrzeuge", delta_color="off")
    d2.metric("Suche ohne Reihenfolge (U)", cost_u, delta=f"{E.fpct(E.price_packing(rec))} gegen die Fläche", delta_color="inverse")
    d3.metric("Suche mit Entladereihenfolge (L)", cost_l, delta=f"{E.fpct(E.price_order(rec))} gegen U", delta_color="inverse")
    kind, text = E.verdict_suche(rec)
    getattr(st, kind)(text)
    st.caption(f"Quelle der Suche: {source}.")
else:
    if S.n <= K.LIVE_SEARCH_MAX_N:
        st.caption(f"Für diese Instanz ist keine Suche gespeichert. Sie lässt sich live rechnen (kleines Budget; {K.LIVE_SUCHE_ZEIT}); die Kosten der Suche sind Obergrenzen der Kosten der besten packbaren Lösung, weil „unbekannt“ als nicht packbar zählt.")
        if st.button("🔎 Suche live rechnen (n ≤ 20)", key="live_search_btn"):
            st.session_state["live_search_for"] = (S.n, S.depot, S.seed, S.k, S.phi, S.spread, S.rot)
            with st.spinner(f"Suche rechnet (kleines Budget; {K.LIVE_SUCHE_ZEIT}) …"):
                L.search_record(S.n, S.depot, S.seed, S.k, S.phi, S.spread, S.rot)
            st.rerun()
    else:
        st.caption("Bei 40 Kunden rechnet die App keine Suche live: sie dauert in der Messreihe Minuten. Gespeichert ist die Suche ohne Drehung für die Zufalls-Seeds 610000 bis 610005 (Instanzen der Messreihe), mit Drehung für 610000 bis 610002, und für das Preset mit 40 Kunden („Viele kleine Teile“). "
                   "Die Aussage steht deshalb auf der Zelle der Messreihe.")
gr_by = {}
g_aus = RES["aus"]["m2_gruppen_96"]
g_an = RES["an"]["m2_gruppen"]
for form in K.SPREAD_CHOICES:
    gr_by[(False, form)] = g_aus
    gr_by[(True, form)] = g_an
st.plotly_chart(V.fig_preis_nach_teilen(gr_by), width="stretch", key="preis_teile")
mm = RES["aus"]["m2_96"]
mn = RES["an"]["m2"]
st.caption(f"Mittel je Balken über Depots, Gesamtflächen und je drei Instanzen. Über alle {mn['N']} Instanzen: mittlerer Preis des Packens ohne Drehung {E.fpct(mm['dU_mean'])} (Median {E.fpct(mm['dU_median'])}), "
           f"mit Drehung {E.fpct(mn['dU_mean'])} (Median {E.fpct(mn['dU_median'])}); Basis ist die Flächenlösung bei θ = 1,00, die selbst nicht packbar ist. "
           "Die Kosten der Suche sind Obergrenzen der Kosten der besten packbaren Lösung („unbekannt“ zählt als nicht packbar); ein Preis ist der Quotient zweier Näherungen und kein garantierter Höchstwert (Reiter „Messreihe“: Wie stark hängen die Kosten am Budget und am Start der Suche?).")

# --- Kernfrage 3 ---------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage 3: Reparatur oder Suche?")
kind, text = E.verdict_reparatur(m2c, S.rot)
getattr(st, kind)(text)
data = rec if rec is not None else (base if base is not None else None)
if data is None:
    st.caption("Bei 40 Kunden rechnet die App Reparatur und Faustregel nur auf Knopfdruck (bis etwa eine halbe Minute lokal; auf Streamlit Cloud nicht gemessen). " + LIVE_NOTE)
    if st.button("🧰 Reparatur und Faustregel dieser Instanz rechnen", key="base_btn"):
        st.session_state["base_for"] = base_key
        st.rerun()
if data is not None:
    steps = [("Fläche<br>θ = 1,00", data["area"]["cost"], data["area"]["V"], K.COLOR_GREY),
             ("Reparatur<br>roh", data["rep_U"]["cost"], data["rep_U"]["V"], K.COLOR_BAD),
             ("Reparatur mit<br>lokaler Suche", data["repls_U"]["cost"], data["repls_U"]["V"], K.COLOR_UNKNOWN)]
    rule_u = data["rule"]["U"]
    if rule_u:
        steps.append((f"Faustregel<br>θ = {E.theta_text(rule_u['theta'])}", rule_u["cost"], rule_u["V"], K.COLOR_LINE))
    if "U" in data:
        steps.append(("Suche<br>(U)", data["U"]["cost"], data["U"]["V"], K.COLOR_OK))
    st.plotly_chart(V.fig_billige_wege(steps), width="stretch", key="billige_wege")
    if "U" in data:
        gap_rows = [{"Verfahren": nm.replace("<br>", " "), "Kosten": c, "Fahrzeuge": v, "Lücke zur Suche": E.fpct(E.gap_to_search(c, data, "U"))} for (nm, c, v, _) in steps if nm != "Suche<br>(U)"]
        st.dataframe(pd.DataFrame(gap_rows), hide_index=True, width="stretch")
        ra_, rn_ = RES["aus"]["m2"], RES["an"]["m2"]
        st.caption("Lücke = (Kosten des Verfahrens − Kosten der Suche) / Kosten der Suche. Die Suche startet aus der Reparatur: die Lücke der beiden Reparatur-Zeilen ist deshalb nie negativ und zeigt, was die Suche über die Reparatur hinaus findet. "
                   "Die Fläche (bewusst ohne Packbarkeit) liegt bauartbedingt unter der Suche U; die Faustregel kann unter der Suche liegen "
                   f"(in der Messreihe in {ra_['regel_U']['unter_suche']} von {ra_['regel_U']['N_mit_regel']} Instanzen ohne Drehung und {rn_['regel_U']['unter_suche']} von {rn_['regel_U']['N_mit_regel']} mit Drehung): die Suche ist nicht optimal. "
                   "Die Verfahren hatten nicht denselben Rechenaufwand, eine Rangfolge ist das nicht.")
    elif rule_u is None:
        st.caption("Bei dieser Instanz gibt es keine Faustregel: auch θ = 0,70 liefert eine nicht packbare Tour (oder „unbekannt“).")
mu, mnn = RES["aus"]["m2"], RES["an"]["m2"]
st.caption(
    f"Messreihe (U, ohne Drehung, {mu['N']} Instanzen): Reparatur mit lokaler Suche im Mittel {E.fpct(mu['rep_U']['ls_mean'])} über der Suche (roh {E.fpct(mu['rep_U']['roh_mean'])}), höchstens 1 % über der Suche in {mu['rep_U']['ls_le1']} Instanzen. "
    f"Faustregel θ = 0,90 reicht in {mu['regel_U']['verteilung'].get('0.9', 0)} Instanzen, keine Regel in {mu['regel_U']['verteilung'].get('keine', 0)}; Mehrkosten gegen die Suche im Mittel {E.fpct(mu['regel_U']['mehrkosten_mean'])} (nur Instanzen mit Regel). "
    f"Mit Drehung ({mnn['N']} Instanzen): {E.fpct(mnn['rep_U']['ls_mean'])} (roh {E.fpct(mnn['rep_U']['roh_mean'])}), höchstens 1 % in {mnn['rep_U']['ls_le1']}; keine Regel in {mnn['regel_U']['verteilung'].get('keine', 0)}. "
    f"Die beiden Zeilen haben verschiedene Instanzzahlen; auf denselben {RES['aus']['m2_96']['N']} Instanzen sind es ohne Drehung keine Regel in {RES['aus']['m2_96']['regel_U']['verteilung'].get('keine', 0)} (Reiter „Drehung“)."
)

# --- Zusatz: Entladereihenfolge ------------------------------------------------------------------------------------------------------------

with st.expander("➕ Zusatz: Welchen Preis hat die Entladereihenfolge?"):
    kind, text = E.verdict_reihenfolge(m2c, S.rot)
    getattr(st, kind)(text)
    ml = RES[R.state(S.rot)]["m2"]
    st.markdown(f"Über alle {ml['N']} Instanzen ({E.rot_text(S.rot)}): mittlerer Preis der Reihenfolge Δ_L = {E.fpct(ml['dL_mean'])} (Median {E.fpct(ml['dL_median'])}) gegen U. Das ist kleiner als der Preis des Packens, deshalb ein Zusatz und kein Aufhänger. "
                "Die Regel ist eine **vereinfachte Fassung** (siehe „Wie funktioniert diese Demo?“).")
    st.markdown("**Beispiel mit drei Kunden** (Breite × Länge: A 25 × 30, B 30 × 60, C 15 × 40, in der Reihenfolge A, B, C besucht): ohne Reihenfolge packbar, mit Reihenfolge in keiner der beiden Richtungen.")
    ex = [(0, 25, 30), (1, 30, 60), (2, 15, 40)]
    status, place, _ = P.exact_pack([(0, w, l) for _, w, l in ex], False, False, 2.0)
    if status == "feas":
        t_ex = {"u_place": place, "rect": [(w, l) for _, w, l in ex], "cust": [1, 2, 3], "u": "feas", "u_left": [], "fill": sum(w * l for _, w, l in ex) / K.AREA, "parts": 3}
        st.plotly_chart(V.fig_loading(t_ex, "u", 1), width="stretch", key="beispiel_l")
        st.caption("Die gezeichnete Packung (ohne Reihenfolge, Tür rechts): B liegt hinten, A und C liegen nebeneinander vor der Tür. Mit Entladereihenfolge blockiert dann C, das erst nach B beliefert wird, das Teil B. "
                   "Auch alle anderen Packungen scheitern, in beiden Richtungen der Tour (exakt geprüft).")

st.markdown("---")

# --- Expander ------------------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – Fläche, Reparatur, Suche, Faustregel"):
    tab_v, tab_z, tab_b, tab_d, tab_m = st.tabs(["📋 Verfahren", "🔎 Zellen", "🧰 Billige Wege", "🔄 Drehung", "📈 Messreihe"])
    with tab_v:
        st.dataframe(pd.DataFrame(T.METHODS_ROWS, columns=["Verfahren", "Was es tut", "Wo gemessen"]), hide_index=True, width="stretch")
        st.caption("Es gibt keinen Vergleich mit dem Routing von OR-Tools: es kennt keine Packbarkeit je Tour (CP-SAT von OR-Tools wird hier nur für die Packbarkeit je Tour benutzt). Reparatur und Suche haben nicht denselben Rechenaufwand; die Tabelle ist keine Rangfolge.")
    with tab_z:
        st.markdown(f"**„Fläche reicht oft nicht“ ab θ je Gruppe** ({E.rot_text(S.rot)}; kleinstes θ des Rasters, bei dem mindestens die Hälfte der 12 Instanzen eine nachweislich nicht packbare Tour hat; „nie“ = nie im Raster):")
        rows = []
        for form in K.SPREAD_CHOICES:
            for n_, k_ in ((20, 5), (20, 3), (40, 5), (40, 3)):
                row = {"Form": form, "(n, k)": f"{n_} / {k_}", "Teile je Fahrzeug": E.fz(R.teile_je_fahrzeug(n_, k_), 1)}
                for dep in ("mitte", "rand"):
                    v = R.kipp(S.rot, dep, n_, k_, form)
                    row[f"Depot {DEPOT_LABEL[dep]}"] = E.theta_text(v) if v is not None else "nie"
                rows.append(row)
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.markdown(f"**Preis des Packens je Gruppe** ({E.rot_text(S.rot)}, Mittel über Depots, Gesamtflächen und Instanzen):")
        gr = RES[R.state(S.rot)]["m2_gruppen"]
        st.dataframe(pd.DataFrame([{"Form": g["spread"], "(n, k)": f"{g['n']} / {g['k']}", "Teile je Fahrzeug": E.fz(g["teile_je_fahrzeug"], 1), "Instanzen": g["N"], "Δ_U im Mittel": E.fpct(g["dU"]),
                                    "Median": E.fpct(g["dU_median"]), "Δ_L im Mittel": E.fpct(g["dL"]), "keine Faustregel": f"{g['keine_regel_U']} von {g['N']}"} for g in gr]),
                     hide_index=True, width="stretch")
    with tab_b:
        st.markdown(f"**Reparatur gegen Suche über die 32 Zellen** ({E.rot_text(S.rot)}; U; Lücke zur Suche im Mittel je Zelle):")
        zz = RES[R.state(S.rot)]["m2_zellen"]
        st.dataframe(pd.DataFrame([{"Depot": DEPOT_LABEL[c["depot"]], "(n, k)": f"{c['n']} / {c['k']}", "Form": c["spread"], "φ": E.fz(c["phi"], 2), "Instanzen": c["N"],
                                    "Reparatur roh": E.fpct(c["rep0U"]), "mit lokaler Suche": E.fpct(c["repU"]), "Fahrzeuge mehr": E.fz(c["repUV"], 2),
                                    "Urteil": "genügt" if c["okU"] else ("genügt nicht" if c["badU"] else "dazwischen")} for c in zz]), hide_index=True, width="stretch")
        nok = sum(1 for c in zz if c["okU"])
        nbad = sum(1 for c in zz if c["badU"])
        st.caption(f"Urteile: „genügt“ in {nok} von {len(zz)} Zellen, „genügt nicht“ in {nbad}. Schwellen: genügt = höchstens 1 % über der Suche und höchstens 0,1 Fahrzeuge mehr; genügt nicht = mindestens 3 % oder mindestens 0,3 Fahrzeuge mehr (gesetzt, nicht hergeleitet).")
    with tab_d:
        st.markdown("**Dieselben Fragen ohne und mit Drehung** (Preis, Reparatur und Faustregel auf denselben 96 Instanzen, die Zellen der Frage 1 auf 192 Instanzen):")
        a96, an_, ba, bb = RES["aus"]["m2_96"], RES["an"]["m2"], RES["aus"]["m1"]["m1b"], RES["an"]["m1"]["m1b"]
        rows = [
            ("Zellen „Fläche reicht oft nicht“ (von 64; nachweislich nicht packbar)", str(oa), str(ob)),
            ("Zellen „reicht oft nicht“, wenn „unbekannt“ mitzählt (von 64)", str(R.count_unsicher(cells_a)), str(R.count_unsicher(cells_b))),
            ("Zellen „Fläche reicht“ (von 64)", str(na), str(nb)),
            ("Zellen mit spürbarem Preis des Packens (von 32)", str(sum(1 for c in RES["aus"]["m2_zellen_96"] if c["relU"])), str(sum(1 for c in RES["an"]["m2_zellen"] if c["relU"]))),
            ("Preis des Packens Δ_U, Mittel (Median)", f"{E.fpct(a96['dU_mean'])} ({E.fpct(a96['dU_median'])})", f"{E.fpct(an_['dU_mean'])} ({E.fpct(an_['dU_median'])})"),
            ("Preis der Reihenfolge Δ_L, Mittel (Median)", f"{E.fpct(a96['dL_mean'])} ({E.fpct(a96['dL_median'])})", f"{E.fpct(an_['dL_mean'])} ({E.fpct(an_['dL_median'])})"),
            ("Reparatur mit lokaler Suche gegen Suche (U), Mittel", E.fpct(a96["rep_U"]["ls_mean"]), E.fpct(an_["rep_U"]["ls_mean"])),
            ("Faustregel: keine Regel in … Instanzen", f"{a96['regel_U']['verteilung'].get('keine', 0)} von {a96['N']}", f"{an_['regel_U']['verteilung'].get('keine', 0)} von {an_['N']}"),
            ("Touren mit Status „unbekannt“ (Messreihe der Frage 1)", f"{ba['unbekannt']} von {ba['touren_gesamt']}", f"{bb['unbekannt']} von {bb['touren_gesamt']}"),
            ("CP-SAT-Aufrufe der Suche je Instanz, davon unbekannt", f"{E.fz(a96['exakt_je_instanz'], 0)}, {E.fz(a96['unbekannt_je_instanz'], 1)}", f"{E.fz(an_['exakt_je_instanz'], 0)}, {E.fz(an_['unbekannt_je_instanz'], 1)}"),
            ("Rechenzeit der Suche je Instanz, Mittel (Wanduhr, nicht unter gleicher Last gemessen)", f"{E.fz(a96['zeit_mittel_s'], 0)} s", f"{E.fz(an_['zeit_mittel_s'], 0)} s"),
        ]
        st.dataframe(pd.DataFrame(rows, columns=["", "ohne Drehung", "mit Drehung"]), hide_index=True, width="stretch")
        st.caption("Mit Drehung sind mehr Aufrufe „unbekannt“, und die Suche brauchte in der Messreihe länger (Wanduhr; beide Läufe liefen nicht unter gleicher Last, der Faktor ist ein Anhalt): die Kosten der Suche sind mit Drehung noch stärker Obergrenzen der Kosten der besten packbaren Lösung. "
                   "Die Drehung entschärft das Problem, löst es nicht.")
    with tab_m:
        mm6, mm6n = RES["aus"]["m6"], RES["an"]["m6"]
        st.markdown(f"**Kontrolle der Suche (n = 8, k = 2, φ = 0,85 und 0,95, {mm6['N']} Instanzen, exaktes Verfahren):** mittlere Lücke ohne Drehung {E.fpct(mm6['gap_mean'], 3)}, mit Drehung {E.fpct(mm6n['gap_mean'], 3)}; nie unter dem Optimum; "
                    f"die Flächenlösung liegt {E.fpct(-mm6['flaeche_gegen_orakel'])} (ohne Drehung) bzw. {E.fpct(-mm6n['flaeche_gegen_orakel'])} (mit Drehung) unter dem Optimum (Basis: das Optimum, nicht die Fläche). Gilt nur für n = 8.")
        rows = []
        for nm, key in (("ohne Reihenfolge (U)", "U"), ("mit Reihenfolge (L)", "L")):
            for st_ in ("aus", "an"):
                b = RES[st_]["m7"][key]
                hi_ = b["je_fuellgrad"][-1]
                rows.append({"Beladung": nm, "Stellung": "mit Drehung" if st_ == "an" else "ohne Drehung", "Touren mit exaktem Status": b["bekannt"], "Heuristik nein, exakt ja (von den Touren mit exaktem Status)": f"{b['heur_nein_exakt_ja']} ({E.fshare(b['heur_nein_exakt_ja'] / b['bekannt'], 1)})",
                             "bei Füllgrad ab 0,9 (Heuristik nein, exakt ja)": f"{hi_['gap']} von {hi_['bekannt']}", "unbekannt": b["unbekannt"]})
        st.markdown("**Heuristik gegen exakt** (40 Kunden, 3 Ladungen, φ = 0,90, Depot Mitte: 30 Instanzen mit je 12 Zufallstouren, Zielfüllgrad gleichverteilt von 0,55 bis 1,0; 360 Touren je Beladung):")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        k2 = RES["aus"]["k2"]
        ga, gb = RES["aus"]["a"], RES["an"]["a"]
        ko_a, ko_n = RES["kontrollen"]["aus"], RES["kontrollen"]["an"]
        va, vn, cba, cbn = ko_a["v_live_gegen_gespeichert"], ko_n["v_live_gegen_gespeichert"], ko_a["c_gegen_b"], ko_n["c_gegen_b"]
        st.markdown(f"**Wie stark hängen die Kosten der Suche, und damit die Preise, am Budget und am Start der Suche?** Bei 20 Kunden senkt ein größeres CP-SAT-Budget (Nachmessung, nicht vorab festgelegt, {k2['N']} Instanzen, ohne Drehung) die Kosten U im Mittel um {E.fpct(-k2['dU_mean'], 2)} "
                    f"(bei {k2['unveraendert']} Instanzen unverändert, bei {k2['mehr_als_05']} um mehr als 0,5 %, größte Verbesserung {E.fpct(k2['beste_verbesserung_U'], 2)}). "
                    f"Die Live-Suche (100 Iterationen, CP-SAT-Zeit 2,0, {va['N']} Instanzen) lag im Mittel {E.fpct(-va['mean'], 2)} unter der gespeicherten Suche mit 400 Iterationen (ohne Drehung; größte Einsparung {E.fpct(va['beste_einsparung'], 2)}), mit Drehung {E.fpct(-vn['mean'], 2)} (größte {E.fpct(vn['beste_einsparung'], 2)}). "
                    f"Bei 40 Kunden: eine Suche mit 2 000 statt 400 Iterationen, größerem CP-SAT-Budget und Start aus der kürzeren Suche ist im Mittel {E.fpct(ga['gap_mean'], 2)} billiger ({ga['N']} Instanzen ohne Drehung; {ga['gap_gt2']} über 2 %) bzw. {E.fpct(gb['gap_mean'], 2)} ({gb['N']} Instanzen mit Drehung; {gb['gap_gt2']} über 2 %); "
                    f"ein kalt gestarteter Lauf mit demselben Budget unterbot diese Suche in {cba['billiger']} von {cba['N']} Instanzen ohne Drehung (bis {E.fpct(cba['beste_einsparung'], 2)}) und in {cbn['billiger']} von {cbn['N']} mit Drehung (bis {E.fpct(cbn['beste_einsparung'], 2)}). "
                    "Eine Zahl wie „Δ_U = 8,9 %“ ist deshalb eine Größenordnung, kein garantierter Höchstwert.")
        st.markdown(f"**Robustheit:** Teile je Kunde (1 und 3 Rechtecke, Depot Rand, φ = 0,90, {ko_a['c1_n']} Instanzen, 12 Zellen je Form): Rangkorrelation zwischen erwarteten Teilen je Fahrzeug und Preis {E.fz(ko_a['c1_rho']['gleich'], 2)} (gleich) und {E.fz(ko_a['c1_rho']['gemischt'], 2)} (gemischt) ohne Drehung, "
                    f"{E.fz(ko_n['c1_rho']['gleich'], 2)} und {E.fz(ko_n['c1_rho']['gemischt'], 2)} mit Drehung: nur eine Rangfolge, kein Gesetz. Andere Ladeflächen (lang 25 × 160, kompakt 50 × 80 bei gleicher Fläche; Palettenfall: Rechtecke fest 19 × 28, Maße als Entwurfsannahme): in allen drei Layouts gibt es Zellen „reicht“ und „reicht oft nicht“. "
                    f"Das Kipp-θ weicht höchstens 0,10 von dem der Ladefläche 40 × 100 (Depot Rand, 12 Instanzen je Zelle; die anderen Layouts 6) ab in {ko_a['c2_nahe']['lang']} (lang) und {ko_a['c2_nahe']['kompakt']} (kompakt) von 8 Gruppen ohne Drehung, mit Drehung in {ko_n['c2_nahe']['lang']} und {ko_n['c2_nahe']['kompakt']} von 8; "
                    f"darunter sind ohne Drehung {ko_a['c2_nahe_beide_nie']['lang']} und {ko_a['c2_nahe_beide_nie']['kompakt']}, mit Drehung {ko_n['c2_nahe_beide_nie']['lang']} und {ko_n['c2_nahe_beide_nie']['kompakt']} Gruppen, in denen beide „nie im Raster“ haben. "
                    "Mit Drehung ist die Lage der Grenze bei langer Ladefläche damit nicht übertragbar; die Ladefläche ist deshalb kein Regler. **Plattform:** Windows und Linux liefern in "
                    f"{ko_n['e_identisch']} von {ko_n['e_zeilen']} Zeilen dieselben Kosten; der CP-SAT-Status ist in {E.fshare(ko_n['e_status_gleich'], 1)} der 480 Prüfungen gleich (mit Drehung), nie ein Wechsel zwischen packbar und nicht packbar.")
        st.markdown(f"**Rechenzeit** (lokal, Wanduhr, unter Last, mehrere Prozesse gleichzeitig; auf Streamlit Cloud nicht gemessen): Fläche mit Prüfung plus Reparatur bei 40 Kunden ({ko_n['d_n40']} Instanzen, Form gemischt, Depot Rand) im Mittel {E.fz(ko_n['d_t40_mean'], 1)} s (mit Drehung), größter Wert {E.fz(ko_n['d_t_max'], 1)} s; "
                    f"die vollständige Suche je Instanz im Mittel {E.fz(RES['aus']['m2']['zeit_mittel_s'], 0)} s ohne Drehung ({RES['aus']['m2']['N']} Instanzen) und {E.fz(RES['an']['m2']['zeit_mittel_s'], 0)} s mit Drehung ({RES['an']['m2']['N']} Instanzen); "
                    f"beide Läufe wurden nicht unter gleicher Last gemessen, der Faktor ist ein Anhalt. Live-Suche bei 20 Kunden (Knopf): {K.LIVE_SUCHE_ZEIT}.")

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown("**Was die Demo rechnet.** Aus Kunden mit Rechtecken (Teile mit Maßen) entsteht eine Instanz; die **Flächenlösung** plant Touren, als wären nur die Flächen eine Kapazität (bis zur Auslastungsgrenze θ). "
                "Dann prüft die App jede Tour: passen die Rechtecke wirklich in die Ladefläche (ohne oder mit Drehung, ohne oder mit Entladereihenfolge)? Nicht packbare Touren zeigt sie gezeichnet. "
                "Die **Reparatur** macht die Flächenlösung packbar; die **Suche** plant gleich mit der Packbarkeit als Bedingung; die **Faustregel** wählt das größte θ, bei dem die Flächenlösung schon packbar ist.")
    st.markdown("**🚧 Wo die Annahmen enden**")
    st.markdown(T.ASSUMPTIONS_MARKDOWN)
    st.markdown("**Nicht gemessen und nicht versprochen:** Praxiswerte, Optimalität bei 20 und 40 Kunden, andere Drehwinkel als 90°, 3D, Zeitfenster, Flottenmix, begrenzte Fahrzeugzahl, mehr als 40 Kunden, Zahlenvergleich mit der Literatur "
                "(die Literatur wurde nur als Zusammenfassung gelesen). Die Zellen der Messreihe haben 12 Instanzen (Frage 1) bzw. 3 bis 6 (Fragen 2 und 3): einzelne Abweichungen sind zu erwarten, und die Schwellen der Meldungen sind gesetzt, nicht hergeleitet.")
    st.markdown("**Verwandte Demos:** `vrp-demo` (Tourenplanung, Verfahrensvergleich, ohne Packen), `pack-demo` (3D-Packung), `fahrzeuggroesse-demo` (Fixkosten und Reserve: Kapazität als Zahl, nicht als Fläche).")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown("**Lesehilfe.** Gegeben sind Kunden mit Rechtecken, eine Ladefläche und Kosten je Tour; gesucht sind Touren, die jeden Kunden genau einmal besuchen und deren Rechtecke je Tour in die Ladefläche passen. Die Symbole:")
    st.markdown(T.SYMBOLS_MARKDOWN)
    for f in T.FORMULAS:
        st.latex(f)
    st.markdown(T.FORMULAS_NOTE)

with pdf_slot:
    st.download_button("📄 Tourenplan als PDF", data=PDF.build_pdf(settings, view, rec), file_name="tourenplan_packen.pdf", mime="application/pdf", key="pdf_download")
st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Tourenplanung optimieren](https://sebastianhanisch.net/tourenplanung-optimierung.html)."
)
