# TrustGate IoT - Team LinkX

**AIORI Hackathon 3 | A3-PS004-TC154 | CHRIST University**

## Team

- Lalit Kumar
- Sujitha V

Individual work assignments will be documented once confirmed by the team.

## Problem statement

**PS-004: Authenticated Gateway-Assisted DNSSEC for IoT Clients**

Small IoT devices have limited processing power and memory. DNSSEC validation adds resource costs, while forged DNS responses can redirect devices to incorrect destinations. The challenge is to delegate validation to a trusted gateway and secure the client-to-gateway connection.

## Proposed solution

TrustGate IoT uses one lightweight IoT client and one local DNSSEC-validating gateway running Unbound. The client authenticates the gateway over DNS over TLS. The gateway validates DNS data against a configured trust anchor and rejects bogus answers.

The controlled lab will test valid signed data, an authenticated unsigned delegation, invalid signatures and an untrusted gateway certificate. Unsigned data is distinct from bogus data; the proposed strict client policy blocks unsigned answers.

The client relies on the trusted gateway. It does not independently perform end-to-end DNSSEC validation. A compromised trusted gateway remains a limitation.

## Presentation

[Read the proposal PDF](Team_LinkX_PS004_Proposal.pdf)

The presentation follows the supplied structure: abstract, background, RFC review, proposed solution, optimizations, architecture, data flow, milestones and bibliography.

## Team introduction video

[Watch the team introduction and proposed solution](https://youtu.be/earyq23zmHI)

The orientation video introduces the team, problem and proposed solution. The guidelines also require each member to explain their assigned role; this must be checked before marking the video requirement complete.

[Thumbnail](Team_LinkX_YouTube_Thumbnail.png)

## Implementation status

Concept proposal. Prototype implementation, security tests and benchmark results are pending. No measured performance or energy savings are claimed.

Planned measurements include latency, client CPU time and peak memory, with cold/warm caches and new/reused TLS sessions reported separately. Ordinary DNS is an overhead baseline; offloading savings require a comparable client-side validation baseline. Energy is measured only with suitable hardware.

## Level 1 submission checklist

- [x] Repository created from the official template, not forked.
- [x] Repository named A3-PS004-TC154.
- [ ] Confirm all teammate and aiori-hackathon collaborator invitations are accepted.
- [ ] Transfer ownership to aiori-hackathon after the required invitations are accepted.
- [x] Proposal PDF included in this repository.
- [ ] Verify YouTube orientation video includes each member's role.
- [x] Add the uploaded YouTube video URL to this README.

The official page lists October 14 for steps 1-7. This checklist records actual status and does not assert timely submission or qualification.

## References

- [Official hackathon guidelines](https://portal.aiori.in/aiori-3/hackathon-guideline/)
- [RFC 4035 - DNSSEC protocol modifications](https://www.rfc-editor.org/rfc/rfc4035.html)
- [RFC 7858 - DNS over TLS](https://www.rfc-editor.org/rfc/rfc7858.html)
- [RFC 8310 - Authentication profiles](https://www.rfc-editor.org/rfc/rfc8310.html)
- [Unbound configuration](https://unbound.docs.nlnetlabs.nl/en/latest/manpages/unbound.conf.html)

