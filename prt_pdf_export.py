"""Tourenplan als PDF (fpdf2, Standardschriften): Kennzahlen, Touren mit Status und die Ladefläche jeder Tour als Rechtecke.
Sonderzeichen werden vorher bereinigt: Gedankenstrich, Minuszeichen, Euro, Pfeile, griechische Buchstaben und Emoji stürzen die Standardschriften sonst ab
(DEMO-PLAYBOOK, fpdf2-Falle)."""

from fpdf import FPDF

import prt_constants as K
import prt_evaluation as E

_REPLACE = {"–": "-", "—": "-", "−": "-", "€": "EUR", "„": '"', "“": '"', "”": '"', "‚": "'", "‘": "'", "’": "'", "→": "->", "×": "x", "±": "+/-",
            "≤": "<=", "≥": ">=", "·": "-", "…": "...", "θ": "theta", "φ": "phi", "Δ": "Delta", "Σ": "Summe", "↻": "R"}
_STATUS = {"feas": "packbar", "infeas": "nachweislich nicht packbar", "unknown": "unbekannt"}


def clean(text: str) -> str:
    """Nur Zeichen der Standardschrift (Latin-1) behalten; bekannte Sonderzeichen ersetzen, Unbekanntes (Emoji) streichen."""
    for old, new in _REPLACE.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "ignore").decode("latin-1")


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _draw_loading(pdf, t, x0, y0, scale=0.9):
    """Ladefläche 100 x 40 als Rechtecke (Länge in x, Breite in y), Tür rechts; Kundennummer im Rechteck, gedrehte mit R."""
    pdf.set_draw_color(80, 80, 80)
    pdf.rect(x0, y0, K.LEN * scale, K.W * scale)
    for pl, (w, l), c in zip(t["u_place"] or [], t["rect"], t["cust"]):
        if pl is None:
            continue
        x, y = pl[0], pl[1]
        rot = pl[2] if len(pl) > 2 else 0
        sx, sy = (w, l) if rot else (l, w)
        pdf.set_fill_color(*_rgb(K.CUSTOMER_COLORS[(c - 1) % len(K.CUSTOMER_COLORS)]))
        pdf.set_draw_color(255, 255, 255)
        pdf.rect(x0 + x * scale, y0 + y * scale, sx * scale, sy * scale, style="DF")
        if sx * scale > 5 and sy * scale > 3:
            pdf.set_font("Helvetica", "", 6)
            pdf.set_text_color(255, 255, 255)
            pdf.set_xy(x0 + x * scale, y0 + y * scale + sy * scale / 2 - 1.5)
            pdf.cell(sx * scale, 3, f"{c}{'R' if rot else ''}", align="C")
            pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.8)
    pdf.line(x0 + K.LEN * scale, y0, x0 + K.LEN * scale, y0 + K.W * scale)
    pdf.set_line_width(0.2)


def build_pdf(s, view, rec=None) -> bytes:
    """`s`: Einstellungen (prt_live.Settings); `view`: Ergebnis von prt_live.area_view; `rec`: Datensatz mit Suche (gespeichert oder live) oder None."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 9, clean("Packen und Routen: Tourenplan"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, clean(
        f"{s.n} Kunden, Depot {s.depot}, {s.k} Ladungen, Form der Teile {s.spread}, Gesamtfläche der Teile {E.fshare(s.phi)} der Ladefläche aller Fahrzeuge, Auslastungsgrenze "
        f"theta = {E.theta_text(s.theta)}, {E.rot_text(s.rot)}, Zufalls-Seed {s.seed}. Ladefläche {K.W} x {K.LEN}, Fixkosten je Fahrzeug {K.F_FIX} Entfernungseinheiten."),
        new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, clean("Flächenlösung dieser Instanz"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, clean(f"Fahrzeuge {view['V']}, Distanz {E.fz(view['D'], 1)}, Kosten {view['cost']}. "
                               f"Touren ohne Reihenfolge packbar: {sum(1 for t in view['tours'] if t['u'] == 'feas')}, nachweislich nicht packbar: "
                               f"{sum(1 for t in view['tours'] if t['u'] == 'infeas')}, unbekannt: {sum(1 for t in view['tours'] if t['u'] == 'unknown')}."),
                   new_x="LMARGIN", new_y="NEXT")
    if rec and "U" in rec:
        pdf.ln(1)
        pdf.multi_cell(0, 5, clean(f"Suche (eine Instanz; die Kosten der Suche sind Obergrenzen der Kosten der besten packbaren Lösung): Fläche bei theta = 1,00 Kosten {rec['area_best']['cost']}, ohne Reihenfolge (U) {rec['U']['cost']} "
                                   f"(Delta_U = {E.fpct(E.price_packing(rec))}), mit Entladereihenfolge (L) {rec['L']['cost']} (Delta_L = {E.fpct(E.price_order(rec))})."),
                       new_x="LMARGIN", new_y="NEXT")
    for i, t in enumerate(view["tours"]):
        if pdf.get_y() > 235:
            pdf.add_page()
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        stops = " - ".join(f"K{c}" for c in t["route"])
        pdf.multi_cell(0, 5, clean(f"Tour {i + 1}: {_STATUS[t['u']]} (Füllgrad {E.fshare(t['fill'])}, {t['parts']} Teile): Depot - {stops} - Depot"), new_x="LMARGIN", new_y="NEXT")
        y0 = pdf.get_y() + 1
        _draw_loading(pdf, t, 12, y0)
        pdf.set_y(y0 + K.W * 0.9 + 2)
        if t["u_left"]:
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 4, clean(f"Teil-Packung (einfache Heuristik): {len(t['u_left'])} Teile ohne Platz."), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 4, clean("Eine Instanz, kein Beleg: die Aussagen der Demo stützen sich auf die vorgerechnete Messreihe (Mittel über 12 Instanzen je Zelle in der Frage "
                               "'Reicht die Fläche?', 3 bis 6 in der Frage 'Was kostet das Packen?'). Distanz in Längeneinheiten des 100 x 100-Gebiets."), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
