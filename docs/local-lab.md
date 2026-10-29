# TrustGate local security lab

## Current scope
Python -> authenticated DNS-over-TLS -> Unbound -> local BIND zones.
ESP32 firmware and restricted LAN forwarding are implemented; see hardware-status.md
for board results. Certificate renewal automation, restart services and
performance benchmarks remain pending. This is a local prototype, not a
production deployment. No Windows system DNS settings were changed.

## Run in Ubuntu
```bash
cd /mnt/d/TrustGate-IoT
bash scripts/run-dnssec-stage.sh
.venv/bin/python client/python/query.py
.venv/bin/python client/python/query.py sensor.unsigned.trustgate.test
.venv/bin/python tests/test_tls_policy.py
```
The full stage prints commands, generates lab certificates, signs zones, safely
stops only matching lab processes, starts the servers and runs all test suites.
The unsigned query exits with code 2 because the strict policy blocks it.
Connection errors exit with code 1. Accepted answers exit with code 0.

## Services and fixtures
- BIND: Linux loopback port 15353, authoritative test zones.
- Unbound: loopback port 1053 for diagnostics; TLS port 1853 for the client.
- sensor.trustgate.test -> 192.0.2.10, valid signed answer.
- tampered.trustgate.test -> deliberately changed after signing; rejected.
- sensor.unsigned.trustgate.test -> 192.0.2.30, unsigned child; strict client blocks.
- missing.trustgate.test -> authenticated NXDOMAIN (name does not exist).
The addresses are documentation examples, not real sensor endpoints.

## Trust and security
ECDSA DNSSEC keys are generated using dnssec-keygen and kept in Ubuntu under
~/.local/share/trustgate/signing-keys. Unbound trusts that zone's public key.
This is a private local trust anchor, not a chain from the public DNS root.
The parent signs its unsigned delegation with no DS record. Tests verify the
DNSSEC-authenticated absence of DS, not just a response with the AD flag missing.

TLS keys and the local CA key are under ~/.local/share/trustgate/tls, outside
the project. Only the CA public certificate is copied into gateway/ca.pem.
The Python client checks both that CA and gateway.trustgate.test as the hostname.
It has no plaintext fallback. The diagnostic UDP port remains loopback-only.
The client trusts the authenticated gateway's DNSSEC decision; a compromised
trusted gateway is outside this prototype's protection. TLS currently authenticates
only the server, not the client. The ESP32 embeds the public lab CA certificate.

Certificates are valid for 30 days and DNSSEC signatures for approximately 30 days.
Rerunning the full stage refreshes the server certificate and zone signatures.
The local CA lasts 365 days; replacement and production renewal are not automated.

## Evidence
results/plumbing-tests.json: four DNS checks.
results/dnssec-tests.json: six validation checks, including a diagnostic
checking-disabled control. Production client never sets CD.
results/tls-policy-tests.json: nine TLS/policy/delegation checks, including
authenticated TLS 1.2 and TLS 1.3 handshakes.
results/unbound.log: actual cryptographic signature failure for tampered data.
SERVFAIL alone does not prove an attack. Report its cause only with diagnostics.
Single-query timings are diagnostic output, not benchmark results.
Services do not automatically start after a reboot.

## Client configuration and failure checks
The client accepts --gateway-ip, --gateway-name, --port, --ca-file and --timeout.
Use a provisioned literal IP for the gateway; the certificate hostname is checked
separately. No insecure verification switch or plaintext fallback is provided.
The gateway also listens on its configured WSL IPv4 address at TLS port 1853.
Windows forwarding is restricted by a firewall rule to the board's IPv4 address.
Update these addresses when changing networks; do not expose diagnostic port 1053.

```bash
.venv/bin/python client/python/query.py --gateway-ip 127.0.0.1 --gateway-name gateway.trustgate.test --port 1853 --timeout 3
bash scripts/verify-lab.sh
```

The verification script runs all four suites. Seven additional resilience checks
use real sockets and the actual command-line client: refused connection, stalled
TLS handshake, certificate mismatch, unsigned and tampered answers, invalid timeout,
and a successful fresh request after failures. The stalled connection uses a
0.5-second network timeout; total process time includes Python startup overhead.
Results are saved in results/resilience-tests.json. This is not an ESP32 recovery
test, automatic reconnection, or a sustained-load benchmark. The no-fallback claim
is based on the TLS-only client code and failed-request results, not packet capture.
