"""Two gateway restart and two client Wi-Fi reconnect cycles on physical ESP32."""
import datetime
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('measure',ROOT/'scripts/measure-board.py')
measure=importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)


def wsl(command):
    p=subprocess.run(['wsl','-d','Ubuntu','--','bash','-lc',
        'cd /mnt/d/TrustGate-IoT; '+command],capture_output=True,text=True,timeout=60)
    if p.returncode:
        raise RuntimeError(p.stdout+p.stderr)


def recover(board):
    start=time.monotonic()
    for attempt in range(8):
        lines=board.query()
        assert not any('rst:' in x for x in lines), 'Unexpected board reset'
        if any('ACCEPT 192.0.2.10' in x for x in lines):
            return {'attempts':attempt+1,'observed_recovery_ms':round((time.monotonic()-start)*1000)}
        time.sleep(1)
    raise AssertionError('No accepted answer after recovery')


def main():
    sys.stdout.reconfigure(errors='replace')
    board=measure.Board()
    report={'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'tests':[], 'limits':['Client-requested Wi-Fi reconnect, not access-point power loss.',
            'Recovery timing includes USB polling and full TLS/DNS query; not link association time.',
            'Two cycles each, not a long-duration reliability test.']}
    try:
        board.ready()
        board.send('SLEEP 0'); board.read_until('SLEEP result=')
        for cycle in range(2):
            print(f'GATEWAY OUTAGE cycle={cycle+1}',flush=True)
            try:
                wsl('.venv/bin/python scripts/stop-lab.py')
                for _ in range(2):
                    lines=board.query()
                    assert any('BLOCK TLS connection or certificate failure' in x for x in lines)
                    assert not any('ACCEPT ' in x for x in lines)
            finally:
                wsl('bash scripts/start-lab.sh')
            result=recover(board)
            report['tests'].append({'test':'gateway restart','cycle':cycle+1,'status':'PASS',**result})
        for cycle in range(2):
            print(f'WIFI RECONNECT cycle={cycle+1}',flush=True)
            board.send('RECONNECT')
            lines=board.read_until('WIFI connected IP=',40)
            assert any('WIFI disconnected; queries paused' in x for x in lines), 'Disconnect not observed'
            assert not any('rst:' in x for x in lines), 'Unexpected board reset'
            result=recover(board)
            report['tests'].append({'test':'client Wi-Fi reconnect','cycle':cycle+1,'status':'PASS',**result})
        (ROOT/'results/esp32-recovery-tests.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2),flush=True)
    finally:
        board.close()


if __name__=='__main__':
    main()
