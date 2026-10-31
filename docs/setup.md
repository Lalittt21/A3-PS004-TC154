# Reproduce the local prototype

The current scripts target Ubuntu in WSL with the project at
`D:\TrustGate-IoT` (`/mnt/d/TrustGate-IoT`). If using another location, update
the absolute paths in the shell scripts, resolver configs and stop script.

## Ubuntu dependencies

```bash
sudo apt-get update
sudo apt-get install -y bind9 bind9-utils dnsutils python3-venv python3-pip openssl curl build-essential libssl-dev libexpat1-dev libevent-dev
cd /mnt/d/TrustGate-IoT
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
bash scripts/install-unbound.sh
```

The installer builds checksum-pinned Unbound 1.26.2 under
`~/.local/share/trustgate/unbound`. It does not replace Ubuntu's system binary.
The gateway explicitly permits TLS 1.2 and TLS 1.3. Unbound 1.24.2 disables
TLS 1.2, which prevents this Arduino ESP32 firmware from connecting.

Before starting, set the non-loopback interface in `gateway/unbound.conf` to
your WSL IPv4 address (`hostname -I`). Adjust access-control entries for the
WSL network and board. Keep diagnostic port 1053 on loopback.

```bash
bash scripts/run-dnssec-stage.sh
```

This creates private lab keys outside the repository, signs the test zones,
starts BIND and Unbound, and runs the software tests. These are controlled
local DNSSEC fixtures, not a validation chain from the public root.

## ESP32 and Windows forwarding

Before each session run `powershell -File scripts/network-preflight.ps1` and
read the ESP32 serial IP. DHCP can change both laptop and board addresses.
Update local files without displaying credentials:

```powershell
python scripts/configure-network.py --laptop 192.168.88.17 --wsl 172.25.142.176 --board 192.168.88.18 --subnet 172.25.128.0/20
```

These are the addresses observed on 31 October, not permanent defaults. Substitute
the current addresses. Restart the lab and rerun the administrator forwarding
script with matching addresses. Rebuild/reflash whenever the gateway IP changes.
The preflight reads source settings; it cannot prove what is flashed on the board.

If WSL cannot overwrite a Windows build output, build in Ubuntu's private cache:

```bash
PLATFORMIO_BUILD_DIR="$HOME/.cache/trustgate-firmware-build" .venv/bin/pio run -d client/esp32
```

Only flash after the build reports SUCCESS. The binary is under that directory's
esp32dev folder and contains credentials. A failed upload is not a usable board;
retry only after checking USB connectivity and require a verified write hash.

Follow `client/esp32/README.md` to create the ignored Wi-Fi configuration and
public CA header. Install PlatformIO into the venv before building:

```bash
.venv/bin/pip install platformio==6.2.0
.venv/bin/python scripts/provision-firmware.py
.venv/bin/pio run -d client/esp32
```

Run `scripts/enable-lan.ps1` in administrator PowerShell with the current
`-LaptopAddress`, `-WslAddress` and `-BoardAddress`. If changing networks,
also pass `-PreviousLaptopAddress` to remove the old lab forwarding entry.
Only TCP port 1853 is forwarded, and the firewall allows only the board IP.
The Wi-Fi network must allow communication between its clients.

Flash the confirmed board with an appropriate serial tool. Firmware binaries
contain Wi-Fi credentials and must remain local. `scripts/monitor-board.py`
uses Windows pyserial, COM8 and 115200 baud; adjust the port if needed.
It provisions the clock over USB and records the serial output locally.

## Physical-board certificate tests

With the genuine gateway running, the board connected and other serial monitors
closed, run this in Windows PowerShell:

```powershell
python -m pip install pyserial
python scripts/test-board-certificates.py
```

The test first checks the genuine gateway, then temporarily presents a
self-signed certificate with the correct hostname, followed by a certificate
signed by the trusted lab CA with the wrong hostname. A Python control verifies
each intended certificate error, while serial output must show an explicit ESP32
certificate verification failure, repeated blocked attempts and no accepted
answers. Socket timeouts are counted separately. A finally block
restores the original TLS configuration and gateway. The final phase checks
that the same board accepts the genuine gateway again without resetting it.

The test temporarily interrupts the lab service. If the test process or machine
is forcibly terminated, regenerate the genuine configuration using
`bash scripts/prepare-tls.sh` and restart the lab. Keep raw logs local; the
structured result is written only after all phases pass.

## Remaining work

Repeated failure/recovery testing, intermittent timeout diagnosis,
controlled performance benchmarks and production provisioning remain separate
tasks. See docs/submission-checklist.md for the final deliverable review and
docs/demo-walkthrough.md for the recording sequence. Initial measurements are
documented in docs/reliability-and-measurements.md; they are not energy savings.
