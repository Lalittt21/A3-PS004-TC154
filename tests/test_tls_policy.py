import importlib.util
import json
from pathlib import Path
import ssl
import socket
import dns.flags
import dns.message
import dns.query

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('client', root / 'client/python/query.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
results = []
# The ESP32 Arduino client requires TLS 1.2. Check both supported versions,
# using the same CA and hostname verification as the application.
for version in (ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3):
    context = ssl.create_default_context(cafile=str(root / 'gateway/ca.pem'))
    context.minimum_version = context.maximum_version = version
    with socket.create_connection(('127.0.0.1', 1853), timeout=3) as raw:
        with context.wrap_socket(raw, server_hostname='gateway.trustgate.test') as tls:
            results.append({'test': f'Authenticated {tls.version()} handshake', 'status': 'PASS'})
for name, accepted, ad, code in [
    ('sensor.trustgate.test', True, True, 'NOERROR'),
    ('sensor.unsigned.trustgate.test', False, False, 'NOERROR'),
    ('tampered.trustgate.test', False, False, 'SERVFAIL'),
    ('missing.trustgate.test', False, True, 'NXDOMAIN'),
]:
    r = client.resolve(name)
    assert (r['accepted'], r['authenticated_data'], r['rcode']) == (accepted, ad, code), r
    results.append({'test': name, 'status': 'PASS', 'detail': r})

# Signed parent must authenticate the absence of a DS at the unsigned delegation.
q = dns.message.make_query('unsigned.trustgate.test', 'DS', want_dnssec=True)
response = dns.query.udp(q, '127.0.0.1', port=1053, timeout=3)
assert response.rcode() == 0 and not response.answer and response.flags & dns.flags.AD
results.append({'test': 'Authenticated absence of DS for unsigned child', 'status': 'PASS'})

for label, kwargs in [('Wrong gateway hostname', {'hostname': 'impostor.trustgate.test'}),
                      ('Untrusted CA', {'cafile': None})]:
    try:
        client.resolve('sensor.trustgate.test', **kwargs)
    except ssl.SSLCertVerificationError:
        results.append({'test': label, 'status': 'PASS: certificate rejected'})
    else:
        raise AssertionError(label)

(root / 'results/tls-policy-tests.json').write_text(json.dumps(results, indent=2)+'\n')
print(json.dumps(results, indent=2))
