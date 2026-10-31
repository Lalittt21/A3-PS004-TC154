"""Update only lab IP settings; never display Wi-Fi credentials."""
import argparse
import ipaddress
from pathlib import Path
import re


def update(root, laptop, wsl, board, subnet):
    addresses = [ipaddress.IPv4Address(x) for x in (laptop, wsl, board)]
    network = ipaddress.IPv4Network(subnet, strict=False)
    if any(not x.is_private or x.is_loopback or x.is_unspecified for x in addresses):
        raise ValueError('Use private, non-loopback LAN addresses')
    if addresses[1] not in network:
        raise ValueError('WSL address must belong to the supplied subnet')
    config = root / 'client/esp32/include/config.h'
    text = config.read_text()
    match = re.search(r'^#define TG_GATEWAY_IP "([^"]+)"', text, re.M)
    if not match:
        raise ValueError('Expected exactly one TG_GATEWAY_IP definition')
    replaced, n = re.subn(r'^#define TG_GATEWAY_IP "[^"]+"',
                          f'#define TG_GATEWAY_IP "{laptop}"', text, flags=re.M)
    if n != 1:
        raise ValueError('Ambiguous gateway configuration')
    path = root / 'gateway/unbound.conf'
    gateway = path.read_text()
    gateway, n = re.subn(r'^    interface: (?!127\.0\.0\.1)[0-9.]+@1853$',
                         f'    interface: {wsl}@1853', gateway, flags=re.M)
    if n != 1:
        raise ValueError('Expected one WSL TLS interface')
    gateway = re.sub(r'^    access-control: (?!127\.0\.0\.0/8)[0-9./]+ allow\n?', '', gateway, flags=re.M)
    gateway = gateway.replace('    access-control: 127.0.0.0/8 allow',
        f'    access-control: 127.0.0.0/8 allow\n    access-control: {network} allow\n    access-control: {board}/32 allow')
    config.write_text(replaced)
    path.write_text(gateway)
    print(f'Gateway {match.group(1)} -> {laptop}; WSL {wsl}; board {board}. Rebuild/flash if the gateway IP changed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('laptop','wsl','board','subnet'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    update(Path(__file__).resolve().parents[1],args.laptop,args.wsl,args.board,args.subnet)
