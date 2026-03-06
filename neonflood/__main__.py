"""
neonflood/__main__.py
Allows running the package directly:
    python -m neonflood           → launches GUI
    python -m neonflood -u URL    → runs CLI
"""

from neonflood.cli import main

if __name__ == "__main__":
    main()
