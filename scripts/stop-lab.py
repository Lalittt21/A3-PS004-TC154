"""Stop only the lab processes identified by their PID and exact config argument."""
import os
from pathlib import Path
import signal
import time

root = Path('/mnt/d/TrustGate-IoT')
for name, config in [('named', 'dns-lab/named.conf'), ('unbound', 'gateway/unbound.conf')]:
    pidfile = root / 'results' / (name + '.pid')
    if not pidfile.exists():
        continue
    pid = int(pidfile.read_text().strip())
    proc = Path(f'/proc/{pid}/cmdline')
    if not proc.exists():
        continue
    args = proc.read_bytes().split(b'\0')
    if str(root / config).encode() not in args or Path(os.fsdecode(args[0])).name != name:
        raise RuntimeError(f'Refusing to stop unrelated PID {pid}')
    os.kill(pid, signal.SIGTERM)
    for _ in range(50):
        if not proc.exists():
            break
        time.sleep(0.1)
    else:
        raise RuntimeError(f'{name} did not stop')
    print(f'Stopped lab {name}')
