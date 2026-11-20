"""Plotly-Figuren: Tourenkarte, Ladefläche mit Rechtecken je Tour, Zellenkarte, Füllgrad, Preis nach Teilen je Fahrzeug, billige Wege gegen Suche.
Alle Achsen fest (fixedrange), damit Touch-Scrollen auf der Seite nicht am Chart hängen bleibt."""

from __future__ import annotations

import plotly.graph_objects as go

import prt_constants as K
import prt_evaluation as E

STATUS_COLOR = {"feas": K.COLOR_OK, "infeas": K.COLOR_BAD, "unknown": K.COLOR_UNKNOWN}
STATUS_SHORT = {"feas": "packbar", "infeas": "nicht packbar", "unknown": "unbekannt", "skip": "nicht geprüft"}
STATUS_TEXT = {"feas": "packbar", "infeas": "nachweislich nicht packbar", "unknown": "unbekannt", "skip": "nicht geprüft"}


def _fixed(fig, height, **layout):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=40, b=10), **layout)
    return fig


def customer_color(c):
    return K.CUSTOMER_COLORS[(c - 1) % len(K.CUSTOMER_COLORS)]


# ------------------------------------------------------------------------------------------------ Tourenkarte

def fig_routes(xy, tours, title="Touren der Flächenlösung"):
    """Depot, Kunden und Touren; die Farbe einer Tour ist ihr Status ohne Reihenfolge (grün packbar, rot nachweislich nicht packbar, gelb unbekannt)."""
    fig = go.Figure()
    for ti, t in enumerate(tours):
        pts = [xy[0]] + [xy[c] for c in t["route"]] + [xy[0]]
        fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="lines+markers", name=f"Tour {ti + 1}: {STATUS_TEXT[t['u']]}",
                                 line=dict(color=STATUS_COLOR[t["u"]], width=2), marker=dict(size=6),
                                 hovertemplate="Tour " + str(ti + 1) + "<extra></extra>"))
    fig.add_trace(go.Scatter(x=[xy[0][0]], y=[xy[0][1]], mode="markers", name="Depot", marker=dict(symbol="square", size=12, color="black"), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[-5, 105], y=[-5, 105], mode="markers", marker=dict(opacity=0), showlegend=False, hoverinfo="skip"))
    _fixed(fig, 380, title=dict(text=title, font=dict(size=14)), legend=dict(orientation="h", y=-0.05), yaxis=dict(scaleanchor="x"))
    fig.update_xaxes(showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(showgrid=False, zeroline=False, visible=False)
    return fig


# ------------------------------------------------------------------------------------------------ Ladefläche

def fig_loading(t, which="u", number=1):
    """Ladefläche (Länge 100 in x, Breite 40 in y, Tür bei x = 100) mit den Rechtecken einer Tour. Farbe je Kunde, gedrehte Rechtecke mit Kreuzschraffur-Rand und ↻.
    Bei nicht packbaren oder unbekannten Touren die einfache Teil-Packung; Rechtecke ohne Platz stehen im Titel."""
    if which == "u":
        place, rect, cust, status, left = t["u_place"], t["rect"], t["cust"], t["u"], t["u_left"]
    else:
        place, rect, cust, status, left = t["l_place"], t["l_rect"], t["l_cust"], t["l"], []
    fig = go.Figure()
    shapes, notes = [], []
    shapes.append(dict(type="rect", x0=0, y0=0, x1=K.LEN, y1=K.W, line=dict(color="#555", width=2), fillcolor="rgba(0,0,0,0)"))
    if place:
        for idx, (pl, (w, l), c) in enumerate(zip(place, rect, cust)):
            if pl is None:
                continue
            x, y = pl[0], pl[1]
            rot = pl[2] if len(pl) > 2 else 0
            sx, sy = (w, l) if rot else (l, w)
            shapes.append(dict(type="rect", x0=x, y0=y, x1=x + sx, y1=y + sy, line=dict(color="white" if not rot else "black", width=1.5, dash="solid" if not rot else "dot"),
                               fillcolor=customer_color(c), opacity=0.9))
            notes.append(dict(x=x + sx / 2, y=y + sy / 2, text=f"{c}{'↻' if rot else ''}", showarrow=False, font=dict(size=10, color="white")))
    shapes.append(dict(type="line", x0=K.LEN, y0=0, x1=K.LEN, y1=K.W, line=dict(color="black", width=5)))
    title = f"Tour {number}: {STATUS_SHORT[status]}"
    fig.add_trace(go.Scatter(x=[0, K.LEN], y=[0, K.W], mode="markers", marker=dict(opacity=0), showlegend=False, hoverinfo="skip"))
    fig.update_layout(shapes=shapes, annotations=notes + [dict(x=K.LEN + 1.5, y=K.W / 2, text="Tür", showarrow=False, textangle=90, font=dict(size=10))],
                      title=dict(text=title, font=dict(size=12, color=STATUS_COLOR[status])))
    _fixed(fig, 150)
    fig.update_xaxes(range=[-1, K.LEN + 5], visible=False)
    fig.update_yaxes(range=[-1, K.W + 1], visible=False)
    return fig


# ------------------------------------------------------------------------------------------------ Zellenkarte, Füllgrad

def fig_zellenkarte(zellen, rot):
    """Zellen der Messreihe M1: Zeile = Depot × (n, k) × Form, Spalte = θ, Farbe und Zahl = Anteil der Instanzen mit mindestens einer nachweislich nicht packbaren Tour."""
    rows = []
    for depot in ("mitte", "rand"):
        for n, k in ((20, 3), (20, 5), (40, 3), (40, 5)):
            for sp in K.SPREAD_CHOICES:
                rows.append((depot, n, k, sp))
    z, text = [], []
    for (depot, n, k, sp) in rows:
        zr, tr = [], []
        for th in K.THETA_CHOICES:
            c = next((c for c in zellen if (c["depot"], c["n"], c["k"], c["spread"]) == (depot, n, k, sp) and abs(c["theta"] - th) < 1e-9), None)
            zr.append(c["pmin"] if c else None)
            tr.append(f"{E.fshare(c['pmin'])}" if c else "")
        z.append(zr)
        text.append(tr)
    labels = [f"{depot.capitalize()} · {n}/{k} · {sp}" for (depot, n, k, sp) in rows]
    fig = go.Figure(go.Heatmap(z=z, x=[E.theta_text(t) for t in K.THETA_CHOICES], y=labels, text=text, texttemplate="%{text}", zmin=0, zmax=1,
                               colorscale=[[0, "#e8f1ef"], [0.5, "#f3dc8c"], [1, "#b5493a"]], showscale=False,
                               hovertemplate="%{y}, θ = %{x}: %{text} der Instanzen mit einer nachweislich nicht packbaren Tour<extra></extra>"))
    _fixed(fig, 520, title=dict(text=f"Nicht packbare Tour je Zelle ({E.rot_text(rot)})", font=dict(size=14)))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Auslastungsgrenze θ", type="category")
    return fig


def fig_fuellgrad(fill_by_state):
    """Anteil nachweislich nicht packbarer Touren je Füllgrad der Tour, Form und Stellung. `fill_by_state`: {(rot, form): [(lo, hi, N, Anteil)]}."""
    fig = go.Figure()
    colors = {"gleich": "#b5493a", "gemischt": "#4c78a8"}
    for (rot, form), bins in fill_by_state.items():
        labels = [f"{E.fz(lo, 2)}–{E.fz(min(hi, 1.0), 2)}" for lo, hi, _, _ in bins]
        fig.add_trace(go.Bar(x=labels, y=[(a * 100 if a is not None else None) for _, _, _, a in bins], name=f"{form}, {E.rot_text(rot)}",
                             marker=dict(color=colors[form], pattern_shape="/" if rot else ""), opacity=0.9,
                             customdata=[n for _, _, n, _ in bins], hovertemplate="Füllgrad %{x}: %{y:.0f} % von %{customdata} Touren<extra></extra>"))
    fig.update_layout(barmode="group", yaxis=dict(range=[0, 100], title="nachweislich nicht packbar (%)"), xaxis=dict(title="Füllgrad der Tour (Fläche der Teile / Ladefläche)"),
                      legend=dict(orientation="h", y=-0.45), title=dict(text="Nicht packbare Touren je Füllgrad", font=dict(size=14)))
    _fixed(fig, 420)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=90))
    return fig


def fig_preis_nach_teilen(gruppen_by_state):
    """Mittlerer Preis des Packens Δ_U je (n, k) und Form. `gruppen_by_state`: {(rot, form): [Gruppen mit n, k, teile_je_fahrzeug, dU]}."""
    fig = go.Figure()
    colors = {"gleich": "#b5493a", "gemischt": "#4c78a8"}
    for (rot, form), gr in gruppen_by_state.items():
        gr = [g for g in gr if g["spread"] == form]
        gr = sorted(gr, key=lambda g: g["teile_je_fahrzeug"])
        fig.add_trace(go.Bar(x=[f"{g['n']}/{g['k']} ({E.fz(g['teile_je_fahrzeug'], 1)} Teile je Fahrzeug)" for g in gr], y=[g["dU"] for g in gr],
                             name=f"{form}, {E.rot_text(rot)}", marker=dict(color=colors[form], pattern_shape="/" if rot else ""), opacity=0.9,
                             text=[E.fz(g["dU"], 1) for g in gr], textposition="outside", hovertemplate="%{x}: Δ_U = %{y:.1f} %<extra></extra>"))
    fig.update_layout(barmode="group", yaxis=dict(title="Preis des Packens Δ_U (%)"), xaxis=dict(title="(n, k) und erwartete Teile je Fahrzeug"),
                      legend=dict(orientation="h", y=-0.5), title=dict(text="Preis des Packens nach (n, k), Form, Stellung", font=dict(size=14)))
    _fixed(fig, 460)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=110))
    return fig


# ------------------------------------------------------------------------------------------------ billige Wege gegen Suche

def fig_billige_wege(steps):
    """Kosten je Verfahren einer Instanz; `steps`: Liste (Name, Kosten, Fahrzeuge, Farbe)."""
    fig = go.Figure(go.Bar(x=[s[0] for s in steps], y=[s[1] for s in steps], marker=dict(color=[s[3] for s in steps]),
                           text=[f"{s[1]}<br>{s[2]} Fahrzeuge" for s in steps], textposition="outside", hovertemplate="%{x}: Kosten %{y}<extra></extra>"))
    hi = max(s[1] for s in steps)
    fig.update_layout(yaxis=dict(title="Kosten (Länge + 250 je Fahrzeug)", range=[0, hi * 1.12]), title=dict(text="Eine Instanz: billige Wege gegen die Suche", font=dict(size=14)))
    _fixed(fig, 400)
    fig.update_xaxes(type="category")
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=70))
    return fig
