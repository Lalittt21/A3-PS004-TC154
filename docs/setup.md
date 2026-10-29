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

## Remaining work

Hardware negative-certificate tests, repeated failure/recovery testing,
controlled performance benchmarks and production provisioning remain separate
tasks. Single-query serial timings are diagnostic observations, not benchmarks.
