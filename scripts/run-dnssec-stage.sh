#!/usr/bin/env bash
set -euo pipefail
set -x
cd /mnt/d/TrustGate-IoT
export PATH="$HOME/.local/share/trustgate/unbound/sbin:$PATH"
bash scripts/prepare-tls.sh
bash scripts/prepare-dnssec.sh
.venv/bin/python scripts/stop-lab.py
bash scripts/start-lab.sh
.venv/bin/python tests/test_dnssec.py
.venv/bin/python tests/test_plumbing.py
.venv/bin/python tests/test_tls_policy.py
.venv/bin/python tests/test_resilience.py
