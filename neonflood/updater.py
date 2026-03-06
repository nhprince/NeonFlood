"""
neonflood/updater.py
====================
Checks the GitHub Releases API for a newer version of NeonFlood.

The check is performed in a background thread so it never blocks startup.
If a newer tag is found the GUI shows an update badge; in CLI mode a line
is printed to the console.

Functions
---------
check_for_update(timeout)  — returns (has_update, latest_version, release_url)
"""

import urllib.request
import json

from neonflood import __version__


GITHUB_API_URL = "https://api.github.com/repos/nhprince/NeonFlood/releases/latest"


def _parse_version(version_str: str) -> tuple:
    """
    Parse a semantic version string into a comparable tuple of ints.

    Accepts strings with or without a leading 'v' (e.g. "v2.1.0" or "2.1.0").

    Parameters
    ----------
    version_str : str — version string to parse

    Returns
    -------
    tuple[int, ...] — e.g. (2, 1, 0)
    """
    cleaned = version_str.strip().lstrip("v")
    try:
        return tuple(int(x) for x in cleaned.split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def check_for_update(timeout: int = 4) -> tuple:
    """
    Query the GitHub Releases API and compare with the running version.

    Performs a single HTTP GET to the GitHub API with a 4-second timeout.
    Any network or parsing error is silently caught and treated as
    "no update available" so the tool always starts cleanly.

    Parameters
    ----------
    timeout : int — HTTP request timeout in seconds (default: 4)

    Returns
    -------
    tuple[bool, str, str]
        (has_update, latest_version_string, release_html_url)

        has_update          — True if a newer version exists on GitHub
        latest_version_string — e.g. "2.1.0" (current version if no update)
        release_html_url    — URL to the GitHub release page, or "" on error
    """
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"User-Agent": f"NeonFlood-UpdateChecker/{__version__}"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data      = json.loads(resp.read().decode("utf-8"))
            tag       = data.get("tag_name", __version__)
            html_url  = data.get("html_url", "https://github.com/nhprince/NeonFlood")
            has_new   = _parse_version(tag) > _parse_version(__version__)
            return has_new, tag.lstrip("v"), html_url

    except Exception:
        # Network unavailable, rate-limited, or repo not yet public — fail silently
        return False, __version__, ""
