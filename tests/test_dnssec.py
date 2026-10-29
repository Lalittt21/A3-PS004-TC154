"""Validate signed answers and prove rejection of a deliberately corrupted RRset."""
import json
from pathlib import Path
import dns.flags
import dns.message
import dns.query
import dns.rcode

results = []
def query(name, port=1053, cd=False):
    q = dns.message.make_query(name, 'A', want_dnssec=True)
    if cd:
        q.flags |= dns.flags.CD
    return dns.query.udp(q, '127.0.0.1', port=port, timeout=5)

def check(label, response, code, ad, address=None):
    assert response.rcode() == code, (label, response.to_text())
    assert bool(response.flags & dns.flags.AD) == ad, label
    addresses = [r.address for rr in response.answer if rr.rdtype == 1 for r in rr]
    assert addresses == ([] if address is None else [address]), (label, addresses)
    results.append({'test': label, 'status': 'PASS', 'rcode': dns.rcode.to_text(code),
                    'authenticated_data': ad, 'addresses': addresses})

check('Valid signed answer', query('sensor.trustgate.test'), 0, True, '192.0.2.10')
check('Authenticated nonexistent name', query('missing.trustgate.test'), 3, True)
check('Authority serves corrupted test address', query('tampered.trustgate.test', 15353), 0, False, '192.0.2.99')
check('Gateway rejects corrupted signature', query('tampered.trustgate.test'), 2, False)
# Diagnostic control only: CD disables checking and must never be set by production clients.
check('Diagnostic CD control retrieves same corrupted record', query('tampered.trustgate.test', cd=True), 0, False, '192.0.2.99')
check('Gateway still rejects after CD control', query('tampered.trustgate.test'), 2, False)
p = Path(__file__).resolve().parents[1] / 'results' / 'dnssec-tests.json'
p.write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
