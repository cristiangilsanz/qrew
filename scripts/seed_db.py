#!/usr/bin/env python3
"""Entry point for the fixture loader. The seeder itself lives in scripts/seed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from seed.__main__ import main

if __name__ == "__main__":
    main()
