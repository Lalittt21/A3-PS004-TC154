# Hardware reliability and initial measurements

Tested on 29 October 2026: classic ESP32, Arduino/PlatformIO firmware,
Unbound 1.26.2 in WSL, Windows TCP forwarding and the current shared Wi-Fi.

## Confirmed configuration fault

After a board reboot, DHCP assigned a different board address. The Windows
firewall allowed only the old address, so connection attempts timed out.
Updating the board-specific rule restored connectivity. This explains that
particular failure, not every earlier intermittent timeout.

Always compare the board's `WIFI connected IP=` output with the firewall's
RemoteAddress before testing. Reserve a DHCP address on a router you administer
if available. On this shared network, rerun `scripts/enable-lan.ps1` with the
current board IP when it changes. Do not broaden the rule to the whole network.

## Repeated queries

`results/board-power-save-comparison.json` records four alternating phases:
12 queries with modem sleep on, 12 off, then the same pair again.
All 48 measured queries accepted the expected signed answer.

| Wi-Fi modem sleep | Accepted | Median successful query | Observed range |
| --- | --- | --- | --- |
| On | 24/24 | 888 ms | 690–1671 ms |
| Off | 24/24 | 805 ms | 685–935 ms |

Each request opened a new authenticated TLS connection. There was a 0.5-second
pause between samples; the gateway cache was not flushed. Timing is the board's
wall-clock query duration, including connection and DNS exchange, not CPU time.
All 48 interleaved laptop TLS controls passed, but they do not exercise the
board's Wi-Fi link and are not equivalent DNS-query benchmarks.

Measured phases began after the first successful warm-up query. Warm-up had
failures, including an incomplete response and connection failures. Those are
excluded from the table and remain relevant to reliability. Modem sleep off
showed lower latency in this sample; these results do not establish the root
cause of intermittent failures or imply an energy saving.

The ten-second-pause follow-up (`results/board-idle-comparison.json`) accepted
5/6 requests with modem sleep on and 6/6 with it off. The failed request had
completed TLS authentication but did not deliver a complete DNS frame within
the client read limits. This narrows that failure to the post-handshake exchange;
it does not identify whether the AP, forwarding path, or device caused it.
Software verification briefly ran during this follow-up, so treat its timings
as diagnostic observations, not a controlled performance comparison.
The running demo was left with sleep off; reboot restores the framework default.

## Recovery tests

`results/esp32-recovery-tests.json` records two gateway shutdown/restart cycles
and two client-requested Wi-Fi reconnect cycles. Modem sleep was disabled for
these tests. With the gateway down, requests failed closed. After each restart
or reconnect, the first attempted valid query was accepted without board reset.

The reported recovery times include polling and a full query after the gateway
restart or Wi-Fi connected event. They are not total outage or association times.
Client-requested reconnection does not reproduce access-point power loss.

## Reproduce and interpret

Close other COM8 monitors and run in Windows PowerShell:

```powershell
python scripts/measure-board.py
python scripts/test-board-recovery.py
python scripts/measure-board.py --samples 6 --pause 10 --rounds 1 --output board-idle-comparison.json
```

Both scripts require a running genuine gateway. Raw serial output is saved
locally in results/board-diagnostics.log. Do not run unrelated load tests while
collecting performance numbers. USB diagnostics are intended for a trusted lab
operator. The firmware still checks CA, hostname and certificate dates.

Still required: diagnose intermittent failures during startup and spaced
requests, longer runs on a controlled network, cold/warm-cache separation,
and suitable baselines before claiming CPU, memory or battery savings.
