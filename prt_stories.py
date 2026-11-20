"""Abnahmekriterien der Presets: was die Instanz eines Presets zeigen muss (festgelegt vor der Suche der Zufalls-Seeds).

Stufe 1 (nur Fläche und Status der Touren, schnell): `probe` = {"aus": {θ: [tour_info]}, "an": {θ: [tour_info]}, "cost": {θ: Kosten der Flächenlösung}}.
  Die Flächenlösung hängt nicht von der Drehung ab; „alle Touren packbar“ wird in der strengeren Stellung geprüft (ohne Drehung; was ohne Drehung packbar
  ist, ist mit Drehung packbar), „mindestens eine Tour nachweislich nicht packbar“ in der Stellung mit Drehung (was mit Drehung nicht packbar ist, ist es
  ohne Drehung erst recht). So gilt jedes Preset in beiden Stellungen des Schalters „Rechtecke drehen“.
Stufe 2 (mit Suche): `rec` = run_record(..., search=True) je Stellung.
Die Kriterien der Stufe 1 sind die aus dem Nachtrag zu Teil 1 der Messreihe „Drehung“ (messreihe_packrouten_drehung/ERGEBNIS.md), mit den zwei Änderungen beim Bau
(tools/PRESET_SWEEP.md); die der Stufe 2 gehören zur Abstimmung der Presets (Plan Abschnitt 14, AP 5)."""

THETAS_NEEDED = {
    "Standard": (0.9,),
    "Wenige große Teile": (0.9, 0.8),
    "Viele kleine Teile": (0.9, 1.0),
    "Grenzfall bei voller Auslastung": (0.9, 1.0),
    "Reihenfolge kostet": (0.9,),
}


def n_status(infos, key, value):
    return sum(1 for t in infos if t[key] == value)


def all_packable(infos, key="u"):
    return all(t[key] == "feas" for t in infos)


def stufe1(name, probe):
    """(erfüllt?, Text) für Stufe 1."""
    aus, an, cost = probe["aus"], probe["an"], probe["cost"]
    if name == "Standard":
        ok = all_packable(aus[0.9])
        return ok, f"θ = 0,9: {len(aus[0.9])} Touren, alle ohne Drehung packbar: {ok}"
    if name == "Wenige große Teile":
        a, b = n_status(an[0.9], "u", "infeas"), n_status(an[0.8], "u", "infeas")
        return a >= 1 and b >= 1, f"nachweislich nicht packbare Touren (mit Drehung): bei θ = 0,9 {a}, bei θ = 0,8 {b}"
    if name == "Viele kleine Teile":
        ok1 = all_packable(aus[0.9])
        ratio = cost[0.9] / cost[1.0]
        return ok1 and ratio <= 1.005, f"θ = 0,9 alle packbar: {ok1}; Kosten bei θ = 0,9 gegen θ = 1,0: {ratio:.4f}"
    if name == "Grenzfall bei voller Auslastung":
        ok1 = all_packable(aus[0.9])
        b = n_status(an[1.0], "u", "infeas")
        return ok1 and b >= 1, f"θ = 0,9 alle packbar (ohne Drehung): {ok1}; bei θ = 1,0 nachweislich nicht packbar (mit Drehung): {b}"
    if name == "Reihenfolge kostet":
        cnt = sum(1 for tu, tl in zip(aus[0.9], an[0.9]) if tu["u"] == "feas" and tl["l"] == "infeas")
        return cnt >= 1, f"θ = 0,9: Touren, die ohne Reihenfolge packbar (ohne Drehung) und mit Entladereihenfolge nachweislich nicht packbar sind (mit Drehung): {cnt}"
    raise KeyError(name)


def delta_u(rec):
    return (rec["U"]["cost"] - rec["area_best"]["cost"]) / rec["area_best"]["cost"] * 100.0


def delta_l(rec):
    return (rec["L"]["cost"] - rec["U"]["cost"]) / rec["U"]["cost"] * 100.0


def stufe2(name, rec_aus, rec_an):
    """(erfüllt?, Text) für Stufe 2 (Suche beider Stellungen)."""
    du_a, du_n = delta_u(rec_aus), delta_u(rec_an)
    dl_a = delta_l(rec_aus)
    txt = f"Δ_U ohne/mit Drehung {du_a:.1f} % / {du_n:.1f} %, Δ_L ohne Drehung {dl_a:.1f} %"
    if name == "Wenige große Teile":
        return du_a >= 10.0 and du_n >= 3.0, txt + " (verlangt: ≥ 10 % und ≥ 3 %)"
    if name == "Viele kleine Teile":
        return du_a <= 2.0 and du_n <= 2.0, txt + " (verlangt: beide ≤ 2 %)"
    if name == "Reihenfolge kostet":
        return dl_a >= 1.0, txt + " (verlangt: Δ_L ohne Drehung ≥ 1 %)"
    return True, txt + " (kein Kriterium mit Suche)"
