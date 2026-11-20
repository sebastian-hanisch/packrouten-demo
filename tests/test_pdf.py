"""PDF-Export: Sonderzeichen werden bereinigt (fpdf2-Standardschriften), der Tourenplan lässt sich mit und ohne Suche ausgeben."""

import pytest

import prt_constants as K
import prt_live as L
import prt_pdf_export as PDF
import prt_results as R


def test_clean_ersetzt_sonderzeichen_und_streicht_emoji():
    text = PDF.clean("Fahrzeuge – Σd ≥ 20 % → ± 5 € „Test“ 🚚 ✓ Δ θ φ ↻ − ≤")
    for zeichen in "–→±€🚚✓Δθφ↻−≤Σ":
        assert zeichen not in text
    assert "Fahrzeuge" in text and ">= 20" in text and "EUR" in text and "Summe" in text and "theta" in text and "phi" in text and "Delta" in text
    text.encode("latin-1")                                       # muss in der Standardschrift darstellbar sein
    assert PDF.clean("Größe, Füllgrad, Maße, Tür") == "Größe, Füllgrad, Maße, Tür"          # Umlaute und ß bleiben


@pytest.mark.parametrize("rot", [False, True])
@pytest.mark.parametrize("preset", ["Standard", "Wenige große Teile"])
def test_pdf_mit_und_ohne_suche(preset, rot):
    p = K.PRESETS[preset]
    s = L.Settings(p["n"], p["k"], p["spread"], p["phi"], p["depot"], p["theta"], rot, p["seed"])
    view = L.area_view(s.n, s.depot, s.seed, s.k, s.phi, s.spread, s.rot, s.theta)
    rec = R.stored_record(rot, p["depot"], p["n"], p["k"], p["spread"], p["phi"], p["seed"])
    for r in (None, rec):
        data = PDF.build_pdf(s, view, r)
        assert data[:5] == b"%PDF-" and len(data) > 1500
