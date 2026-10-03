#!/usr/bin/env python3
import sys
from pathlib import Path

value = float(sys.argv[1])
if not 0 <= value <= 10:
    raise SystemExit("Latency must be between zero and ten seconds")
path = Path(".env")
lines = [line for line in path.read_text().splitlines() if not line.startswith("LAB_LATENCY_SECONDS=")]
path.write_text("\n".join(lines) + f"\nLAB_LATENCY_SECONDS={value}\n")
path.chmod(0o600)
