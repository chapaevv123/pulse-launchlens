const $ = (q) => document.querySelector(q);
const money = (value) => value == null ? "Not available" : new Intl.NumberFormat("en-US", {style:"currency",currency:"USD",maximumFractionDigits:value < 1 ? 8 : 0}).format(value);
const age = (seconds) => seconds == null ? "Unknown" : seconds < 3600 ? `${Math.max(1,Math.round(seconds/60))}m` : seconds < 86400 ? `${Math.round(seconds/3600)}h` : `${Math.round(seconds/86400)}d`;
const short = (value) => value ? `${value.slice(0,6)}…${value.slice(-4)}` : "Unknown";
const safe = (value) => String(value ?? "Unknown").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const yesNo = (value) => value == null ? "Unknown" : value ? "Yes" : "No";
const external = (href, label) => href ? `<a class="external" href="${safe(href)}" target="_blank" rel="noopener noreferrer">${safe(label)} ↗</a>` : "";

let launches = [];

function openDetail(id, updateUrl = true) {
  const item = launches.find(x => x.launch_id === id); if (!item) return;
  $("#detailBody").innerHTML = detail(item);
  $("#detail").showModal();
  if (updateUrl) history.replaceState(null, "", `#launch=${encodeURIComponent(id)}`);
}

function card(item) {
  return `<button class="card ${item.decision.toLowerCase()}-card" data-id="${safe(item.launch_id)}">
    <span class="token"><span class="token-icon">${safe((item.token_symbol || "?").slice(0,1))}</span><span><strong>${safe(item.token_symbol || item.token_name || "Unknown token")}</strong><small>${safe(short(item.token_address))} · ${safe(item.launch_source.replaceAll("_"," "))}</small></span></span>
    <span class="metric"><small>AGE</small><strong>${age(item.age_seconds)}</strong></span>
    <span class="metric"><small>MARKET</small><strong>${safe(item.market_data_status.replaceAll("_"," "))}</strong></span>
    <span class="metric"><small>ENTRY / EXIT</small><strong>${yesNo(item.entry_executable)} / ${yesNo(item.exit_executable)}</strong></span>
    <span class="decision">${safe(item.decision)}</span>
  </button>`;
}

function detail(item) {
  const r = item.round_trip_result;
  const evidence = Object.entries(item.evidence).filter(([,v]) => v != null);
  return `<article class="detail ${item.decision.toLowerCase()}-card">
    <p class="eyebrow">02 / LAUNCH DETAIL · ${safe(item.record_mode)}</p>
    <div class="detail-top"><span class="token-icon">${safe((item.token_symbol || "?").slice(0,1))}</span><div><h2>${safe(item.token_symbol || item.token_name || "Unknown token")}</h2><div class="address">${safe(item.token_address)}</div><div class="external-row">${external(item.links.contract_explorer,"Contract")}${external(item.links.launch_source,"Launch source")}</div></div></div>
    <section class="verdict"><strong>${safe(item.decision)}</strong>${item.decision_reasons.map(x=>`<p>— ${safe(x)}</p>`).join("")}</section>
    <section class="grid">
      <div><small>DETECTED</small><strong>${new Date(item.detected_at).toLocaleString()}</strong></div>
      <div><small>FRESHNESS</small><strong>${safe(item.freshness_state)}</strong></div>
      <div><small>SOURCE</small><strong>${safe(item.launch_source.replaceAll("_"," "))}</strong></div>
      <div><small>PRICE / QUOTE</small><strong>${money(item.price_usd)}</strong></div>
      <div><small>LIQUIDITY</small><strong>${money(item.liquidity_usd)}</strong></div>
      <div><small>24H VOLUME</small><strong>${money(item.volume_24h_usd)}</strong></div>
      <div><small>MARKET EVIDENCE</small><strong>${safe(item.market_data_status.replaceAll("_"," "))}</strong></div>
      <div><small>MARKET FRESHNESS</small><strong>${safe(item.market_freshness)}</strong></div>
      <div><small>MARKET SOURCE</small><strong>${safe(item.market_source)}</strong></div>
      <div><small>ENTRY EXECUTABLE</small><strong>${yesNo(item.entry_executable)}</strong></div>
      <div><small>EXIT EXECUTABLE</small><strong>${yesNo(item.exit_executable)}</strong></div>
      <div><small>ROUND-TRIP IMPACT</small><strong>${r.loss_percent == null ? "Unknown" : `${r.loss_percent.toFixed(1)}%`}</strong></div>
    </section>
    <section class="evidence"><h3>PROVENANCE & EVIDENCE</h3>${evidence.map(([k,v])=>`<div class="evidence-row"><span>${safe(k.replaceAll("_"," ").toUpperCase())}</span><span>${safe(v)}</span></div>`).join("")}<div class="external-row">${external(item.links.block_explorer,"Observed block")}${external(item.links.market_source,"Market source")}</div></section>
    <p class="disclaimer">${safe(r.disclaimer)} LaunchLens provides research evidence, not financial advice. It never signs or submits transactions.</p>
  </article>`;
}

async function init() {
  const response = await fetch("/api/launches");
  if (!response.ok) throw new Error("Launch feed unavailable");
  const payload = await response.json(); launches = payload.launches;
  $("#dataset").textContent = payload.meta.dataset === "live" ? "LIVE READ-ONLY" : "VERIFIED REPLAY";
  $("#launchCount").textContent = launches.length;
  $("#researchCount").textContent = launches.filter(x=>x.decision === "RESEARCH").length;
  $("#lastObserved").textContent = payload.meta.captured_at ? new Date(payload.meta.captured_at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}) : "—";
  $("#feed").innerHTML = launches.map(card).join("");
  const selected = new URLSearchParams(location.hash.slice(1)).get("launch");
  if (selected) openDetail(selected, false);
}

$("#feed").addEventListener("click", event => {
  const target = event.target.closest("[data-id]"); if (!target) return;
  openDetail(target.dataset.id);
});
function closeDetail(){ $("#detail").close(); history.replaceState(null,"",location.pathname); }
$("#detail .close").addEventListener("click",closeDetail);
$("#detail").addEventListener("click",event=>{if(event.target === $("#detail")) closeDetail()});
init().catch(error => { $("#feed").innerHTML = `<p>${safe(error.message)}</p>`; });
