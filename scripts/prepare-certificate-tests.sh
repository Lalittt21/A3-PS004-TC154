#!/usr/bin/env bash
set -euo pipefail
umask 077
certdir="$HOME/.local/share/trustgate/tls"
fixtures="$HOME/.local/share/trustgate/certificate-tests"
mkdir -p "$fixtures"
# Correct hostname, but a self-signed certificate outside the provisioned CA.
openssl req -x509 -newkey rsa:2048 -nodes -days 2 \
  -subj '/CN=gateway.trustgate.test' \
  -addext 'subjectAltName=DNS:gateway.trustgate.test' \
  -addext 'extendedKeyUsage=serverAuth' \
  -keyout "$fixtures/untrusted.key" -out "$fixtures/untrusted.pem"
# Trusted CA, but the wrong DNS hostname: isolates hostname checking.
openssl req -new -newkey rsa:2048 -nodes -subj '/CN=impostor.trustgate.test' \
  -keyout "$fixtures/wrong-host.key" -out "$fixtures/wrong-host.csr"
printf '%s\n' 'subjectAltName=DNS:impostor.trustgate.test' 'basicConstraints=critical,CA:FALSE' 'keyUsage=critical,digitalSignature,keyEncipherment' 'extendedKeyUsage=serverAuth' > "$fixtures/wrong-host.ext"
openssl x509 -req -in "$fixtures/wrong-host.csr" -CA "$certdir/ca.pem" \
  -CAkey "$certdir/ca.key" -CAcreateserial -days 2 \
  -extfile "$fixtures/wrong-host.ext" -out "$fixtures/wrong-host.pem"
