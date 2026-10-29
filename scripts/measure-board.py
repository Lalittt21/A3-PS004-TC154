"""Controlled USB queries and laptop TLS controls; no credentials in output."""
import datetime
import argparse
import json
from pathlib import Path
import re
import socket
import ssl
import statistics
import sys
import time
import serial

ROOT = Path(__file__).resolve().parents[1]


class Board:
    def __init__(self):
        self.port = serial.Serial('COM8', 115200, timeout=0.2)
        self.port.dtr = False
        self.port.rts = False
        self.log = (ROOT/'results/board-diagnostics.log').open('a', encoding='utf-8')
        self.log.write('\n--- '+datetime.datetime.now(datetime.timezone.utc).isoformat()+' ---\n')

    def send(self, command):
        self.port.write((command+'\n').encode())

    def read_until(self, marker, seconds=20):
        lines = []
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            line = self.port.readline().decode(errors='replace').strip()
            if line:
                lines.append(line)
                print(line, flush=True)
                self.log.write(line+'\n'); self.log.flush()
                if marker in line:
                    return lines
        raise TimeoutError('Serial marker missing: '+marker)

    def ready(self):
        # Allow boot; issue clock and manual mode after the firmware prompt.
        self.read_until('No queries until time is provisioned', 20)
        self.send('MODE manual'); self.read_until('MODE manual')
        self.send(f'TIME {int(time.time())}'); self.read_until('Time provisioned')
        # A Wi-Fi event may have appeared before the clock acknowledgement.
        for _ in range(12):
            lines = self.query()
            if any('ACCEPT 192.0.2.10' in x for x in lines):
                return
            time.sleep(2)
        raise RuntimeError('Board did not become ready')

    def query(self):
        self.send('QUERY')
        return self.read_until('QUERY_DONE')

    def close(self):
        self.send('MODE demo')
        self.port.close(); self.log.close()


def laptop_control():
    config = (ROOT/'client/esp32/include/config.h').read_text()
    address = re.search(r'#define\s+TG_GATEWAY_IP\s+"([^"]+)"', config).group(1)
    context = ssl.create_default_context(cafile=str(ROOT/'gateway/ca.pem'))
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    start = time.perf_counter()
    try:
        with socket.create_connection((address,1853),3) as raw:
            with context.wrap_socket(raw,server_hostname='gateway.trustgate.test'):
                pass
        return {'ok':True,'tls_ms':round((time.perf_counter()-start)*1000,2)}
    except OSError as exc:
        return {'ok':False,'error':str(exc)}


def summarize(rows):
    success = [r['elapsed_ms'] for r in rows if r['accepted']]
    return {'attempts':len(rows),'accepted':len(success),
            'failed':len(rows)-len(success),
            'median_success_ms':statistics.median(success) if success else None,
            'min_success_ms':min(success) if success else None,
            'max_success_ms':max(success) if success else None}


def main():
    sys.stdout.reconfigure(errors='replace')
    parser=argparse.ArgumentParser()
    parser.add_argument('--samples',type=int,default=12)
    parser.add_argument('--pause',type=float,default=0.5)
    parser.add_argument('--rounds',type=int,default=2)
    parser.add_argument('--output',default='board-power-save-comparison.json')
    args=parser.parse_args()
    if not (1 <= args.samples <= 100 and 0 <= args.pause <= 60 and 1 <= args.rounds <= 5):
        parser.error('Use 1-100 samples, 0-60 seconds pause, 1-5 rounds')
    if Path(args.output).name != args.output or not args.output.endswith('.json'):
        parser.error('Output must be a JSON filename within results')
    report = {'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'method':f'{args.samples} queries per phase, alternating sleep on/off {args.rounds} times; {args.pause}s pause; new TLS 1.2 connection per query; connection timeout setting 3000ms (not a total-query deadline); existing gateway cache not flushed',
              'limits':['Measured phases start only after first accepted warm-up query. Startup failures are excluded and may occur.',
                        'Laptop control measures TLS only and does not traverse the ESP32 Wi-Fi link.',
                        'No energy or client-side DNSSEC baseline; no offloading-savings claim.'],
              'phases':[]}
    board=Board()
    try:
        board.ready()
        for sleep in (1,0)*args.rounds:
            print(f'PHASE sleep={sleep}',flush=True)
            board.send(f'SLEEP {sleep}')
            setting=board.read_until('SLEEP result=')
            assert any(f'mode={sleep}' in x for x in setting), 'Power mode not applied'
            rows=[]
            for number in range(args.samples):
                lines=board.query()
                accepted=any('ACCEPT 192.0.2.10' in x for x in lines)
                metrics='\n'.join(lines)
                elapsed=re.search(r'(?:FAIL_)?METRIC elapsed_ms=(\d+)',metrics)
                row={'number':number+1,'accepted':accepted,
                     'elapsed_ms':int(elapsed.group(1)) if elapsed else None,
                     'socket_timeout':any('select() timeout' in x for x in lines),
                     'laptop_control':laptop_control()}
                rows.append(row)
                time.sleep(args.pause)
            report['phases'].append({'sleep':sleep,'summary':summarize(rows),'queries':rows})
            print(json.dumps(report['phases'][-1]['summary']),flush=True)
            (ROOT/'results'/args.output).write_text(json.dumps(report,indent=2)+'\n')
    finally:
        board.close()


if __name__=='__main__':
    main()
