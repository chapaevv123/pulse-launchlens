# Pulse LaunchLens

> Know what launched, whether it is actually tradable, and why it deserves attention.

Pulse LaunchLens is a read-only launch intelligence terminal for Robinhood
Chain. It combines on-chain launch provenance, available market observations,
and realistic entry/exit quotes in one evidence-first interface.

LaunchLens never trades, signs wallet messages, or predicts winners.

## What it does

New token launches are fragmented across chain events, launchpads, and market
feeds. LaunchLens answers five focused questions:

1. What launched?
2. Where did it come from?
3. What market evidence is available?
4. Did a benchmark entry and immediate exit quote succeed?
5. Should a researcher **RESEARCH**, **WATCH**, or **SUPPRESS** it?

## Why Robinhood Chain

Robinhood Chain is a new EVM Layer 2 for financial applications. Its emerging
launch ecosystem makes source attribution and executable exit evidence useful
at the moment a launch is hardest to evaluate. LaunchLens is deliberately
Robinhood Chain-only. Mainnet chain ID `4663` and its Blockscout explorer are
documented by [Robinhood Chain](https://docs.robinhood.com/chain/connecting/).

## Core flow

```text
Launch → Provenance → Market state → Executability → Explained decision
```

The public product exposes exactly these five capabilities: launch discovery,
provenance, market state, executability, and explained decisions.

## RESEARCH / WATCH / SUPPRESS

- **RESEARCH** — verified launch source, sufficiently fresh evidence, working
  benchmark entry and exit quotes, and no blocking condition.
- **WATCH** — potentially relevant, but evidence is incomplete or the observed
  round-trip impact is too high.
- **SUPPRESS** — stale, non-executable, blocked by a no-chase condition, or not
  attributable to a verified source.

There is no synthetic master score. Missing evidence cannot become RESEARCH.

## Architecture

```text
Private Pulse engine (pre-existing, not deployed)
  → allowlisted LaunchLens export
  → public replay JSON
  → read-only Cloudflare Worker API
  → standalone static LaunchLens interface
```

The public Worker has no database binding, secret, cron, wallet, or write
endpoint. It supports `GET /api/health`, `GET /api/launches`, and
`GET /api/launches/:id`. All mutating HTTP methods return `405 read_only`.

## Replay mode

Replay is a first-class demo path. Its RESEARCH, WATCH, and SUPPRESS cases are
genuine persisted Robinhood Chain observations. Contracts, event IDs, blocks,
timestamps, and quote results are preserved. A fixed reference time makes the
demo deterministic. Records are visibly labeled `REPLAY`.

Generate the deployable public artifact:

```powershell
.\.venv\Scripts\python.exe -m launchlens.tools.export_public_replay
```

## Safety

- read-only; no trading or wallet signing;
- no automated execution or owner actions;
- no Telegram or Discord dependency;
- no production database is deployed;
- no private owner, wallet, or machine data crosses the allowlist;
- unknown liquidity and volume remain unknown;
- `QUOTE ONLY` means a quote was observed, not that aggregate liquidity is known;
- not financial advice.

## Data provenance

Launch identity and block evidence come from persisted Robinhood Chain
observations. Executability comes from historical read-only Pons quote paths.
Block and contract links target the official Robinhood Chain Blockscout listed
in Robinhood's documentation. Pons links appear only for records attributed to
Pons; no generic homepage is presented as token evidence.

## Pre-existing Pulse infrastructure disclosure

Before the hackathon, private Pulse infrastructure already performed Robinhood
Chain source observation, launch persistence, market discovery, quote and
round-trip evaluation, freshness/no-chase classification, and forward outcome
tracking. That private infrastructure is not included or represented as code
written during the hackathon. See [DISCLOSURE.md](docs/DISCLOSURE.md).

## Hackathon-period work

- standalone LaunchLens product and repository boundary;
- narrow public-safe data contract and export;
- genuine deterministic replay experience;
- dedicated feed and launch-detail UI;
- explainable RESEARCH/WATCH/SUPPRESS policy;
- executability and provenance presentation;
- read-only Cloudflare deployment boundary;
- public documentation, submission copy, scripts, and media plan;
- security, authenticity, responsive, API, and side-effect tests.

## Local setup

Requirements: Python 3.11+ for the local data adapter and Node 18+ for the
Cloudflare build.

```powershell
# deterministic demo
.\.venv\Scripts\python.exe -m launchlens.server --mode replay --port 8780

# current persisted observations, still read-only and offline
.\.venv\Scripts\python.exe -m launchlens.server --mode live --port 8780

# Python tests
.\.venv\Scripts\python.exe -m unittest discover -s launchlens/tests -v

# Worker tests / local Worker preview
cd launchlens
npm install
npm run test:worker
npm run dev
```

## Public demo

**Live:** https://pulse-launchlens.sergtsopa.workers.dev

The isolated `pulse-launchlens` Worker passed the public leakage and read-only
gates. Judges need no account, wallet, or setup.

## Limitations

- Replay is historical evidence, not a live trading signal.
- Quote success does not imply future execution.
- Aggregate liquidity and volume are not available for every bonding-curve
  launch; those records are explicitly `QUOTE ONLY`.
- Source names and token metadata can be incomplete.
- Decisions prioritize evidence quality, not return prediction.

## License

The standalone hackathon work is provided under the MIT License. The private,
pre-existing Pulse engine is outside this repository boundary and is not
licensed by this file.
