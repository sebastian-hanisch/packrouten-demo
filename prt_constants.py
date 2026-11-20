"""Konstanten: Regler-Stufen, feste Annahmen, Schwellen der Meldungen, Farben und Presets."""

# --- Regler: nur gemessene Stufen (die Zellen der Messreihen)
N_CHOICES = (20, 40)
K_CHOICES = (3, 5)
SPREAD_CHOICES = ("gleich", "gemischt")
PHI_CHOICES = (0.75, 0.90)
DEPOT_CHOICES = ("rand", "mitte")
THETA_CHOICES = (0.70, 0.80, 0.90, 1.00)
THETA_PCT_CHOICES = (70, 80, 90, 100)     # der Regler ist ein Schieberegler in Prozent der Ladefläche: θ = Prozent / 100
DEFAULT_N, DEFAULT_K, DEFAULT_SPREAD, DEFAULT_PHI, DEFAULT_DEPOT, DEFAULT_THETA = 20, 3, "gemischt", 0.90, "mitte", 0.90
DEFAULT_ROT = False                       # Standard-Stellung des Schalters „Rechtecke drehen“: aus (strengerer Praxisfall, mehr Instanzen vorgerechnet)
SEED_MAX = 999999
DEFAULT_SEED = 740000
OWN_SEED_MAX = 299                        # „Neue Instanz“ würfelt einen Zufalls-Seed aus 0 bis 299 (kein Seed der Messreihen)
MESSREIHE_SEEDS = tuple(range(610000, 610006))   # Instanzen der Messreihe M2 (Suche gespeichert)

LIVE_DET_N40 = 0.3                        # CP-SAT-Zeit (deterministisch) je Tour für den Status bei 40 Kunden live (die Messreihe mit Drehung: 1,0): mehr Touren bleiben „unbekannt“
LIVE_L_MAX_N = 20                         # der Status mit Entladereihenfolge wird live nur bis 20 Kunden geprüft
LIVE_SEARCH_MAX_N = 20                    # der Knopf „Suche starten“ rechnet nur bis 20 Kunden
LIVE_SEARCH_ITERS = 100                   # kleines Budget der Live-Suche (Messreihe (d), Teil v: 100 Iterationen, CP-SAT-Zeit 2)
LIVE_SEARCH_DET_MAX = 2.0
LIVE_SUCHE_ZEIT = "lokal gemessen etwa 30 bis 80 Sekunden ohne und 90 bis 105 Sekunden mit Drehung (Wanduhr, unter Last, acht Läufe bei 20 Kunden), auf Streamlit Cloud nicht gemessen"

# --- Ladefläche und Kosten (siehe prt_pack, prt_core)
W, LEN = 40, 100
AREA = W * LEN
F_FIX = 250                               # Fixkosten je Fahrzeug in Entfernungseinheiten = 25 Längeneinheiten
SCALE = 10

# --- Schwellen der Meldungen (gesetzt, nicht hergeleitet; Messplan Abschnitt 5)
M1_NIE = 0.10                             # Zelle „nie“: höchstens 10 % der Instanzen mit einer nicht packbaren oder unbekannten Tour
M1_OFT = 0.50                             # Zelle „oft“: mindestens die Hälfte der Instanzen mit einer nachweislich nicht packbaren Tour
M2_REL_MEAN, M2_REL_SHARE1 = 2.0, 0.5     # Packen „relevant“: mittleres Δ_U ≥ 2 % und bei mindestens der Hälfte der Instanzen ≥ 1 %
M2_NON_MEAN = 0.5                         # „nicht relevant“: mittleres Δ_U < 0,5 %
M3_REL_MEAN, M3_REL_SHARE05 = 1.0, 0.5    # Reihenfolge „relevant“: mittleres Δ_L ≥ 1 % und bei mindestens der Hälfte ≥ 0,5 %
M3_NON_MEAN = 0.3
M4_OK_REP, M4_BAD_REP = 1.0, 3.0          # Reparatur reicht: Lücke ≤ 1 %; reicht nicht: ≥ 3 % oder mindestens 0,3 Fahrzeuge mehr
M4_OK_DV, M4_BAD_DV = 0.1, 0.3

FILL_BINS = ((0.0, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.85), (0.85, 0.9), (0.9, 0.95), (0.95, 1.01))

# --- Farben
COLOR_OK = "#2F6B65"
COLOR_BAD = "#B5493A"
COLOR_UNKNOWN = "#C9A227"
COLOR_LINE = "#4c78a8"
COLOR_GREY = "rgba(150,150,150,0.55)"
CUSTOMER_COLORS = ("#4c78a8", "#f58518", "#54a24b", "#b279a2", "#e45756", "#72b7b2", "#eeca3b", "#9d755d", "#bab0ac", "#ff9da6")

# --- Presets: Zelle der Messreihe und Zufalls-Seed (Suche der Seeds: tools/find_preset_seeds.py, tools/PRESET_SWEEP.md)
PRESETS = {
    "Standard": {"n": 20, "k": 3, "spread": "gemischt", "phi": 0.90, "depot": "mitte", "theta": 0.90, "seed": 740000},
    "Wenige große Teile": {"n": 20, "k": 5, "spread": "gleich", "phi": 0.90, "depot": "rand", "theta": 0.90, "seed": 740000},
    "Viele kleine Teile": {"n": 40, "k": 3, "spread": "gemischt", "phi": 0.75, "depot": "mitte", "theta": 0.90, "seed": 740003},
    "Grenzfall bei voller Auslastung": {"n": 20, "k": 3, "spread": "gemischt", "phi": 0.90, "depot": "rand", "theta": 1.00, "seed": 740003},
    "Reihenfolge kostet": {"n": 20, "k": 5, "spread": "gemischt", "phi": 0.90, "depot": "mitte", "theta": 0.90, "seed": 740005},
}
PRESET_HELP = {
    "Standard": "Mittlere Teile (20 Kunden, 3 Ladungen, gemischte Formen): bei θ = 0,90 sind alle Touren der Flächenlösung auch ohne Drehung packbar.",
    "Wenige große Teile": "20 Kunden, 5 Ladungen, ähnlich große, ungefähr quadratische Teile (Depot am Rand): bei θ = 0,90 und auch bei θ = 0,80 ist mindestens eine Tour der Flächenlösung selbst mit Drehung nachweislich nicht packbar; der Preis des Packens ist in dieser Instanz groß (mindestens 10 % ohne, mindestens 3 % mit Drehung).",
    "Viele kleine Teile": "40 Kunden, 3 Ladungen, gemischte Formen, Fläche zu 75 % gefüllt: bei θ = 0,90 sind alle Touren der Flächenlösung ohne Drehung packbar, ihre Kosten liegen höchstens 0,5 % über denen bei θ = 1,00, und der Preis des Packens ist höchstens 2 % (ohne und mit Drehung). Die Suche ist gespeichert (n = 40).",
    "Grenzfall bei voller Auslastung": "20 Kunden, 3 Ladungen, Depot am Rand: bei θ = 0,90 sind alle Touren der Flächenlösung ohne Drehung packbar, bei θ = 1,00 (volle Fläche) ist mindestens eine Tour selbst mit Drehung nachweislich nicht packbar. Der Name meint diese Instanz, nicht die Zellenklasse der Messreihe: ohne Drehung meldet die App für die Zelle dieser Einstellung „Fläche reicht oft nicht“.",
    "Reihenfolge kostet": "20 Kunden, 5 Ladungen, gemischte Formen: bei θ = 0,90 ist mindestens eine Tour der Flächenlösung ohne Reihenfolge packbar (ohne Drehung), mit Entladereihenfolge selbst mit Drehung nachweislich nicht; die Suche mit Entladereihenfolge kostet ohne Drehung mindestens 1 % mehr als die ohne.",
}
