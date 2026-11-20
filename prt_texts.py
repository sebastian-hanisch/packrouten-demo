"""Feste Texte der App: Annahmen („Wo die Annahmen enden“), Formeln mit Lesehilfe, Erklärtabelle der Verfahren. Dieselben Fassungen stehen in der README
(tests/test_claims.py vergleicht sie); Zahlen, die aus den Messreihen stammen, werden in der App berechnet und stehen hier nicht; Ausnahme ist die Zeile „Unabhängiger Prüfer“ (die Zahlen prüft tests/test_claims.py)."""

ASSUMPTIONS_MARKDOWN = """| Baustein | Festlegung |
|---|---|
| Instanz | Ein Depot (Rand oder Mitte des 100 × 100-Gebiets), n ∈ {20, 40} Kunden gleichverteilt, ganzzahlige euklidische Entfernungen (1 Längeneinheit = 10 Entfernungseinheiten). Jeder Kunde hat 1, 2 oder 3 Rechtecke (zu 40, 40 und 20 %). Es sind Zufallsinstanzen eines Generators, keine Praxisdaten. |
| Ladefläche | 40 × 100 (Breite × Länge), die Tür liegt an der Stirnseite; Fläche 4 000. Drehung um 90° ist ein Schalter (Standard: aus); andere Winkel, andere Ladeflächen als Regler und 3D gibt es nicht. |
| Form der Teile | „gleich“: ungefähr quadratisch, ähnlich groß (vor der Skalierung Breite 0,40 bis 0,60 und Länge 0,15 bis 0,25 der Ladefläche); „gemischt“: sehr verschieden (vor der Skalierung Breite 0,10 bis 1,00, Länge 0,05 bis 0,60). Alle Maße werden so skaliert, dass die Gesamtfläche der Teile φ mal die Fläche von k Ladeflächen beträgt (φ = 0,75 oder 0,90). Nach der Skalierung liegt die Breite der Form „gleich“ bei 20 Kunden und 5 Ladungen zwischen 0,40 und 0,70 der Ladefläche, bei 40 Kunden und 3 Ladungen zwischen 0,23 und 0,38. |
| Kosten | Länge der Tour plus 250 Entfernungseinheiten (25 Längeneinheiten) je genutzte Tour; ohne Fixkosten wären zusätzliche Fahrzeuge gratis. |
| Ohne Reihenfolge (U) | Die Rechtecke einer Tour liegen überschneidungsfrei in der Ladefläche. |
| Mit Entladereihenfolge (L) | Vereinfachte Fassung: Zusätzlich darf beim Entladen kein Rechteck eines später besuchten Kunden vor einem eines früher besuchten stehen; kein Umladen. Eine Tour und ihre Umkehrung sind gleich lang, L gilt als packbar, wenn eine der beiden Richtungen packbar ist. Die Fassung ist aus Zusammenfassungen der Literatur rekonstruiert, nicht aus den Aufsätzen. |
| Packbarkeit | Notwendige Bedingungen, dann Heuristiken (MaxRects, Skyline), dann exakt mit CP-SAT (deterministische Zeitgrenze). „Unbekannt“ heißt: nach der Zeitgrenze weder gepackt noch widerlegt; die Suche zählt „unbekannt“ als nicht packbar, ihre Kosten sind deshalb Obergrenzen der Kosten der besten packbaren Lösung. Ein Preis ist der Quotient zweier Näherungen und kein garantierter Höchstwert (siehe „Wie stark hängen die Preise am Budget der Suche?“). |
| Suche | Eigene Ruin-and-Recreate-Suche (Relocate, Swap, 2-opt, 2-opt*, Verschmelzen, 400 Iterationen); Start aus der Reparatur, die Fläche anschließend mit Start aus U. Kosten Fläche ≤ U ≤ L und Suche ≤ Reparatur gelten dadurch von Bauart: das ist kein Befund. |
| Basis der Preise | Die Flächenlösung bei θ = 1,00 (volle Fläche). Sie ist selbst nicht packbar; jede Prozentzahl eines Preises nennt diese Basis. |
| Referenzen | Exaktes Verfahren (Partitions-DP, Held-Karp, exakte Packbarkeit) nur bis n = 9; kein Vergleich mit dem Routing von OR-Tools (es kennt keine Packbarkeit je Tour; CP-SAT von OR-Tools wird hier nur für die Packbarkeit je Tour benutzt); kein Zahlenvergleich mit der Literatur. |
| Zufall | SplitMix64 mit Ganzzahlen, Zufalls-Seed je Instanz; die Zeitgrenzen von CP-SAT sind deterministisch (max_deterministic_time), nie Wanduhr. |"""

SYMBOLS_MARKDOWN = """| Symbol | Bedeutung |
|---|---|
| i, c | Kunde (1 bis n) |
| (w_ij, l_ij) | Breite und Länge des j-ten Rechtecks von Kunde i (ganzzahlig) |
| a_i | Fläche des Kunden: Summe der Flächen seiner Rechtecke |
| W, L | Breite und Länge der Ladefläche (40 und 100) |
| R | eine Tour (Folge von Kunden) |
| θ | Auslastungsgrenze: die Flächenlösung belegt höchstens θ · W · L je Tour |
| F | Fixkosten je genutzte Tour (250 Entfernungseinheiten) |
| ℓ(R) | Länge der Tour R einschließlich der Wege vom und zum Depot |
| K | Kosten einer Lösung |
| Δ_U, Δ_L | Preis des Packens und Preis der Entladereihenfolge in Prozent |"""

FORMULAS = [
    r"""R \text{ ist packbar} \iff \exists\, (x_{ij}, y_{ij}) \text{ mit } 0 \le x_{ij},\; x_{ij} + l_{ij} \le L,\; 0 \le y_{ij},\; y_{ij} + w_{ij} \le W \text{ und paarweise überschneidungsfrei}""",
    r"""\sum_{i \in R} a_i \le \theta \cdot W \cdot L \qquad \text{(Flächen-Relaxation; } \theta = 1 \text{ ist das klassische CVRP mit der Fläche als Kapazität)}""",
    r"""K = \sum_{R} \bigl(\ell(R) + F\bigr)""",
    r"""\Delta_U = \frac{K_U - K_{\text{Fläche}}}{K_{\text{Fläche}}}, \qquad \Delta_L = \frac{K_L - K_U}{K_U}, \qquad \text{Lücke} = \frac{K_{\text{Verfahren}} - K_{\text{Suche}}}{K_{\text{Suche}}}""",
]
FORMULAS_NOTE = ("Mit Entladereihenfolge (L) kommt hinzu: haben die Rechtecke zweier Kunden i früher und j später in der Tour überlappende y-Bereiche, muss "
                 "x_j + l_j ≤ x_i gelten. Das ist kein vollständiges Modell der Tourenplanung mit Packen, sondern die Prüfbedingung, die die Suche für jede Tour verwendet; "
                 "die Tourenplanung selbst (jeder Kunde genau einmal, Kosten Länge plus Fixkosten) steht in der Suche, nicht als Formelmodell.")

METHODS_ROWS = [
    ("Fläche (θ)", "CVRP mit der Fläche der Teile als Nachfrage und θ · 4 000 als Kapazität; keine Packbarkeitsprüfung.", "Frage 1 und 2; Reiter Messreihe: Zellen der Frage 1"),
    ("Faustregel θ", "Das größte θ aus 0,90, 0,80, 0,70, dessen Flächenlösung nur packbare Touren enthält; kostet gegen die Suche Mehrkosten.", "Frage 3; Faustregel"),
    ("Reparatur (roh)", "Aus jeder nicht packbaren Tour der Flächenlösung (θ = 1,00) wird der Kunde mit der größten Fläche entfernt, bis sie packbar ist; die Entfernten werden am billigsten zulässig eingefügt.", "Frage 3; Reparatur gegen Suche"),
    ("Reparatur mit lokaler Suche", "Wie die rohe Reparatur, danach eine lokale Suche (Relocate, Swap, 2-opt, 2-opt*, Verschmelzen) ohne Neustarts.", "Frage 3; Reparatur gegen Suche"),
    ("Suche", "Ruin-and-Recreate mit der Packbarkeitsprüfung als Zulässigkeitstest, 400 Iterationen; Start aus der Reparatur. Kein exaktes Verfahren: Güte nur bei n = 8 gegen ein Orakel geprüft.", "Frage 2 und 3; Reiter Messreihe: Kontrolle der Suche"),
    ("Packbarkeit: Heuristik", "MaxRects (drei Reihenfolgen, drei Wertungen), Skyline und deterministisch gemischte Reihenfolgen; hinreichend, nicht notwendig.", "Prüfung jeder Tour; Reiter Messreihe: Heuristik gegen exakt"),
    ("Packbarkeit: exakt", "CP-SAT mit NoOverlap2D; Status packbar, nachweislich nicht packbar oder unbekannt (Zeitgrenze erreicht).", "Prüfung jeder Tour"),
    ("Unabhängiger Prüfer", "Sucht für jede Tour einer Lösung noch einmal eine Packung (Heuristik, dann CP-SAT) und rechnet diese mit eigenem Code nach (Außerhalb, Überlappung, Entladereihenfolge, Orientierung). Findet er in seiner Zeitgrenze keine Packung, besteht die Lösung nicht („unbekannt“): in der Frage 2 traf das ohne Drehung 0 von 192 Lösungen, mit Drehung 5 von 96; dazu 2 von 64 in der Kontrolle der Teile je Kunde (ohne wie mit Drehung) und 1 von 8 beim kalten Lauf mit Drehung. In den 6 Fällen mit gespeicherter Tour fand CP-SAT mit mehr Zeit eine bestätigte Packung: ein Artefakt der Reihenfolge der Rechtecke im Modell, kein Fehler der Lösung.", "Lösungen der Messreihen"),
]
