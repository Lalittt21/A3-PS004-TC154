#!/usr/bin/env bash
set -euo pipefail
set -x
cd /mnt/d/TrustGate-IoT
.venv/bin/python tests/test_plumbing.py
.venv/bin/python tests/test_dnssec.py
.venv/bin/python tests/test_tls_policy.py
.venv/bin/python tests/test_resilience.py
