"""Record every attempt, including startup failures, during a 60-query run."""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('measure',ROOT/'scripts/measure-board.py')
measure=importlib.util.module_from_spec(spec);spec.loader.exec_module(measure)


def main():
    sys.stdout.reconfigure(errors='replace')
    report={'started_at':datetime.now(timezone.utc).isoformat(),'completed':False,
      'method':'60 fixed valid-fixture requests, 2-second pause, fresh TLS each time, modem sleep disabled, no automatic query retries; startup attempts included.',
      'limits':['Shared Wi-Fi, not a controlled network.','No energy or independent client DNSSEC baseline.'], 'samples':[]}
    board=measure.Board()
    start=time.monotonic()
    try:
        board.read_until('No queries until time is provisioned')
        board.send('MODE manual');board.read_until('MODE manual')
        board.send(f'TIME {int(time.time())}');board.read_until('Time provisioned')
        board.send('SLEEP 0');board.read_until('SLEEP result=')
        for index in range(60):
            lines=board.query()
            row={'attempt':index+1,'accepted':any('ACCEPT 192.0.2.10' in x for x in lines)}
            metric=re.search(r'(?:FAIL_)?METRIC elapsed_ms=(\d+)','\n'.join(lines))
            row['elapsed_ms']=int(metric.group(1)) if metric else None
            row['decision']=next((x for x in lines if x.startswith(('ACCEPT','BLOCK'))),'no decision')
            row['board_reset']=any('rst:' in x for x in lines)
            report['samples'].append(row)
            if row['board_reset']: raise RuntimeError('Board reset during run')
            time.sleep(2)
        report['completed']=True
    finally:
        report['duration_seconds']=round(time.monotonic()-start,2)
        report['accepted']=sum(r['accepted'] for r in report['samples'])
        report['failed']=len(report['samples'])-report['accepted']
        (ROOT/'results/esp32-soak-2026-10-31.json').write_text(json.dumps(report,indent=2)+'\n')
        board.close()
        print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))


if __name__=='__main__': main()
