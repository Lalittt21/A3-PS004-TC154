"""Windows hardware test. Temporarily replaces lab TLS config; restores in finally.

Run with ESP32 attached and no other COM8 monitor. No firmware changes required.
Private fixture keys remain in the Ubuntu user's private application directory.
"""
import datetime
import json
from pathlib import Path
import subprocess
import sys
import time
import serial

ROOT = Path(__file__).resolve().parents[1]
WSL_ROOT = '/mnt/d/TrustGate-IoT'


def wsl(command, check=True):
    result = subprocess.run(['wsl', '-d', 'Ubuntu', '--', 'bash', '-lc',
                             f'cd {WSL_ROOT}; {command}'],
                            capture_output=True, text=True, timeout=60)
    if check and result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result


def restart():
    wsl('.venv/bin/python scripts/stop-lab.py')
    # start-lab's final client query intentionally fails with negative fixtures.
    result = wsl('bash scripts/start-lab.sh', check=False)
    return result


def observe(port, label, duration):
    port.reset_input_buffer()
    lines = []
    end = time.monotonic() + duration
    last_time = 0
    clock_ready = False
    with (ROOT / 'results/esp32-certificate-tests.log').open('a', encoding='utf-8') as log:
        log.write(f'\n--- {label} ---\n')
        while time.monotonic() < end:
            if not clock_ready and time.monotonic() - last_time > 5:
                port.write(f'TIME {int(time.time())}\n'.encode())
                last_time = time.monotonic()
            line = port.readline().decode(errors='replace').strip()
            if line:
                if 'Time provisioned' in line:
                    clock_ready = True
                print(line, flush=True)
                log.write(line + '\n')
                log.flush()
                lines.append(line)
    return lines


def main():
    sys.stdout.reconfigure(errors='replace')
    config = ROOT / 'gateway/tls-local.conf'
    original = config.read_bytes()
    report = {'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'board': 'ESP32-D0WD-V3', 'tests': [],
              'limitations': ['Controlled lab certificate substitution, not on-network interception.',
                             'Socket timeouts are not certificate-verification evidence.',
                             'This is a functional test, not a reliability benchmark.']}
    wsl('bash scripts/prepare-certificate-tests.sh')
    home = wsl('printf %s "$HOME"').stdout.strip()
    with serial.Serial('COM8', 115200, timeout=0.5) as port:
        port.dtr = False
        port.rts = False
        try:
            print('BASELINE: genuine gateway', flush=True)
            baseline = observe(port, 'baseline', 90)
            assert any('ACCEPT 192.0.2.10' in x for x in baseline), 'Baseline failed'
            report['tests'].append({'test': 'Genuine gateway baseline', 'status': 'PASS'})
            for fixture, reason in [('untrusted', 'self-signed certificate'),
                                    ('wrong-host', 'Hostname mismatch')]:
                print(f'TEST: {fixture}', flush=True)
                base = f'{home}/.local/share/trustgate/certificate-tests/{fixture}'
                config.write_text(f'server:\n    tls-service-key: "{base}.key"\n'
                                  f'    tls-service-pem: "{base}.pem"\n')
                result = restart()
                # Prove a reachable TLS endpoint presents the intended bad cert.
                detail = result.stdout + result.stderr
                assert reason.lower() in detail.lower(), detail
                lines = observe(port, fixture, 45)
                failures = sum('BLOCK TLS connection or certificate failure' in x for x in lines)
                verification = sum('certificate verify failed' in x.lower() or '-0x2700' in x for x in lines)
                assert failures >= 2 and verification >= 1, 'No board certificate rejection evidence'
                assert not any('ACCEPT ' in x for x in lines), 'Board accepted a negative fixture'
                assert not any('rst:' in x for x in lines), 'Board reset during negative test'
                report['tests'].append({'test': fixture, 'status': 'PASS',
                    'certificate_control': reason, 'tls_blocked_attempts': failures,
                    'certificate_verification_errors': verification,
                    'socket_timeouts': sum('select() timeout' in x for x in lines)})
        finally:
            print('RESTORE: genuine gateway', flush=True)
            config.write_bytes(original)
            restored = restart()
            if restored.returncode:
                raise RuntimeError('Gateway restoration failed: ' + restored.stdout + restored.stderr)
        recovery = observe(port, 'restored genuine gateway', 50)
        assert any('ACCEPT 192.0.2.10' in x for x in recovery), 'Board did not recover'
        assert not any('rst:' in x for x in recovery), 'Board reset during recovery'
        report['tests'].append({'test': 'Genuine gateway restored without board reset', 'status': 'PASS'})
    (ROOT / 'results/esp32-certificate-tests.json').write_text(json.dumps(report, indent=2)+'\n')
    print('PASS: hardware certificate tests and recovery', flush=True)


if __name__ == '__main__':
    main()
