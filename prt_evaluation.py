"""Kennzahlen und Verdikte (reine Funktionen; die App ruft `getattr(st, art)(text)`).

Jedes Verdikt beruht auf der vorgerechneten Zelle der Messreihe (Mittel über 12 Instanzen je Zelle in M1, 3 bis 6 in M2), nie auf dem einen gezeigten Lauf.
Schwellen: prt_constants (M1_NIE, M1_OFT, M2_*, M3_*, M4_*)."""

from __future__ import annotations

import prt_constants as K


# ------------------------------------------------------------------------------------------------ Format

def fz(x, d=1):
    """Zahl mit Dezimalkomma."""
    return f"{x:.{d}f}".replace(".", ",")


def fpct(x, d=1):
    """Prozentzahl (Wert schon in Prozent) mit Dezimalkomma."""
    return f"{fz(x, d)} %"


def fshare(x, d=0):
    """Anteil 0 bis 1 als Prozent."""
    return fpct(x * 100.0, d)


def theta_text(theta):
    return fz(theta, 2)


def rot_text(rot):
    return "mit Drehung" if rot else "ohne Drehung"


# ------------------------------------------------------------------------------------------------ Kennzahlen einer Lösung

def rel(a, b):
    """(a − b) / b in Prozent; Nenner 0 gibt 0 zurück (keine Aussage)."""
    return (a - b) / b * 100.0 if b else 0.0


def price_packing(rec):
    """Preis des Packens Δ_U = (K_U − K_Fläche) / K_Fläche in Prozent (Fläche = beste gefundene Flächenlösung θ = 1,00)."""
    return rel(rec["U"]["cost"], rec["area_best"]["cost"])


def price_order(rec):
    """Preis der Entladereihenfolge Δ_L = (K_L − K_U) / K_U in Prozent."""
    return rel(rec["L"]["cost"], rec["U"]["cost"])


def gap_to_search(cost, rec, mode="U"):
    """Lücke einer billigen Lösung zur Suche in Prozent: (K − K_Suche) / K_Suche."""
    return rel(cost, rec[mode]["cost"])


def count_status(infos, key="u"):
    """Zählung der Tourstatus: {'feas': a, 'infeas': b, 'unknown': c}."""
    out = {"feas": 0, "infeas": 0, "unknown": 0}
    for t in infos:
        out[t[key]] += 1
    return out


# ------------------------------------------------------------------------------------------------ Zellen

def m1_class(cell):
    """'nie' | 'oft' | 'dazwischen' nach p_max (nie) und p_min (oft)."""
    if cell["pmax"] <= K.M1_NIE:
        return "nie"
    if cell["pmin"] >= K.M1_OFT:
        return "oft"
    return "dazwischen"


def verdict_flaeche(cell, theta, rot, phi=0.90):
    """Reicht die Fläche als Kapazität bei diesem θ? Aus der Zelle der Messreihe M1 (Depot × (n, k) × Form × θ; gemessen bei φ = 0,90)."""
    if cell is None:
        return "info", "Für diese Einstellung liegt keine Zelle der Messreihe vor."
    cls = m1_class(cell)
    kopf = (f"Zelle der Messreihe ({rot_text(rot)}, θ = {theta_text(theta)}, {cell['N']} Instanzen): in {fshare(cell['pmin'])} der Instanzen mindestens eine nachweislich nicht packbare Tour, "
            f"in {fshare(cell['pmax'])} mindestens eine nicht packbare oder unbekannte.")
    if cls == "nie":
        art, kern = "success", "Die Fläche reicht hier (höchstens 10 % der Instanzen mit einer nicht packbaren oder unbekannten Tour)."
    elif cls == "oft":
        art, kern = "warning", "Die Fläche reicht hier oft nicht (mindestens die Hälfte der Instanzen mit einer nachweislich nicht packbaren Tour)."
    else:
        art, kern = "info", "Grenzfall: weder „reicht“ noch „reicht oft nicht“."
    fuss = ""
    if abs(phi - 0.90) > 1e-9:
        fuss = " Gemessen ist die Zelle bei φ = 0,90 (Gesamtfläche der Teile 90 % der Ladefläche aller Fahrzeuge); bei φ = 0,75 ist die Flotte weniger voll, die Meldung ist dort eher zu streng (aus der Faustregel der Frage 3 abgeleitet, für die Frage 1 nicht gemessen)."
    return art, f"{kern} {kopf}{fuss}"


def verdict_packen(cell, rot):
    """Preis des Packens aus der Zelle der Messreihe M2: relevant / nicht relevant / dazwischen."""
    if cell is None:
        return "info", "Für diese Einstellung liegt keine Zelle der Messreihe vor."
    kopf = (f"Zelle der Messreihe ({rot_text(rot)}, {cell['N']} Instanzen): mittlerer Preis des Packens Δ_U = {fpct(cell['dU'])} gegen die Flächenlösung bei θ = 1,00; "
            f"in {fshare(cell['dU1'])} der Instanzen mindestens 1 %.")
    if cell["relU"]:
        return "warning", f"Das Packen kostet hier spürbar (Δ_U ≥ 2 % im Mittel und bei mindestens der Hälfte der Instanzen ≥ 1 %). {kopf}"
    if cell["nonU"]:
        return "success", f"Das Packen kostet hier kaum etwas (Δ_U unter 0,5 % im Mittel). {kopf}"
    return "info", f"Das Packen kostet hier im Mittel etwas, erfüllt aber nicht beide Bedingungen für „spürbar“ (Mittel ≥ 2 % und bei mindestens der Hälfte der Instanzen ≥ 1 %). {kopf}"


def verdict_reparatur(cell, rot):
    """Reicht die Reparatur der Flächenlösung (mit lokaler Suche)? Aus der Zelle der Messreihe M2 (U)."""
    if cell is None:
        return "info", "Für diese Einstellung liegt keine Zelle der Messreihe vor."
    kopf = (f"Zelle der Messreihe ({rot_text(rot)}, {cell['N']} Instanzen): Reparatur mit lokaler Suche im Mittel {fpct(cell['repU'])} teurer als die Suche, "
            f"Reparatur ohne lokale Suche {fpct(cell['rep0U'])}, im Mittel {fz(cell['repUV'], 2)} Fahrzeuge mehr.")
    if cell["okU"]:
        return "success", f"Die Reparatur genügt hier (höchstens 1 % über der Suche und höchstens 0,1 Fahrzeuge mehr). {kopf}"
    if cell["badU"]:
        return "warning", f"Die Reparatur genügt hier nicht (mindestens 3 % über der Suche oder mindestens 0,3 Fahrzeuge mehr). {kopf}"
    return "info", f"Die Reparatur liegt zwischen „genügt“ und „genügt nicht“. {kopf}"


def verdict_reihenfolge(cell, rot):
    """Preis der Entladereihenfolge (L gegen U) aus der Zelle der Messreihe M2."""
    if cell is None:
        return "info", "Für diese Einstellung liegt keine Zelle der Messreihe vor."
    kopf = (f"Zelle der Messreihe ({rot_text(rot)}, {cell['N']} Instanzen): mittlerer Preis der Reihenfolge Δ_L = {fpct(cell['dL'])} gegen U; "
            f"in {fshare(cell['dL05'])} der Instanzen mindestens 0,5 %.")
    if cell["relL"]:
        return "warning", f"Die Entladereihenfolge kostet hier spürbar (Δ_L ≥ 1 % im Mittel und bei mindestens der Hälfte der Instanzen ≥ 0,5 %). {kopf}"
    if cell["nonL"]:
        return "success", f"Die Entladereihenfolge kostet hier kaum etwas (Δ_L unter 0,3 % im Mittel). {kopf}"
    return "info", f"Die Entladereihenfolge kostet hier im Mittel etwas, erfüllt aber nicht beide Bedingungen für „spürbar“ (Δ_L ≥ 1 % im Mittel und bei mindestens der Hälfte der Instanzen ≥ 0,5 %) und liegt über „kaum“ (unter 0,3 %). {kopf}"


def verdict_instanz(infos_u, infos_l, theta, rot, with_l=True):
    """Aussage über die EINE gezeigte Instanz (Flächenlösung bei θ): Zählung der Tourstatus. Kein Urteil über die Zelle. Ohne `with_l` (40 Kunden live) nur ohne Reihenfolge."""
    cu = count_status(infos_u, "u")
    n = len(infos_u)
    text = (f"Diese eine Instanz ({rot_text(rot)}, θ = {theta_text(theta)}): von {n} Touren sind ohne Reihenfolge {cu['feas']} packbar, {cu['infeas']} nachweislich nicht packbar, "
            f"{cu['unknown']} unbekannt")
    if with_l:
        cl = count_status(infos_l, "l")
        text += f"; mit Entladereihenfolge {cl['feas']} packbar, {cl['infeas']} nachweislich nicht packbar, {cl['unknown']} unbekannt."
    else:
        text += "; mit Entladereihenfolge ist bei 40 Kunden live nicht geprüft."
    if cu["infeas"] > 0:
        return "warning", text
    if cu["unknown"] > 0:
        return "info", text
    return "success", text


def verdict_suche(rec):
    """Aussage über die gespeicherte oder live gerechnete Suche dieser Instanz (eine Instanz, Preise sind Obergrenzen)."""
    du, dl = price_packing(rec), price_order(rec)
    text = (f"Diese eine Instanz: Preis des Packens Δ_U = {fpct(du)} (Kosten {rec['U']['cost']} gegen {rec['area_best']['cost']} der Flächenlösung bei θ = 1,00), "
            f"Preis der Entladereihenfolge Δ_L = {fpct(dl)} (L {rec['L']['cost']} gegen U {rec['U']['cost']}). Die Suche zählt „unbekannt“ als nicht packbar: ihre Kosten sind Obergrenzen der Kosten der besten packbaren Lösung, ein Preis aus zwei Näherungen ist kein garantierter Höchstwert.")
    return ("warning" if du >= 2.0 else "info"), text


def zelle_phi_hinweis(phi):
    """Hinweis zur Zuordnung der Zelle: M1 ist nur bei φ = 0,90 gemessen."""
    if abs(phi - 0.90) > 1e-9:
        return "Die Zellen der Frage „Reicht die Fläche?“ sind bei φ = 0,90 gemessen; bei φ = 0,75 ist die nächstliegende Zelle die mit φ = 0,90."
    return ""


def tour_caption(t, which="u"):
    """Unterschrift der Ladeflächen-Zeichnung einer Tour: Status, Füllgrad, Zahl der Teile, bei nicht packbaren Touren die Teile ohne Platz in der einfachen Teil-Packung."""
    status = t["u"] if which == "u" else t["l"]
    names = {"feas": "packbar", "infeas": "nachweislich nicht packbar", "unknown": "unbekannt", "skip": "nicht geprüft"}
    text = f"{names[status]}; Füllgrad {fshare(t['fill'])}, {t['parts']} Teile"
    left = t["u_left"] if which == "u" else []
    if left:
        text += "; in der einfachen Teil-Packung bleibt 1 Teil ohne Platz" if len(left) == 1 else f"; in der einfachen Teil-Packung bleiben {len(left)} Teile ohne Platz"
    return text
