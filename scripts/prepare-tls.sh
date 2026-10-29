#!/usr/bin/env bash
set -euo pipefail
cd /mnt/d/TrustGate-IoT
certdir="$HOME/.local/share/trustgate/tls"
mkdir -p "$certdir"
chmod 700 "$certdir"
umask 077
if [ ! -f "$certdir/ca.pem" ]; then
    openssl req -x509 -newkey rsa:2048 -nodes -days 365 -subj '/CN=TrustGate Local Lab CA' -keyout "$certdir/ca.key" -out "$certdir/ca.pem" -addext 'basicConstraints=critical,CA:TRUE' -addext 'keyUsage=critical,keyCertSign,cRLSign'
fi
openssl req -new -newkey rsa:2048 -nodes -subj '/CN=gateway.trustgate.test' -keyout "$certdir/server.key" -out "$certdir/server.csr"
printf '%s\n' 'subjectAltName=DNS:gateway.trustgate.test' 'basicConstraints=critical,CA:FALSE' 'keyUsage=critical,digitalSignature,keyEncipherment' 'extendedKeyUsage=serverAuth' > "$certdir/server.ext"
openssl x509 -req -in "$certdir/server.csr" -CA "$certdir/ca.pem" -CAkey "$certdir/ca.key" -CAcreateserial -days 30 -extfile "$certdir/server.ext" -out "$certdir/server.pem"
cp "$certdir/ca.pem" gateway/ca.pem
printf 'server:\n    tls-service-key: "%s/server.key"\n    tls-service-pem: "%s/server.pem"\n' "$certdir" "$certdir" > gateway/tls-local.conf
