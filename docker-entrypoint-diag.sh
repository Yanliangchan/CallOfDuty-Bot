#!/usr/bin/env bash
# Temporary diagnostic entrypoint: proves exactly where startup gets stuck
# (DNS resolution, TCP connect, alembic, or bot.py) instead of hanging
# silently. Remove once the underlying issue is confirmed and fixed.
set -x

echo "DIAG: container started at $(date -u)"
echo "DIAG: whoami=$(whoami) pwd=$(pwd)"

python3 - <<'PYEOF'
import os
import socket
import sys

url = os.environ.get("DATABASE_URL", "")
print(f"DIAG: DATABASE_URL scheme/host preview: {url.split('@')[-1] if '@' in url else '(no @ found)'}", flush=True)

try:
    hostport = url.split("@", 1)[1].split("/", 1)[0]
    host, _, port = hostport.partition(":")
    port = int(port or 5432)
except Exception as exc:
    print(f"DIAG: failed to parse host/port from DATABASE_URL: {exc}", flush=True)
    sys.exit(0)

print(f"DIAG: resolving host={host!r}", flush=True)
try:
    infos = socket.getaddrinfo(host, port)
    print(f"DIAG: DNS resolved to: {infos}", flush=True)
except Exception as exc:
    print(f"DIAG: DNS resolution FAILED: {exc}", flush=True)
    sys.exit(0)

print(f"DIAG: attempting raw TCP connect to {host}:{port} with 15s timeout", flush=True)
try:
    s = socket.create_connection((host, port), timeout=15)
    print("DIAG: raw TCP connect SUCCEEDED", flush=True)
    s.close()
except Exception as exc:
    print(f"DIAG: raw TCP connect FAILED/TIMED OUT: {exc}", flush=True)
PYEOF
echo "DIAG: python diagnostic block exit=$?"

alembic upgrade head
echo "DIAG: alembic exit=$?"

python bot.py
echo "DIAG: bot.py exit=$?"
