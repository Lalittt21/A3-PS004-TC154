"""Embed only the local lab CA public certificate in the ESP32 build."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
ca = (root / 'gateway/ca.pem').read_text()
if 'PRIVATE KEY' in ca or not ca.startswith('-----BEGIN CERTIFICATE-----'):
    raise ValueError('Expected a public CA certificate only')
target = root / 'client/esp32/include/ca_cert.h'
target.write_text('#pragma once\nstatic const char TG_CA[] = R"CERT(' + ca + ')CERT";\n')
print('Embedded public CA:', target)
