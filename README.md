# Packen und Routen: reicht die Fläche als Kapazität? – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-packrouten-demo.streamlit.app/)**

Fall-Demo für die Website „Sebastian Hanisch – Operations Research und Machine Learning“ (`demos.html`, Gruppe „Transport & Tourenplanung“). Ein Fahrzeug fasst nicht „Mengen“, sondern **Teile mit Maßen**. Die Demo fragt: **Wann genügt es, die Fläche der Teile zu addieren, und was kostet es, wenn die Teile wirklich in die Ladefläche passen müssen?** (eine **vereinfachte Fassung** des CVRP mit zweidimensionaler Packung, kurz 2L-CVRP). Sie zeigt eine Instanz live (Flächenlösung und Packbarkeit je Tour; Reparatur und Faustregel bei 20 Kunden sofort, bei 40 Kunden auf Knopfdruck; die Suche für die Instanzen der Messreihe und die Presets gespeichert, bei 20 Kunden auch live mit kleinem Budget) und stützt jede Aussage auf **vorgerechnete Messreihen** über Zufallsinstanzen, ohne und mit **Drehung der Rechtecke um 90°**.

## Warum dieses Problem

Tourenplanung rechnet Kapazität meist als Zahl (Menge, Gewicht, Fläche). Ladungen sind aber Rechtecke: zwei Teile von 25 × 60 haben zusammen die Fläche 3 000 und passen nicht in eine Ladefläche von 40 × 100 mit der Fläche 4 000. Wann die Fläche als Kapazität reicht, hängt an der **Auslastungsgrenze θ** (die Flächenlösung belegt höchstens θ der Ladefläche) und an den Teilen (Zahl und Größe im Verhältnis zur Ladefläche; ob die Größe die Ursache ist, ist nicht gesichert). Der Aufhänger folgt der Messung: **Ohne Drehung gibt es in 12 von 16 Gruppen (Depot × Kunden × Ladungen × Form) eine Auslastungsgrenze θ, ab der bei mindestens der Hälfte der Instanzen eine Tour nachweislich nicht packbar ist, bei 20 Kunden und 5 Ladungen schon ab 0,70 bis 0,80. Mit Drehung der Rechtecke um 90° gibt es sie nur in 5 von 16 Gruppen (bei 20 Kunden und 5 Ladungen ab 0,80 bis 1,00): die Drehung entschärft das Problem, löst es nicht.** Der Preis des Packens ist in 25 von 32 Zellen ohne Drehung und in 16 von 32 Zellen mit Drehung spürbar (beide auf denselben 96 Instanzen; mit allen 192 Instanzen ohne Drehung 26; „spürbar“ heißt: mittlerer Preis mindestens 2 % und bei mindestens der Hälfte der Instanzen mindestens 1 %; „kaum“: unter 0,5 %), er fällt aber mit der Zahl der Teile je Fahrzeug.

Nachbarn: `vrp-demo` (Tourenplanung, Verfahrensvergleich, ohne Packen), `pack-demo` (3D-Packung), `fahrzeuggroesse-demo` (Fixkosten und Reserve: Kapazität als Zahl, nicht als Fläche). Das gemeinsame Rechenmodell dieser Demo ist ein CVRP mit Fixkosten je Tour plus eine Packbarkeitsbedingung je Tour; verwandt ist die Packbarkeitsprüfung mit der Packen-Reihe, die Tourenplanung mit der Linie Transport & Tourenplanung.

## Modell

Ein Depot (am Rand (50, 0) oder in der Mitte (50, 50)), `n` Kunden (20 oder 40) gleichverteilt im 100 × 100-Gebiet, ganzzahlige euklidische Entfernungen. Jeder Kunde hat 1, 2 oder 3 Rechtecke; die Ladefläche ist 40 × 100. Die Flächenlösung plant mit der Fläche der Teile als Nachfrage und `θ · 4 000` als Kapazität; „packbar“ heißt, dass die Rechtecke einer Tour überschneidungsfrei in die Ladefläche passen (**ohne Reihenfolge, U**) und, in einer vereinfachten Fassung, dass beim Entladen kein später besuchter Kunde vor einem früher besuchten steht (**mit Entladereihenfolge, L**). Die Formeln stehen im 📐-Expander der App. Die Annahmen und ihre Grenzen (Text der App, „Wo die Annahmen enden“):

| Baustein | Festlegung |
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
| Zufall | SplitMix64 mit Ganzzahlen, Zufalls-Seed je Instanz; die Zeitgrenzen von CP-SAT sind deterministisch (max_deterministic_time), nie Wanduhr. |

## Methodik

- **Fläche:** CVRP mit der Fläche als Nachfrage (Savings-Start, Ruin-and-Recreate), Kapazität `θ · 4 000` mit θ ∈ {0,70; 0,80; 0,90; 1,00}; ohne Packbarkeitsprüfung.
- **Packbarkeit:** Heuristiken (MaxRects in drei Reihenfolgen und drei Wertungen, Skyline, deterministisch gemischte Reihenfolgen), dann CP-SAT mit NoOverlap2D; mit Drehung zusätzlich Fassungen mit Orientierung je Rechteck (optionale Intervalle). Live prüft die App bei 20 Kunden mit der CP-SAT-Zeit der Messreihen (0,3 ohne, 1,0 mit Drehung je Tour), bei 40 Kunden mit 0,3 und ohne die Entladereihenfolge (Rechenzeit). Ein unabhängiger Prüfer sucht für jede Tour einer Lösung noch einmal eine Packung (Heuristik, dann CP-SAT) und rechnet diese nach (Außerhalb, Überlappung, Entladereihenfolge, Orientierung); findet er in seiner Zeitgrenze keine, besteht die Lösung nicht („unbekannt“): in der Frage 2 ohne Drehung 0 von 192 Lösungen, mit Drehung 5 von 96, dazu 2 von 64 in der Kontrolle der Teile je Kunde (ohne wie mit Drehung) und 1 von 8 beim kalten Lauf mit Drehung; in den 6 Fällen mit gespeicherter Tour fand CP-SAT mit mehr Zeit eine bestätigte Packung (ein Artefakt der Reihenfolge der Rechtecke im Modell, kein Fehler der Lösung).
- **Reparatur:** aus jeder nicht packbaren Tour der Flächenlösung (θ = 1,00) wird der Kunde mit der größten Fläche entfernt, bis sie packbar ist; die Entfernten werden am billigsten zulässig eingefügt; „mit lokaler Suche“ folgt eine lokale Suche ohne Neustarts.
- **Faustregel:** das größte θ aus 0,90, 0,80 und 0,70, dessen Flächenlösung nur packbare Touren enthält.
- **Suche:** Ruin-and-Recreate mit der Packbarkeitsprüfung als Zulässigkeitstest, 400 Iterationen, Start aus der Reparatur. Sie ist **kein** exaktes Verfahren; Reparatur und Suche hatten nicht denselben Rechenaufwand, die Lücke ist keine Rangfolge der Verfahren.
- **Messreihen:** die Aggregate in `data/prt_results.json` stammen aus den Messreihen vor dem Bau (ohne Drehung: erste Messreihe mit 192 Instanzen für die Fragen 2 und 3, 12 Instanzen je Zelle für die Frage 1; mit Drehung: die Frage 1 auf 192 Instanzen, die Fragen 2 und 3 auf 96). `tools/dump_results.py` verdichtet die Rohdaten (Stunden Rechenzeit, nicht im Repo); `tools/preset_suche.py` rechnet die gespeicherte Suche der Presets, `tools/find_preset_seeds.py` sucht ihre Zufalls-Seeds. Der Rechenkern der Demo ist der der Messreihen ohne Importe aus Nachbarordnern; auf drei Instanzen der Messreihen (je eine ohne und mit Drehung bei 20 Kunden, 5 Ladungen, und eine ohne Drehung bei 20 Kunden, 3 Ladungen) stimmten Kosten und Touren beim Bau exakt überein (Prüflauf beim Bau, Messung dieser README, nicht im Test; im Test gilt ein Band, siehe Verifikation).
- **Presets:** fünf Instanzen, je Preset der kleinste Zufalls-Seed ab 740000, der die Geschichte des Presets zeigt (Kriterien in `prt_stories.py`, festgelegt vor der Suche; Bericht in `tools/PRESET_SWEEP.md`):

| Preset | Einstellung | Zufalls-Seed | Geschichte (geprüft in `tests/test_presets.py`) |
|---|---|---|---|
| Standard | 20 Kunden, 3 Ladungen, gemischt, φ = 0,90, Mitte, θ = 0,90 | 740000 | alle Touren der Flächenlösung bei θ = 0,90 ohne Drehung packbar |
| Wenige große Teile | 20 Kunden, 5 Ladungen, gleich, φ = 0,90, Rand, θ = 0,90 | 740000 | bei θ = 0,90 und bei θ = 0,80 mindestens eine Tour selbst mit Drehung nachweislich nicht packbar; Preis des Packens mindestens 10 % ohne und mindestens 3 % mit Drehung |
| Viele kleine Teile | 40 Kunden, 3 Ladungen, gemischt, φ = 0,75, Mitte, θ = 0,90 | 740003 | alle Touren bei θ = 0,90 ohne Drehung packbar, Kosten höchstens 0,5 % über denen bei θ = 1,00, Preis des Packens höchstens 2 % (beide Stellungen) |
| Grenzfall bei voller Auslastung | 20 Kunden, 3 Ladungen, gemischt, φ = 0,90, Rand, θ = 1,00 | 740003 | bei θ = 0,90 alle Touren ohne Drehung packbar, bei θ = 1,00 mindestens eine selbst mit Drehung nachweislich nicht packbar |
| Reihenfolge kostet | 20 Kunden, 5 Ladungen, gemischt, φ = 0,90, Mitte, θ = 0,90 | 740005 | bei θ = 0,90 mindestens eine Tour ohne Reihenfolge packbar (ohne Drehung), mit Entladereihenfolge selbst mit Drehung nachweislich nicht; Preis der Reihenfolge ohne Drehung mindestens 1 % |

Eine Instanz streut: die Meldungen der App stützen sich auf die Zelle der Messreihe, nicht auf den einen gezeigten Lauf.

## Befunde (gemessen, keine Behauptungen)

Die Zahlen der Tabelle stehen in `data/prt_results.json` (Aggregate der Messreihen) und werden in `tests/test_claims.py` aus dieser Datei nachgerechnet, soweit die Spalte „Test“ einen Test nennt; Angaben zu Zellenzahlen, Prüfläufen beim Bau und Laufzeiten sind Messungen dieser README und stehen nicht im Test. Ohne Drehung stammen die Zahlen aus der ersten Messreihe (Fragen 1 bis 3) und der Restmessung vor dem Bau (Kontrollen), mit Drehung aus der Messreihe „Drehung“ (Zufalls-Seeds 600000 bis 600011 für die Frage 1, 610000 bis 610005 bzw. 610000 bis 610002 für die Fragen 2 und 3).

| Frage | Befund | Test |
|---|---|---|
| Reicht die Fläche? | Von den 64 Zellen (Depot × (n, k) × Form × θ, je 12 Instanzen, φ = 0,90) sind ohne Drehung 25 „Fläche reicht“ (höchstens 10 % der Instanzen mit einer nicht packbaren oder unbekannten Tour), 27 „Fläche reicht oft nicht“ (mindestens die Hälfte der Instanzen mit einer nachweislich nicht packbaren Tour) und 12 Grenzfälle; mit Drehung 35, 10 und 19. Mit Drehung ist der Nachweis schwerer (mehr Touren bleiben „unbekannt“), die 10 sind eine Untergrenze: zählt man „unbekannt“ als Problem mit (mindestens die Hälfte der Instanzen mit einer nicht packbaren oder unbekannten Tour), sind es ohne Drehung 30 und mit Drehung 18 Zellen | `test_claim_flaeche_zellenklassen` |
| Hängt das an θ und an den Teilen je Fahrzeug? | Zellen „reicht oft nicht“ je θ (0,70 / 0,80 / 0,90 / 1,00, je 16 Zellen): ohne Drehung 2 / 4 / 9 / 12, mit Drehung (Untergrenze) 0 / 2 / 3 / 5; je (n, k) (20/3, 20/5, 40/3, 40/5, je 16 Zellen): ohne Drehung 6 / 14 / 0 / 7, mit Drehung 1 / 9 / 0 / 0 (Teile je Fahrzeug im Erwartungswert 12,0 / 7,2 / 24,0 / 14,4; vier Punkte: eine Rangfolge, keine Ursache) | `test_claim_flaeche_theta_und_nk` |
| Bei gleichem Füllgrad: Form und Zahl der Teile? | Touren ab Füllgrad 0,85 mit bekanntem Status: ohne Drehung sind 77,7 % der Touren der Form „gleich“ (480 Touren) und 40,1 % der Form „gemischt“ (461) nachweislich nicht packbar; bei höchstens 10 Teilen je Tour 86,7 % (293), bei mindestens 11 Teilen 46,9 % (648); mit Drehung 34 % (389) und 19 % (467), 66 % (293) und 5 % (563). Deutung (aus den Zählungen, nicht gesondert gemessen): Teile, die breiter als die halbe Ladefläche sind, können nicht nebeneinander stehen; das trifft die Form „gleich“ bei 20 Kunden und 5 Ladungen (69 % der Rechtecke bei φ = 0,90), bei 40 Kunden gar nicht (0 von 449 Rechtecken); warum die Form bei 40 Kunden trotzdem zählt, ist nicht geklärt | `test_claim_flaeche_fuellgrad_form_und_teile` |
| Ab welchem θ ist die Fläche oft zu groß? | Kleinstes θ des Rasters mit „reicht oft nicht“: bei 20 Kunden, 5 Ladungen, Form gleich ohne Drehung ab 0,70 (Depot Mitte und Rand), mit Drehung ab 0,80; bei 40 Kunden und 3 Ladungen (24 Teile je Fahrzeug) in keiner Gruppe im Raster, ohne und mit Drehung (bei θ = 1,00 teils nur „unbekannt“). Gruppen mit einem Kipp-θ im Raster: ohne Drehung 12 von 16, mit Drehung 5 von 16 (alle bei 20 Kunden); bei 20 Kunden und 5 Ladungen ohne Drehung ab 0,70 bis 0,80, mit Drehung ab 0,80 bis 1,00 | `test_claim_kipp_theta` |
| Was kostet das Packen? | Preis Δ_U = (Kosten der Suche ohne Reihenfolge − Kosten der Flächenlösung bei θ = 1,00) / Kosten der Flächenlösung: ohne Drehung im Mittel 8,9 % (Median 5,7 %) über 192 Instanzen, ΔV +0,60 Fahrzeuge; auf denselben 96 Instanzen ohne Drehung 9,6 % (Median 7,1 %), mit Drehung 3,9 % (Median 1,8 %); der Preis ist der Quotient zweier Näherungen (siehe „Ist die Suche gut?“) | `test_claim_preis_des_packens` |
| Wovon hängt der Preis ab? | Mittel je (n, k) und Form (ohne Drehung, 24 Instanzen je Gruppe): von 0,9 % ((40, 3), gemischt, 24,0 Teile je Fahrzeug) bis 27,3 % ((20, 5), gleich, 7,2 Teile je Fahrzeug); mit Drehung (12 Instanzen je Gruppe) von 0,4 % ((20, 3), gemischt) bis 9,8 % ((20, 5), gleich). Zellenurteile (32 Zellen aus Depot × (n, k) × Form × φ; „spürbar“: mittleres Δ_U ≥ 2 % und bei mindestens der Hälfte der Instanzen ≥ 1 %, „kaum“: unter 0,5 %): ohne Drehung auf 192 Instanzen 26 „spürbar“ und 1 „kaum“, auf denselben 96 Instanzen wie mit Drehung 25 und 1, mit Drehung 16 und 2; es fehlen „kaum“-Zellen für ein Regime ohne Preis | `test_claim_preis_nach_gruppen` |
| Was kostet die Entladereihenfolge? | Δ_L = (Kosten L − Kosten U) / Kosten U: ohne Drehung im Mittel 1,8 % (Median 1,1 %, 192 Instanzen), auf denselben 96 Instanzen wie mit Drehung 1,7 % (Median 1,2 %); mit Drehung 1,2 % (Median 0,5 %, 96 Instanzen); Zellen „spürbar“ / „kaum“ (Schwellen: Δ_L im Mittel ≥ 1 % und bei mindestens der Hälfte der Instanzen ≥ 0,5 % bzw. unter 0,3 %) ohne Drehung 20 / 2 (auf den 96 Instanzen 20 / 1), mit Drehung 12 / 8 (von 32); ein Zusatz, kein Aufhänger | `test_claim_preis_der_reihenfolge` |
| Reparatur oder Suche? | Lücke der Reparatur zur Suche (U): roh im Mittel 13,7 %, mit lokaler Suche 2,7 % (Median 1,5 %), höchstens 1 % in 90 von 192 Instanzen; mit Drehung 10,4 % und 2,2 % (Median 0,5 %), 49 von 96. Die Suche startet aus der Reparatur: die Lücke der Reparatur ist nie negativ (0 von 192 Instanzen ohne, 0 von 96 mit Drehung); die Faustregel liegt in 8 von 168 Instanzen ohne Drehung und in 3 von 96 mit Drehung unter der Suche, die Suche ist nicht optimal | `test_claim_reparatur_gegen_suche` |
| Faustregel θ? | Größtes θ mit lauter packbaren Touren (U): ohne Drehung θ = 0,9 in 100 von 192 Instanzen, 0,8 in 38, 0,7 in 30, keine Regel in 24; Mehrkosten gegen die Suche im Mittel 4,8 % (Median 3,3 %, 168 Instanzen mit Regel). Mit Drehung (96 Instanzen): 80, 11, 5 und keine Regel in 0; Mehrkosten 4,8 % (Median 4,9 %). Auf denselben 96 Instanzen ohne Drehung: θ = 0,9 in 45, keine Regel in 14 | `test_claim_faustregel` |
| Ist die Suche gut? | Kontrolle gegen das exakte Verfahren bei n = 8, k = 2, φ = 0,85 und 0,95 (40 Instanzen): mittlere Lücke ohne und mit Drehung je 0,000 %, nie unter dem Optimum; die Flächenlösung liegt dort 17,2 % (ohne Drehung) bzw. 8,5 % (mit Drehung) unter dem Optimum (Basis: das Optimum). Bei 40 Kunden ist ein Lauf mit 2 000 statt 400 Iterationen, größerem CP-SAT-Budget und Start aus der kürzeren Suche im Mittel 0,36 % billiger (24 Instanzen ohne Drehung, 3 über 2 %) bzw. 0,57 % (8 Instanzen mit Drehung, 1 über 2 %); ein kalt gestarteter Lauf mit demselben Budget unterbot diese Suche in 4 von 8 Instanzen ohne Drehung (bis 5,25 %) und in 5 von 8 mit Drehung (bis 1,30 %). Bei 20 Kunden senkt ein größeres Budget (Nachmessung, 32 Instanzen, ohne Drehung) die Kosten im Mittel um 0,42 % (bei 23 Instanzen unverändert, bei 8 um mehr als 0,5 %), und die Live-Suche (100 Iterationen, 10 Instanzen) lag im Mittel 1,30 % (ohne Drehung; größte Einsparung 8,54 %) bzw. 0,78 % (mit Drehung) unter der gespeicherten Suche mit 400 Iterationen. Die Suche ist also weder optimal noch gegen Start und Budget stabil | `test_claim_guete_der_suche` |
| Wie viel verpasst die Heuristik? | Touren mit exaktem Status (40 Kunden, 3 Ladungen, φ = 0,90, Depot Mitte: 30 Instanzen mit je 12 Zufallstouren, Zielfüllgrad gleichverteilt von 0,55 bis 1,0; 360 Touren je Beladung): „Heuristik nein, exakt ja“ ohne Drehung U 45 von 316 (14,2 %) und L 64 von 301 (21,3 %), bei Füllgrad ab 0,9 U 36 von 55 (65 %); mit Drehung U 42 von 330 (12,7 %) und L 41 von 305 (13,4 %), bei Füllgrad ab 0,9 U 42 von 69 (61 %); unter Füllgrad 0,8 U 0 von 164 (ohne Drehung). Die Suche nutzt zusätzlich CP-SAT; ihre Kosten bleiben Obergrenzen der Kosten der besten packbaren Lösung | `test_claim_heuristik_gegen_exakt` |
| Wie oft bleibt es „unbekannt“? | Touren der Frage 1 mit Status „unbekannt“: 66 von 3 739 ohne Drehung, 151 von 3 739 mit Drehung; CP-SAT-Aufrufe der Suche je Instanz im Mittel 1 075, davon 28 unbekannt (ohne Drehung, 96 Instanzen), 535 und 42 (mit Drehung) | `test_claim_unbekannt` |
| Hält das für andere Teile und Ladeflächen? | Rangkorrelation zwischen erwarteten Teilen je Fahrzeug und Preis über 12 Zellen je Form (1 und 3 Rechtecke je Kunde, Depot Rand, φ = 0,90, 64 Instanzen; die Zahl der Zellen steht im Bericht der Messreihe, nicht im Test): ohne Drehung −0,95 (gleich) und −0,91 (gemischt), mit Drehung −0,77 und −0,72; andere Ladeflächen (lang 25 × 160, kompakt 50 × 80 bei gleicher Fläche; Palettenfall: Rechtecke fest 19 × 28, Maße als Entwurfsannahme): in allen drei Layouts „reicht“- und „reicht oft nicht“-Zellen; das Kipp-θ weicht höchstens 0,10 von dem der Ladefläche 40 × 100 ab (Depot Rand, 12 Instanzen je Zelle, die anderen Layouts 6) bei lang in 8 (ohne Drehung) bzw. 4 (mit Drehung) von 8 Gruppen, bei kompakt in 6 bzw. 7 von 8; darunter sind ohne Drehung 2 und 1, mit Drehung 2 und 6 Gruppen, in denen beide „nie im Raster“ haben. Mit Drehung ist die Lage der Grenze bei langer Ladefläche nicht übertragbar | `test_claim_robustheit` |
| Windows gegen Linux? | Messreihe: 12 von 12 Zeilen mit denselben Kosten (ohne Drehung wie mit); CP-SAT-Status in 100 % (ohne Drehung) bzw. 99,4 % (mit Drehung) von 480 Prüfungen gleich, nie ein Wechsel zwischen packbar und nicht packbar | `test_claim_plattform` |
| Wie lange rechnet das? | Messreihe (lokal, Wanduhr, unter Last, auf Streamlit Cloud nicht gemessen): Fläche mit Prüfung plus Reparatur bei 40 Kunden (10 Instanzen, Form gemischt, Depot Rand) im Mittel 6,9 s, größter Wert 13,0 s (mit Drehung; 13,5 s und 31,3 s ohne Drehung unter fremder Last); die vollständige Suche je Instanz im Mittel 148 s ohne und 452 s mit Drehung (auf denselben 96 Instanzen; beide Läufe liefen nicht unter gleicher Last, der Faktor ist ein Anhalt). In der App (Prüflauf beim Bau, nicht im Test; drei Konfigurationen mit 40 Kunden, lokal, ein Prozess, unter Last): Flächenlösung mit Statusprüfung 2,6 bis 11,8 s, Reparatur und Faustregel auf Knopfdruck 9,6 bis 26,7 s; Live-Suche bei 20 Kunden (Knopf, Prüflauf beim Bau, nicht im Test): lokal gemessen etwa 30 bis 80 Sekunden ohne und 90 bis 105 Sekunden mit Drehung (Wanduhr, unter Last, acht Läufe) | `test_claim_rechenzeit` |

## Befunde und Korrekturen

- **Die Drehung ändert die Hauptaussage.** Die vorab festgelegte Regel für die Frage 1 war in der ersten Messreihe (ohne Drehung) erfüllt (25 „reicht“-, 27 „reicht oft nicht“-Zellen); mit Drehung ist sie nur teilweise erfüllt (35 und 10 Zellen, kein Faktor mit mindestens 60 % „reicht oft nicht“-Zellen; zählt man „unbekannt“ als Problem mit, sind es mit Drehung 18 statt 10 Zellen, ohne Drehung 30 statt 27). Die Aussage „Bei θ = 0,90 reicht die Fläche in 9 von 16 Zellen oft nicht“ gilt nur ohne Drehung (mit Drehung mindestens 3 von 16).
- **Der Preis fällt mit der Drehung, aber er verschwindet nicht:** 9,6 % gegen 3,9 % im Mittel auf denselben 96 Instanzen; bei 20 Kunden und 5 Ladungen bleibt er mit 9,8 % (Form gleich) und 6,5 % (gemischt) groß. Die Kosten der Suche sind Obergrenzen der Kosten der besten packbaren Lösung (CP-SAT mit Budget, „unbekannt“ zählt als nicht packbar), mit Drehung noch stärker (mehr unbekannte Aufrufe); ein Preis ist der Quotient zweier Näherungen und kein garantierter Höchstwert.
- **„Teile je Fahrzeug“ ist keine gesicherte Ursache.** Die Rangkorrelation fällt mit Drehung von −0,95 auf −0,77 (gleich); die Größe hängt in diesem Generator an (n, k) und ist mit k und φ vermischt. Der Regler heißt deshalb (n, k), die Zahl der Teile steht als Erwartungswert dabei.
- **Das Preset „Reihenfolge kostet“** brauchte einen anderen Zufalls-Seed als zuerst gefunden: der erste Treffer der Stufe 1 (740000) erfüllte das Kriterium mit Suche (mindestens 1 % Preis der Reihenfolge ohne Drehung) nicht (Δ_L 0,3 %); der kleinste Seed, der beide Stufen erfüllt, ist 740005.
- **Nachträge der Messreihen** (in `ERGEBNIS.md` der Messreihen offengelegt, hier genannt): die Schwellen der Frage 1 wurden nach einer Erkundung gesetzt; der erste Lauf der Frage 2 (zu langsam) wurde abgebrochen und mit 6 statt 8 Instanzen je Zelle und kleinerem CP-SAT-Budget neu gerechnet; mit Drehung wurden die Fragen 2 und 3 auf 96 statt 192 Instanzen und die Güte bei 40 Kunden auf 8 statt 24 Instanzen gekürzt (Zeitgründe, vorab festgelegt); die Zeit für den Status einer Tour lief mit 1,0 statt der vorab genannten 2,0 deterministischen Zeit.

## Ehrliche Grenzen

- **Zufallsinstanzen eines Generators, keine Praxisdaten:** Ladefläche 40 × 100, 1 bis 3 Rechtecke je Kunde, zwei Formen, Orte gleichverteilt, n ≤ 40, Drehung nur um 90°. Praxis-Mengen, andere Winkel, 3D, Zeitfenster, Flottenmix und begrenzte Fahrzeugzahl sind nicht gemessen.
- **Die Kosten der Suche sind Obergrenzen der Kosten der besten packbaren Lösung, ein Preis ist kein garantierter Höchstwert.** Die Suche nutzt Heuristik und CP-SAT mit Zeitgrenze und zählt „unbekannt“ als nicht packbar; bei Füllgrad ab 0,9 sagt die Heuristik allein bei 36 von 55 Touren mit bekanntem Status (U, ohne Drehung, Zufallstouren) „nicht packbar“, obwohl sie exakt packbar sind (Tabelle oben). Der Preis ist ein Quotient zweier Näherungen: Die Faustregel liegt in 8 von 168 Instanzen unter der Suche, die kurze Live-Suche war bei 20 Kunden im Mittel 1,3 % billiger als die gespeicherte, und bei 40 Kunden ist nur die Lücke zwischen kurzer und fünffach längerer Suche gemessen (a); ein kalter Lauf lag dabei in 4 von 8 (ohne Drehung) bzw. 5 von 8 Proben (mit Drehung) unter der längeren Suche (bis 5,25 %): die Güte bei 40 Kunden ist nicht gesichert.
- **Kein exaktes Verfahren bei 20 und 40 Kunden:** die Suche ist nur bei n = 8 gegen ein Orakel geprüft.
- **Basis der Preise ist die Flächenlösung bei θ = 1,00**, die selbst nicht packbar ist; die Faustregel ist der Vergleich, den ein Planer anwenden würde.
- **Die Konstruktion sichert Monotonien:** Fläche ≤ U ≤ L und Suche ≤ Reparatur gelten durch die Warmstarts (Kosten L unter U: 0 Instanzen, Kosten U unter der Fläche: 0 Instanzen); das sind keine Befunde. Reparatur und Suche hatten nicht denselben Rechenaufwand.
- **Die Entladereihenfolge ist eine vereinfachte Fassung**, aus Zusammenfassungen rekonstruiert; die Literatur wurde nicht gelesen, nur Zusammenfassungen. Es gibt keinen Zahlenvergleich mit der 2L-CVRP-Literatur.
- **Zellen mit wenigen Instanzen:** 12 Instanzen je Zelle in der Frage 1, 3 bis 6 in den Fragen 2 und 3; Zellenanteile haben grobe Schritte, einzelne Abweichungen sind zu erwarten; die Schwellen der Meldungen sind gesetzt, nicht hergeleitet.
- **Der unabhängige Prüfer findet nicht in jedem Fall eine Packung:** mit Drehung bestehen 5 von 96 Lösungen der Frage 2 ihn nicht („unbekannt“ in seiner Zeitgrenze), dazu 2 von 64 in der Kontrolle der Teile je Kunde (ohne wie mit Drehung) und 1 von 8 beim kalten Lauf; in den 6 Fällen mit gespeicherter Tour fand CP-SAT mit mehr Zeit eine bestätigte Packung, die 2 Fälle der Kontrolle mit Drehung sind nicht nachgeprüft.
- **Plattform:** Neu-Rechnen ist ein Band, kein bitgleicher Vergleich: der CP-SAT-Status kann zwischen Windows und Linux zwischen „packbar“ und „unbekannt“ wechseln (3 von 480 Prüfungen mit Drehung).
- **Rechenzeit auf Streamlit Cloud nicht gemessen**; die Zeiten oben sind lokal (Wanduhr, unter Last), die Läufe ohne und mit Drehung nicht unter gleicher Last.

## Verifikation

- **Orakel** (`tests/test_oracle_packrouten.py`): Packbarkeit gegen eine vollständige Aufzählung (Normalmuster) für bis zu fünf Rechtecke, ohne und mit Drehung; Routen gegen die Aufzählung aller Zerlegungen und Reihenfolgen auf einer Hand-Instanz mit fünf Kunden; die Suche gegen das exakte Verfahren bei n = 8 (nie unter dem Optimum).
- **Packbarkeit** (`tests/test_pack.py`): Handbeispiele von Hand nachgerechnet (perfekte Packung, zwei 25 × 60 trotz passender Fläche nicht packbar, das Beispiel mit drei Kunden und Entladereihenfolge, drei 30 × 35 nur mit Drehung), Prüfer mit Orientierung, Monotonie (ohne Drehung packbar heißt mit Drehung packbar), jede gefundene Packung besteht den Prüfer.
- **Kern** (`tests/test_core.py`): Instanzen, Flächenlösung, Reparatur, Suche, Faustregel, Randfälle (ein und zwei Kunden), Zweig (Preset „Wenige große Teile“ zeigt nicht packbare Touren).
- **Ergebnisdatei und Aussagen:** `tests/test_results.py` (Aufbau, Schwellen der Urteile, gespeicherte Lösungen gegen die Kosten ihrer Routen) und `tests/test_claims.py` (die Zahlen der Befundtabelle, die Testzahl, die Tabelle „Wo die Annahmen enden“ gleich der der App).
- **Presets:** Geschichte jedes Presets an künstlichen Werten, an der Neuberechnung und an der gespeicherten Suche (`tests/test_presets.py`).
- **Verdikte:** reine Funktionen, an Schwellen und handgesetzten Zellen (`tests/test_verdicts.py`).
- **Oberfläche:** AppTest (jeder Regler, jedes Preset, Drehung, Permalink, Live-Suche), Layout, PDF, Footer, Laufzeit-Importe.
- **Plattform:** Neu-Rechnen als Band (`tests/test_reproduktion.py`: Fläche exakt, Reparatur 3 %, kein Statuswechsel zwischen packbar und nicht packbar bei mehr Zeit); Linux-CI-Simulation mit Docker vor dem Push.
- Die Suite hat 199 Tests.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App |
| `data/prt_results.json` | Aggregate der Messreihen und gespeicherte Lösungen (unter 300 kB) |
| `modul_frisch.py` | lädt geänderte Hilfsmodule nach einem Update neu (Standard neuer Demos; sonst bräuchte die Cloud einen Neustart) |
| `prt_constants.py` | Regler-Stufen, Schwellen der Meldungen, Farben, Presets |
| `prt_core.py` | Instanzen, Packer mit Zwischenspeicher, Fläche, Reparatur, Suche, Prüfer, Orakel |
| `prt_evaluation.py` | Kennzahlen und Verdikte (reine Funktionen), Zahlenformat |
| `prt_layout.py` | Fester Kopf (Stylesheet) |
| `prt_live.py` | Live-Rechnung mit Zwischenspeicher |
| `prt_pack.py` | Packbarkeit ohne und mit Drehung, Prüfer, Teil-Packung für die Zeichnung |
| `prt_pdf_export.py` | Tourenplan als PDF |
| `prt_presets.py` | Permalink (auf Stufen einrasten), Presets, Hervorhebung, Zufalls-Seed-Knopf |
| `prt_results.py` | Laden und Auswerten der Ergebnisdatei |
| `prt_rng.py` | SplitMix64 (Ganzzahlen, plattformfest) |
| `prt_stories.py` | Kriterien der Presets |
| `prt_texts.py` | Feste Texte (Annahmen, Formeln, Verfahren) |
| `prt_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `requirements-dev.txt`, `requirements.txt` | Laufzeit (streamlit, pandas, plotly, ortools, fpdf2) und pytest |
| `tools/` | `dump_results.py`, `find_preset_seeds.py`, `preset_suche.py`, `preset_suche*.json`, `PRESET_SWEEP.md` |
| `tests/` | Orakel, Packbarkeit, Kern, Ergebnisse, Presets, Verdikte, Aussagen, Layout, AppTest, PDF, Footer, Laufzeit-Importe |

## Bewusst nicht umgesetzt

- Andere Drehwinkel als 90°, 3D-Packung (`pack-demo`), Zeitfenster, Flottenmix, begrenzte Fahrzeugzahl, mehr als 40 Kunden, Praxisinstanzen.
- Die Ladefläche als Regler (mit Drehung ist die Lage der Grenze bei langer Ladefläche nicht übertragbar; die drei gemessenen Layouts stehen als Angabe im Reiter „Messreihe“, nicht als Regler).
- Ein Vergleich mit dem Routing von OR-Tools (es kennt keine Packbarkeit je Tour) und ein Zahlenvergleich mit der Literatur.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, pandas, OR-Tools (CP-SAT) und fpdf2.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [Tourenplanung optimieren](https://sebastianhanisch.net/tourenplanung-optimierung.html).
