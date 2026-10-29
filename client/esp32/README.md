# TrustGate ESP32 prototype

Target: classic ESP32 Dev Module (esp32dev), Arduino framework, PlatformIO
Espressif32 platform pinned to 6.9.0. Confirm your exact board before flashing;
ESP32-C3/S3 boards need a different target. The connected board is an
ESP32-D0WD-V3 with 4 MB flash. See docs/hardware-status.md for verified results.

## Configure
Copy include/config.example.h to include/config.h. Set your Wi-Fi SSID, password,
and gateway host LAN IP. Credentials are ignored by Git. The embedded public CA
is generated from ../../gateway/ca.pem by scripts/provision-firmware.py.
Never embed the CA private key or server private key.

The gateway listens on WSL loopback and a configured WSL address. Windows/WSL
LAN forwarding and a firewall rule restricted to the board are also required.
The example IP is deliberately a documentation address, not a working gateway.

## Build in Ubuntu
```bash
cd /mnt/d/TrustGate-IoT
.venv/bin/python scripts/provision-firmware.py
.venv/bin/pio run -d client/esp32
```
After confirming the board and USB port, upload with PlatformIO and open a serial
monitor at 115200 baud. USB access from WSL may require additional setup; a Windows
upload tool is another option. This board was flashed using Windows esptool.

## Clock and serial demo
Certificate validation requires a valid clock. Each boot waits for a trusted
operator to enter `TIME <current Unix seconds>` through USB serial. Obtain the
current timestamp on the laptop using `date +%s` in Ubuntu, then send it promptly.
This manual provisioning is a lab compromise, not a production secure-time design.
The firmware will not use unauthenticated network time to set its clock.

Once Wi-Fi and time are ready, it cycles through the four test names every ten
seconds. Expect ACCEPT for sensor.trustgate.test and BLOCK for unsigned, tampered,
and missing names. NXDOMAIN is a legitimate negative response, not an attack.
It logs elapsed query time and heap statistics, not measured energy consumption.

USB diagnostic commands: `MODE manual` pauses periodic queries, `QUERY` requests
the fixed valid fixture, `MODE demo` resumes the four-name cycle, `SLEEP 0`/`SLEEP 1`
disable/enable modem power saving, and `RECONNECT` requests Wi-Fi reconnection.
These do not bypass certificate or DNS policy checks. Commands are for the trusted
USB operator. Power settings are temporary; reboot restores the framework default.
The library reports result=0 when the requested sleep setting was already active;
inspect the reported mode. Disabling sleep may increase energy consumption.

Failed connection timings are now logged as FAIL_METRIC. Its heap reading is
before TLS cleanup, while successful METRIC is after cleanup; do not compare
these as evidence of a leak. A 3000ms connection setting is not a total-query
deadline: connection phases and DNS reads can make total elapsed time longer.

## Security and limits
The gateway IP is provisioned separately from the certificate hostname. ESP-TLS
checks the embedded CA, hostname and certificate dates. No plaintext fallback or
certificate-check bypass is provided. The device trusts the gateway's AD flag
over TLS and does not perform DNSSEC cryptographic validation itself.
Only direct IPv4 A answers are supported; CNAME chains and IPv6 are not implemented.
DNS response frames are limited to 2048 bytes; oversized frames fail closed.
Name decompression is bounded. Wi-Fi auto-reconnect is enabled, but behaviour,
timeouts, memory use, and recovery still require actual board testing.
This demo opens a new TLS connection for every query. Connection reuse is later work.
Firmware credentials are plaintext in flash; secure boot, flash encryption and
production credential provisioning are not implemented.
