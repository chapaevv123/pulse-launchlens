const SECURITY_HEADERS = {
  "Cache-Control": "public, max-age=60",
  "Content-Security-Policy": "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
};

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...SECURITY_HEADERS },
  });
}

async function replay(env, request) {
  const response = await env.ASSETS.fetch(new Request(new URL("/data/launches.json", request.url)));
  if (!response.ok) throw new Error("public replay unavailable");
  return response.json();
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!["GET", "HEAD"].includes(request.method)) {
      return json({ error: "read_only" }, 405);
    }
    if (url.pathname === "/api/health") {
      return json({ status: "ok", mode: "verified_replay", read_only: true });
    }
    if (url.pathname === "/api/launches") {
      try { return json(await replay(env, request)); }
      catch { return json({ error: "data_unavailable" }, 503); }
    }
    if (url.pathname.startsWith("/api/launches/")) {
      try {
        const payload = await replay(env, request);
        const id = decodeURIComponent(url.pathname.slice("/api/launches/".length));
        const launch = payload.launches.find(item => item.launch_id === id);
        return launch ? json(launch) : json({ error: "not_found" }, 404);
      } catch { return json({ error: "data_unavailable" }, 503); }
    }
    const asset = await env.ASSETS.fetch(request);
    const headers = new Headers(asset.headers);
    Object.entries(SECURITY_HEADERS).forEach(([key, value]) => headers.set(key, value));
    return new Response(asset.body, { status: asset.status, statusText: asset.statusText, headers });
  },
};
