#!/usr/bin/env bash
set -euo pipefail
cd /mnt/d/TrustGate-IoT
export PATH="$HOME/.local/share/trustgate/unbound/sbin:$PATH"
mkdir -p results
named-checkconf dns-lab/named.conf
named-checkzone trustgate.test dns-lab/zones/trustgate.test.zone
unbound-checkconf gateway/unbound.conf
# Refuse to start duplicate processes on the lab ports.
if ss -lnut | grep -Eq ':(1053|15353|1853)[[:space:]]'; then
    echo "A lab port is already in use. Inspect existing processes before starting."
    exit 1
fi
nohup named -g -c "$PWD/dns-lab/named.conf" > results/named.log 2>&1 &
nohup unbound -d -c "$PWD/gateway/unbound.conf" > results/unbound.log 2>&1 &
sleep 2
.venv/bin/python client/python/query.py
