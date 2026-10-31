# TrustGate IoT architecture

Implemented local prototype. System overview, query sequence and client acceptance policy.

```mermaid
flowchart LR
    ESP["ESP32 client<br/>Verify gateway CA, hostname and dates<br/>Require authenticated data and a valid A answer"]
    USB["Trusted operator / USB<br/>Clock provisioning"] --> ESP
    subgraph LAPTOP["Laptop / Windows host"]
        WIN["Windows TCP forwarding<br/>Port 1853<br/>Firewall restricted to board IP"]
        subgraph WSL["Ubuntu / WSL"]
            GW["Unbound gateway<br/>TLS termination + DNSSEC validation<br/>Validated response cache"]
            BIND["BIND authoritative test server<br/>127.0.0.1:15353<br/>Valid, unsigned, tampered and missing-name fixtures"]
            ANCHOR["Configured local DNSSEC trust anchor"] --> GW
            DIAG["Local diagnostics / dig<br/>127.0.0.1:1053"] --> GW
            GW <-->|"Local DNS"| BIND
        end
        WIN <-->|"TLS bytes unchanged"| GW
    end
    ESP <-->|"DNS over TLS / Wi-Fi / TCP 1853"| WIN
```

The TLS server identity is verified by the ESP32. TLS does not authenticate the
client with a client certificate in this prototype. Windows forwards the encrypted
connection; Unbound terminates it and validates DNSSEC against the local anchor.

The strict client blocks unsigned answers. Bogus signatures cause validation
failure; SERVFAIL alone does not prove the cause without gateway diagnostics.
NXDOMAIN can be an authenticated negative answer. There is no plaintext fallback.
The client relies on the trusted gateway; gateway compromise remains a limitation.
This lab does not demonstrate a public DNS root chain or a production deployment.
