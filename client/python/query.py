"""Strict DNS-over-TLS client for the local TrustGate lab."""
import argparse
import json
from pathlib import Path
import ssl
import time
import ipaddress
import math
import dns.flags
import dns.message
import dns.query
import dns.rcode

ROOT = Path(__file__).resolve().parents[2]

def resolve(name, hostname='gateway.trustgate.test', cafile=ROOT / 'gateway/ca.pem', port=1853,
            address='127.0.0.1', timeout=3):
    ipaddress.ip_address(address)  # Avoid unauthenticated DNS to discover the gateway.
    if not 1 <= port <= 65535 or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Port must be 1..65535 and timeout must be positive and finite')
    if not hostname:
        raise ValueError('Gateway certificate hostname is required')
    context = ssl.create_default_context(cafile=str(cafile) if cafile else None)
    request = dns.message.make_query(name, 'A', want_dnssec=True)
    request.flags |= dns.flags.AD
    start = time.perf_counter()
    response = dns.query.tls(request, address, port=port, timeout=timeout,
                             ssl_context=context, server_hostname=hostname)
    authenticated = bool(response.flags & dns.flags.AD)
    code = response.rcode()
    addresses = [item.address for rr in response.answer if rr.rdtype == 1 for item in rr]
    accepted = code == dns.rcode.NOERROR and authenticated and bool(addresses)
    if code == dns.rcode.SERVFAIL:
        decision = 'blocked: resolver failure (consult gateway logs for cause)'
    elif not authenticated:
        decision = 'blocked: answer not DNSSEC-authenticated'
    elif code == dns.rcode.NXDOMAIN:
        decision = 'authenticated: name does not exist'
    elif accepted:
        decision = 'accepted'
    else:
        decision = 'no usable answer'
    return {'name': name, 'rcode': dns.rcode.to_text(code),
            'authenticated_data': authenticated, 'accepted': accepted,
            'decision': decision,
            'addresses': addresses if accepted else [],
            'answers': [rr.to_text() for rr in response.answer] if accepted else [],
            'latency_ms': round((time.perf_counter()-start)*1000, 3),
            'transport': 'TLS with CA and hostname verification'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', nargs='?', default='sensor.trustgate.test')
    parser.add_argument('--gateway-ip', default='127.0.0.1', help='Provisioned gateway IP address')
    parser.add_argument('--gateway-name', default='gateway.trustgate.test', help='Expected certificate hostname')
    parser.add_argument('--port', type=int, default=1853)
    parser.add_argument('--ca-file', type=Path, default=ROOT / 'gateway/ca.pem')
    parser.add_argument('--timeout', type=float, default=3, help='Network timeout in seconds')
    args = parser.parse_args()
    try:
        result = resolve(args.name, hostname=args.gateway_name, cafile=args.ca_file,
                         port=args.port, address=args.gateway_ip, timeout=args.timeout)
    except (ValueError, OSError, ssl.SSLError, dns.exception.DNSException) as error:
        print(json.dumps({'accepted': False, 'decision': 'blocked: connection failed',
                          'error': str(error)}, indent=2))
        raise SystemExit(1)
    print(json.dumps(result, indent=2))
    if not result['accepted']:
        raise SystemExit(2)

if __name__ == '__main__':
    main()
