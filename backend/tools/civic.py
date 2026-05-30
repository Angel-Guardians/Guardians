"""Civic-data tools (grounded lookups over local open-data snapshots).

`find_cool_space` answers "where's the nearest air-conditioned public space?" from
data/cool_spaces.json (Toronto Heat Relief Network locations). It is a real
grounded lookup — haversine nearest-neighbour over a bundled dataset — not a model
guess. Swap the JSON for a live CKAN fetch later without touching the agents.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from backend.llm.base import ToolSpec

_DATA = Path(__file__).resolve().parents[2] / "data" / "cool_spaces.json"

# Eleanor's home (downtown Toronto) — default origin when none supplied.
_DEFAULT_LAT, _DEFAULT_LON = 43.6655, -79.3835


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_cool_space(lat: float = _DEFAULT_LAT, lon: float = _DEFAULT_LON) -> dict[str, Any]:
    """Return the nearest open cool space to a coordinate."""
    try:
        spaces = json.loads(_DATA.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"tool": "find_cool_space", "error": "cool_spaces dataset not found"}

    best, best_km = None, float("inf")
    for s in spaces:
        km = _haversine_km(lat, lon, s["lat"], s["lon"])
        if km < best_km:
            best, best_km = s, km
    if best is None:
        return {"tool": "find_cool_space", "error": "no cool spaces in dataset"}
    return {
        "tool": "find_cool_space",
        "name": best.get("name"),
        "address": best.get("address"),
        "type": best.get("type"),
        "distance_km": round(best_km, 2),
        "source": "Toronto Heat Relief Network (open data)",
    }


def register(registry) -> None:
    registry.register(
        ToolSpec(
            name="find_cool_space",
            description="Find the nearest open air-conditioned public space (cooling centre, "
            "library, community centre) during a heat warning. Returns name, address, distance.",
            parameters={
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude of the patient."},
                    "lon": {"type": "number", "description": "Longitude of the patient."},
                },
            },
        ),
        find_cool_space,
    )
