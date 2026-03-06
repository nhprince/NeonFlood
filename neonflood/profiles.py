"""
neonflood/profiles.py
=====================
Named profile save/load system for NeonFlood.

Profiles are stored as JSON files in ~/.neonflood/profiles/<name>.json.
They persist between sessions and can be loaded back into the GUI or CLI.

Functions
---------
save_profile(name, config)  — write a config dict as a named profile
load_profile(name)          — read a profile by name; returns dict or None
list_profiles()             — return list of saved profile names
delete_profile(name)        — remove a profile file
default_config()            — return a fresh default config dict
"""

import json
from pathlib import Path


PROFILE_DIR = Path.home() / ".neonflood" / "profiles"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(name):
    """Sanitise a profile name into a valid filename stem."""
    return name.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")


def save_profile(name, config: dict) -> str:
    """
    Save a configuration dict as a named profile.

    Parameters
    ----------
    name   : str  — human-readable profile name (spaces allowed)
    config : dict — configuration values to store

    Returns
    -------
    str — path to the saved JSON file
    """
    path = PROFILE_DIR / f"{_safe_name(name)}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    return str(path)


def load_profile(name) -> dict | None:
    """
    Load a saved profile by name.

    Parameters
    ----------
    name : str — profile name (as returned by list_profiles)

    Returns
    -------
    dict if the profile exists, None otherwise.
    """
    path = PROFILE_DIR / f"{_safe_name(name)}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_profiles() -> list:
    """
    Return a sorted list of saved profile names (without .json extension).

    Returns
    -------
    list[str]
    """
    return [p.stem for p in sorted(PROFILE_DIR.glob("*.json"))]


def delete_profile(name) -> bool:
    """
    Delete a profile by name.

    Parameters
    ----------
    name : str — profile name to delete

    Returns
    -------
    bool — True if deleted, False if not found
    """
    path = PROFILE_DIR / f"{_safe_name(name)}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def default_config() -> dict:
    """
    Return a fresh default configuration dictionary.

    Keys match the fields used by the GUI and CLI.

    Returns
    -------
    dict
    """
    return {
        "target":     "http://",
        "mode":       "get",
        "workers":    5,
        "sockets":    50,
        "timeout":    5,
        "proxy":      "",
        "rate_limit": 0,
    }
