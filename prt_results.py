"""Laden und Auswerten von data/prt_results.json (Aggregate der Messreihen, gespeicherte Suche der M2-Instanzen und der Presets).

Die Datei erzeugt tools/dump_results.py aus den Rohdaten (nicht im Repo). Zustände: "aus" = ohne Drehung (Vormessung, 192 Instanzen je Frage), "an" = mit Drehung
(Messreihe Drehung; M1 192 Instanzen, M2 bis M5 96 Instanzen)."""

from __future__ import annotations

import json
import pathlib
from functools import lru_cache

import prt_constants as K

PATH = pathlib.Path(__file__).resolve().parent / "data" / "prt_results.json"


@lru_cache(maxsize=1)
def load():
    return json.loads(PATH.read_text(encoding="utf-8"))


def state(rot):
    return "an" if rot else "aus"


def block(rot, res=None):
    return (res or load())[state(rot)]


def m1_cell(rot, depot, n, k, spread, theta, res=None):
    """Zelle der Messreihe M1 (Depot × (n, k) × Form × θ); gemessen nur bei φ = 0,90."""
    for c in block(rot, res)["m1"]["zellen"]:
        if c["depot"] == depot and c["n"] == n and c["k"] == k and c["spread"] == spread and abs(c["theta"] - theta) < 1e-9:
            return c
    return None


def m2_cell(rot, depot, n, k, spread, phi, res=None):
    """Zelle der Messreihen M2 bis M4 (Depot × (n, k) × Form × φ)."""
    for c in block(rot, res)["m2_zellen"]:
        if c["depot"] == depot and c["n"] == n and c["k"] == k and c["spread"] == spread and abs(c["phi"] - phi) < 1e-9:
            return c
    return None


def instance_key(depot, n, k, spread, phi, seed):
    return f"{depot}|{n}|{k}|{spread}|{phi:.2f}|{seed}"


def stored_record(rot, depot, n, k, spread, phi, seed, res=None):
    """Gespeicherte Suche (Messreihe M2 oder Preset) dieser Instanz oder None."""
    return block(rot, res)["instanzen"].get(instance_key(depot, n, k, spread, phi, seed))


def kipp(rot, depot, n, k, spread, res=None):
    """Kleinstes θ des Rasters, ab dem die Zelle „oft“ ist (p_min ≥ 0,5); None = nie im Raster."""
    return block(rot, res)["kipp"].get("|".join(str(x) for x in (depot, n, k, spread)))


def kipp_gruppen(rot, res=None):
    """(Gruppen mit einem Kipp-θ im Raster, Gruppen insgesamt); Gruppe = Depot × (n, k) × Form (16)."""
    werte = list(block(rot, res)["kipp"].values())
    return sum(1 for v in werte if v is not None), len(werte)


def kipp_bereich(rot, n, k, res=None):
    """(kleinstes, größtes) Kipp-θ der Gruppen mit diesen n und k (Depots und Formen); Gruppen ohne Kipp-θ im Raster zählen nicht mit."""
    vs = [v for key, v in block(rot, res)["kipp"].items() if key.split("|")[1:3] == [str(n), str(k)] and v is not None]
    return (min(vs), max(vs)) if vs else (None, None)


def teile_je_fahrzeug(n, k):
    """Erwartungswert der Rechtecke je Fahrzeug: 1,8 Rechtecke je Kunde mal n / k Kunden je Fahrzeug (kein Messwert je Lösung)."""
    return 1.8 * n / k


def count_classes(cells):
    """(nie, oft, dazwischen) über Zellen der Messreihe M1."""
    nie = sum(1 for c in cells if c["pmax"] <= K.M1_NIE)
    oft = sum(1 for c in cells if c["pmin"] >= K.M1_OFT)
    return nie, oft, len(cells) - nie - oft


def count_unsicher(cells):
    """Zellen der Messreihe M1, in denen mindestens die Hälfte der Instanzen eine nicht packbare ODER unbekannte Tour hat (p_max ≥ 0,5): Obergrenze zu „reicht oft nicht“."""
    return sum(1 for c in cells if c["pmax"] >= K.M1_OFT)


def fill_share(rot, spread, res=None):
    """Anteil nachweislich nicht packbarer Touren je Füllgrad-Klasse: Liste von (lo, hi, N, Anteil oder None)."""
    out = []
    for b in block(rot, res)["m1"]["fuell"][spread]:
        out.append((b["lo"], b["hi"], b["N"], b["infeas"] / b["N"] if b["N"] else None))
    return out
