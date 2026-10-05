import assert from "node:assert/strict";
import test from "node:test";
import worker from "../src/index.js";

const replay = JSON.parse(await (await import("node:fs/promises")).readFile(new URL("../public/data/launches.json", import.meta.url), "utf8"));
const env = {
  ASSETS: {
    async fetch(request) {
      const path = new URL(request.url).pathname;
      if (path === "/data/launches.json") return Response.json(replay);
      if (path === "/" || path === "/index.html") return new Response("<title>Pulse LaunchLens</title>", {headers:{"Content-Type":"text/html"}});
      return new Response("not found", {status:404});
    },
  },
};

test("health is public and read-only", async () => {
  const response = await worker.fetch(new Request("https://example.test/api/health"), env);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {status:"ok", mode:"verified_replay", read_only:true});
});

test("feed and detail return the same public records", async () => {
  const feed = await worker.fetch(new Request("https://example.test/api/launches"), env);
  const payload = await feed.json();
  assert.equal(payload.launches.length, 4);
  const detail = await worker.fetch(new Request(`https://example.test/api/launches/${payload.launches[0].launch_id}`), env);
  assert.deepEqual(await detail.json(), payload.launches[0]);
});

test("all writes are rejected", async () => {
  for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
    const response = await worker.fetch(new Request("https://example.test/api/launches", {method}), env);
    assert.equal(response.status, 405);
  }
});

test("security headers protect public assets", async () => {
  const response = await worker.fetch(new Request("https://example.test/"), env);
  assert.equal(response.headers.get("X-Frame-Options"), "DENY");
  assert.match(response.headers.get("Content-Security-Policy"), /connect-src 'self'/);
});
