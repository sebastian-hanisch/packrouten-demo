"""Gemeinsame Einrichtung: Modulpfad und kleine Instanzen."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import prt_core as C  # noqa: E402


@pytest.fixture(scope="session")
def inst20():
    """Eine Instanz mit 20 Kunden (Preset „Standard“: Mitte, 3 Ladungen, gemischt, φ = 0,90)."""
    return C.make_instance(20, "mitte", 740000, 3, 0.90, "gemischt")


@pytest.fixture(scope="session")
def inst8():
    """Kleine Instanz für die Orakel (n = 8, 2 Ladungen)."""
    return C.make_instance(8, "mitte", 605001, 2, 0.95, "gemischt")
