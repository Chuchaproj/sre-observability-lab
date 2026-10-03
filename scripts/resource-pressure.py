#!/usr/bin/env python3
import time

# Pressure is confined by Compose to 64 MiB and 0.25 CPU; no host disk writes.
buffer = bytearray(48 * 1024 * 1024)
deadline = time.monotonic() + 120
while time.monotonic() < deadline:
    for offset in range(0, len(buffer), 4096):
        buffer[offset] = (buffer[offset] + 1) % 256
