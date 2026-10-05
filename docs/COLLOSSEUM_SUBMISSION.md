# Colosseum submission copy

## Project website

https://pulse-launchlens.sergtsopa.workers.dev

## What are you building and who is it for?

Pulse LaunchLens is a read-only launch intelligence terminal for Robinhood
Chain traders and researchers. It detects newly observed token launches,
preserves their contract and source provenance, shows available market state,
and checks whether a realistic benchmark trade could both enter and immediately
exit. It then explains a conservative RESEARCH, WATCH, or SUPPRESS decision.

## Why did you decide to build this and why now?

New Robinhood Chain launches arrive across contracts, launchpads, and market
feeds. Seeing a token early is not useful if its identity is unclear or an exit
cannot be verified. As Robinhood Chain's mainnet launch ecosystem grows, users
need a fast evidence layer that distinguishes a real, inspectable launch from
noise without promising predictive alpha.

## Technologies and integrations

- Robinhood Chain mainnet (`4663`)
- EVM event and contract provenance
- Pons launch and read-only quote evidence
- Robinhood Chain Blockscout links
- Python 3.11 public-safe extraction and local replay service
- vanilla JavaScript responsive frontend
- Cloudflare Workers and static assets
- deterministic replay from genuine persisted observations

## Chains used

Robinhood Chain only.

## How the product uses Robinhood Chain

LaunchLens consumes persisted Robinhood Chain launch events and retains their
token contracts, observed blocks, timestamps, and source identities. Its
executability layer uses historical read-only quote evidence for benchmark
entry and immediate exit paths. The interface links each attributable record
back to its exact contract/block and launch surface. LaunchLens never submits a
transaction or asks a judge to connect a wallet.

## Repository context

This repository contains the standalone LaunchLens work created during the
hackathon: its public data contract, replay exporter, dedicated UI, detail
experience, explained decision layer, deployment boundary, tests, and docs.
The private Pulse engine that originally collected launch observations and
performed quote/forward-outcome research predates the hackathon and is not
included. `docs/DISCLOSURE.md` describes that boundary precisely.

## Notes for judges

Replay mode is intentional: it lets every judge inspect the same genuine
RESEARCH, WATCH, and SUPPRESS cases even when no token launches during the demo.
`QUOTE ONLY` is an honesty state—entry/exit evidence exists, while aggregate
liquidity or volume remains unknown. Unknown data is never filled or inferred.

## Any other judge context

LaunchLens is research infrastructure, not an automated trading bot or token
recommendation engine. It does not predict returns, execute trades, connect a
wallet, or provide financial advice. The product's value is fast, reproducible,
evidence-backed triage.
