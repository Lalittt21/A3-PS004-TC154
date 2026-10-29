"""Verify the authoritative server and gateway agree on local DNS results."""
import json
from pathlib import Path

import dns.flags
import dns.message
import dns.query
import dns.rcode

results = []
for port, role in [(15353, "authoritative"), (1053, "gateway")]:
    for name, expected in [
        ("sensor.trustgate.test", dns.rcode.NOERROR),
        ("missing.trustgate.test", dns.rcode.NXDOMAIN),
    ]:
        response = dns.query.udp(
            dns.message.make_query(name, "A", want_dnssec=True),
            "127.0.0.1", port=port, timeout=3,
        )
        assert response.rcode() == expected, (role, name, response)
        if expected == dns.rcode.NOERROR:
            addresses = [item.address for rr in response.answer if rr.rdtype == 1 for item in rr]
            assert addresses == ["192.0.2.10"], addresses
        if role == 'gateway':
            assert response.flags & dns.flags.AD, 'Gateway must authenticate signed responses'
        results.append({"server": role, "name": name, "result": "PASS",
                        "rcode": dns.rcode.to_text(response.rcode())})

output = Path(__file__).resolve().parents[1] / "results" / "plumbing-tests.json"
output.write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
