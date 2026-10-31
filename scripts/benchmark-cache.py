"""Isolated gateway-cache experiment; fresh TLS connection for every request."""
import importlib.util
import json
from pathlib import Path
import socket
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('client',ROOT/'client/python/query.py')
client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)


def main():
    report={'recorded_at':datetime.now(timezone.utc).isoformat(),
      'method':'20 isolated Unbound instances. First DNS request has an empty resolver cache; second request is immediate and warm. Both use fresh authenticated TLS connections. BIND authoritative server stays running.',
      'limits':['Laptop/WSL client and gateway, not ESP32.','No TLS-session reuse, CPU/energy measurement or client-side DNSSEC baseline.','Failures remain in samples and are excluded only from successful-latency summaries.'], 'samples':[]}
    executable=Path.home()/'.local/share/trustgate/unbound/sbin/unbound'
    for index in range(20):
        with tempfile.TemporaryDirectory(prefix='trustgate-cache-') as directory:
            config=Path(directory)/'unbound.conf'
            config.write_text(f'''include: "{ROOT}/gateway/tls-local.conf"
server:
    interface: 127.0.0.1@1953
    interface: 127.0.0.1@1954
    tls-port: 1954
    tls-protocols: "TLSv1.2 TLSv1.3"
    username: ""
    chroot: ""
    directory: "{directory}"
    pidfile: "{directory}/unbound.pid"
    use-syslog: no
    do-ip6: no
    do-not-query-localhost: no
    trust-anchor-file: "{ROOT}/gateway/trust-anchor.key"
    local-zone: "test." nodefault
stub-zone:
    name: "trustgate.test."
    stub-addr: 127.0.0.1@15353
''')
            with (ROOT/'results/cache-benchmark.log').open('a') as log:
                process=subprocess.Popen([str(executable),'-d','-c',str(config)],stdout=log,stderr=log)
                try:
                    for _ in range(50):
                        if process.poll() is not None: raise RuntimeError('Benchmark resolver failed to start')
                        try:
                            with socket.create_connection(('127.0.0.1',1954),.1): pass
                            break
                        except OSError: time.sleep(.1)
                    else: raise RuntimeError('Benchmark resolver not listening')
                    for state in ('cold','warm'):
                        row={'pair':index+1,'cache':state}
                        try:
                            result=client.resolve('sensor.trustgate.test',port=1954)
                            row.update(accepted=result['accepted'],latency_ms=result['latency_ms'])
                        except Exception as exc:
                            row.update(accepted=False,error=str(exc))
                        report['samples'].append(row)
                finally:
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: process.kill();process.wait()
    report['summary']={}
    for state in ('cold','warm'):
        rows=[r for r in report['samples'] if r['cache']==state]
        values=[r['latency_ms'] for r in rows if r['accepted']]
        report['summary'][state]={'attempts':len(rows),'accepted':len(values),
          'median_ms':statistics.median(values) if values else None,
          'max_ms':max(values) if values else None}
    (ROOT/'results/cache-benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['summary'],indent=2))


if __name__=='__main__': main()
