#!/usr/bin/env python3
"""Zero-install launcher: `python run_grove.py <args...>` without pip install.

It simply puts the bundled src/ layout on sys.path and delegates to the CLI.
"""

import os
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, SRC)

from grove.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
