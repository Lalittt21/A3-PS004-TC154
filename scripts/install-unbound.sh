#!/usr/bin/env bash
# Run as your normal Ubuntu user after installing build dependencies.
set -euo pipefail
version=1.26.2
sha=d8ee7aa6bbb3ff1be7d9e57637d0d0ec2f18273a8efff1a0afe2c665858b96f7
build="$HOME/.cache/trustgate-build"
mkdir -p "$build"
cd "$build"
curl --fail --location --retry 3 "https://nlnetlabs.nl/downloads/unbound/unbound-$version.tar.gz" -o "unbound-$version.tar.gz"
printf '%s  %s\n' "$sha" "unbound-$version.tar.gz" | sha256sum -c -
tar -xzf "unbound-$version.tar.gz"
cd "unbound-$version"
./configure --prefix="$HOME/.local/share/trustgate/unbound" --with-libevent --without-pyunbound --without-pythonmodule
make -j2
make install
