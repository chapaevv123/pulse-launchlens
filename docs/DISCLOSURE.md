# Pre-existing infrastructure disclosure

## Pre-existing Pulse engine

Before the Crypto World's Fair hackathon, the private Pulse codebase already
contained Robinhood Chain launch adapters for sources including Pons, Bankr,
Doppler, hood.dev, and Lunch.fun; persisted launch observations; read-only
market discovery; benchmark quote and round-trip evaluation; freshness and
no-chase rules; paper observation; and forward-outcome tracking.

That engine remains private, is not deployed with LaunchLens, and must not be
interpreted as contest-period code. The genuine replay observations were
exported from it through a narrow allowlist.

## New LaunchLens work

The following work was created for the hackathon:

- standalone product/repository boundary;
- public-safe data contract and exporter;
- deterministic replay built from genuine observations;
- LaunchLens visual identity, feed, and detail experience;
- explainable RESEARCH/WATCH/SUPPRESS presentation;
- quote-only and market-evidence honesty states;
- contract, block, launch-source, and market-source links;
- read-only Python demo service and Cloudflare Worker API;
- security headers and write rejection;
- public tests and documentation;
- judge narrative, form copy, video scripts, and media plan.

No authorship date or provenance claim is made for the private Pulse engine.
