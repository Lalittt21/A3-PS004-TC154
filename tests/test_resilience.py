"""Real local socket failures, CLI exit codes, and recovery through the live gateway."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

root = Path(__file__).resolve().parents[1]
client = root / 'client/python/query.py'
results = []

def run(label, extra, expected):
    start = time.monotonic()
    p = subprocess.run([sys.executable, str(client), *extra], capture_output=True,
                       text=True, timeout=8)
    elapsed = time.monotonic() - start
    data = json.loads(p.stdout)
    assert p.returncode == expected, (label, p.returncode, data, p.stderr)
    assert data['accepted'] == (expected == 0), data
    results.append({'test': label, 'status': 'PASS', 'exit_code': p.returncode,
                    'elapsed_seconds': round(elapsed, 3), 'detail': data})

# Keep the selected port reserved but not listening so refusal is deterministic.
with socket.socket() as unavailable:
    unavailable.bind(('127.0.0.1', 0))
    run('Unavailable gateway refuses connection',
        ['--port', str(unavailable.getsockname()[1])], 1)

# Accept TCP but never respond to the TLS handshake.
with socket.socket() as stalled:
    stalled.bind(('127.0.0.1', 0))
    stalled.listen(1)
    stalled.settimeout(5)
    stop = threading.Event()
    def stall():
        try:
            conn, _ = stalled.accept()
            with conn:
                stop.wait(5)
        except OSError:
            pass
    worker = threading.Thread(target=stall, daemon=True)
    worker.start()
    try:
        run('Stalled TLS handshake times out',
            ['--port', str(stalled.getsockname()[1]), '--timeout', '0.5'], 1)
        assert results[-1]['elapsed_seconds'] < 5
    finally:
        stop.set()
        worker.join(6)

run('Wrong identity blocks without plaintext fallback', ['--gateway-name', 'wrong.test'], 1)
run('Unsigned domain blocked at CLI', ['sensor.unsigned.trustgate.test'], 2)
run('Tampered domain blocked at CLI', ['tampered.trustgate.test'], 2)
run('Invalid timeout rejected', ['--timeout', '-1'], 1)
run('Fresh request succeeds after failed requests', [], 0)
(root / 'results/resilience-tests.json').write_text(json.dumps(results, indent=2)+'\n')
print(json.dumps(results, indent=2))
