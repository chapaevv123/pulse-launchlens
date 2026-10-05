# Public deployment

LaunchLens deploys as a separate Cloudflare Worker named `pulse-launchlens`.
It has static assets plus an API worker, with no D1 binding, secret, variable,
cron, or connection to the production SQLite database.

## Preflight

```powershell
.\.venv\Scripts\python.exe -m launchlens.tools.export_public_replay
cd launchlens
npm install
npm run test:worker
npx wrangler deploy --dry-run
```

Run the full Python and leakage tests from the Pulse root before deployment.

## Deploy

```powershell
cd launchlens
npx wrangler deploy
```

Wrangler authentication is stored outside this repository. Never add account
tokens, `.env`, `.dev.vars`, D1 IDs, or production data.

## Acceptance

Check the public `/`, `/api/health`, `/api/launches`, and one detail endpoint.
Verify POST returns 405, security headers are present, all external links are
exact, and the public response matches `public/data/launches.json`.
