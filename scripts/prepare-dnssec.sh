#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/share/trustgate/unbound/sbin:$PATH"
cd /mnt/d/TrustGate-IoT
# Private signing keys stay in the Linux filesystem, outside the repository.
keydir="$HOME/.local/share/trustgate/signing-keys"
mkdir -p "$keydir"
chmod 700 "$keydir"
if ! compgen -G "$keydir/Ktrustgate.test.+013+*.private" > /dev/null; then
    dnssec-keygen -K "$keydir" -a ECDSAP256SHA256 -f KSK trustgate.test
fi
dnssec-signzone -n 2 -S -z -K "$keydir" -o trustgate.test -f dns-lab/zones/trustgate.test.signed dns-lab/zones/trustgate.test.zone
cat "$keydir"/Ktrustgate.test.+013+*.key > gateway/trust-anchor.key
# Change only the test A record AFTER signing. Its old signature is preserved.
.venv/bin/python - <<'PY'
from pathlib import Path
p = Path('dns-lab/zones/trustgate.test.signed')
s = p.read_text()
assert s.count('192.0.2.20') == 1
p.write_text(s.replace('192.0.2.20', '192.0.2.99'))
PY
named-checkconf dns-lab/named.conf
unbound-checkconf gateway/unbound.conf
