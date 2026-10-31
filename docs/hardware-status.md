# ESP32 hardware status

31 October update: the laptop and ESP32 DHCP addresses changed; configuration
and the board-restricted firewall were updated. A fresh build was flashed with
write-hash verification after resolving USB transfer failures by reconnecting.
The subsequent 60-attempt run lasted 166.78 seconds: 59 valid answers accepted,
one initial request blocked before Wi-Fi connected, and no subsequent failures.
See results/esp32-soak-2026-10-31.json. This is a short shared-network run, not
controlled-network or production reliability validation.

Verified on 29 October 2026 with an ESP32-D0WD-V3 revision 3.1, 4 MB flash,
Windows COM8 and Unbound 1.26.2 in Ubuntu/WSL.

Firmware was built, uploaded and write hashes verified. The board joined Wi-Fi,
received time over USB and queried the gateway over TLS. The firmware verifies
its provisioned CA, certificate hostname and dates.

| Query | Observed board decision |
| --- | --- |
| sensor.trustgate.test | ACCEPT 192.0.2.10 |
| sensor.unsigned.trustgate.test | BLOCK: no authenticated-data flag |
| tampered.trustgate.test | BLOCK: SERVFAIL |
| missing.trustgate.test | BLOCK: NXDOMAIN |

A subsequent valid query was also accepted. The gateway log reported
`signature crypto failed` for the deliberately tampered fixture. SERVFAIL alone
does not identify an attack. NXDOMAIN is a legitimate negative answer.

The initial TLS failure was caused by Unbound 1.24.2 disabling TLS 1.2.
The project now uses Unbound 1.26.2 with TLS 1.2 and 1.3 explicitly enabled;
certificate verification remains enabled. Windows forwarding and a firewall
rule restricted to the board were updated for the current LAN.

Structured evidence: results/esp32-smoke-tests.json. Raw serial logs remain
local in results/esp32-hardware.log. These observations are not benchmarks.

## Physical-board certificate checks

The board rejected both a self-signed certificate with the correct gateway name
and a trusted-CA certificate with the wrong hostname. The first produced two
explicit certificate verification errors; the second produced one. Neither
fixture produced an accepted DNS answer. The Python control confirmed the
intended certificate error in each case. After restoring the genuine gateway,
the same board accepted a valid answer without resetting or reflashing.

Evidence: `results/esp32-certificate-tests.json`. This was controlled server
certificate substitution, not an on-network interception attack.

Intermittent connection timeouts occurred with both genuine and test gateways.
They were recorded separately and do not count as certificate rejection evidence.
An initial recorder encoding error was fixed; another baseline attempt failed
with timeouts before the final complete test passed. The timeout cause remains
unresolved, so reliable repeated operation is not yet demonstrated.

## Recovery and measurements

Two gateway restart cycles and two client-requested Wi-Fi reconnect cycles now
pass on the board with modem sleep disabled. All 48 measured rapid queries
passed after warm-up. See [measurement methods and limits](reliability-and-measurements.md)
for results, including startup failures excluded from those 48 samples.

A DHCP address change caused a stale firewall rule, which was corrected.
Intermittent failures are not fully resolved: the spaced-query follow-up had
one incomplete response with modem sleep enabled. Further controlled-network
diagnosis and longer reliability testing remain necessary. Initial latency
measurements do not demonstrate CPU or energy savings.

Build artifacts under .pio contain configured credentials and are excluded
from publication. Secure boot, flash encryption and production provisioning
are not implemented. The clock needs USB provisioning after reset.
