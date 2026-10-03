#!/usr/bin/env python3
import os
import time

import psycopg

connections = []
try:
    controller = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)
    connections.append(controller)
    controller.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name = 'lab-backend'")
    for _ in range(35):
        try:
            connections.append(psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=2))
        except psycopg.OperationalError:
            break
    print(f"Held {len(connections)} connections for at most 120s", flush=True)
    time.sleep(120)
finally:
    for connection in connections:
        connection.close()
