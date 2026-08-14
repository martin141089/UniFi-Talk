const $ = (id) => document.getElementById(id);

function fmtTime(iso) {
  if (!iso) return "–";
  return new Date(iso).toLocaleString();
}

async function refreshStatus() {
  const res = await fetch("api/status");
  const data = await res.json();

  $("current-ip").textContent = data.current_ip || "unbekannt";
  $("last-change").textContent = data.last_change_at
    ? `Letzte Änderung: ${fmtTime(data.last_change_at)}`
    : "Noch keine Änderung erfasst";

  const badge = $("dry-run-badge");
  badge.textContent = data.dry_run ? "DRY-RUN" : "LIVE";
  badge.className = "badge " + (data.dry_run ? "warn" : "");

  const event = data.last_event;
  if (event) {
    $("health-status").textContent =
      event.health_ok === null ? "–" : event.health_ok ? "OK" : "FEHLER";
    $("health-status").className = "big " + (event.health_ok ? "ok" : event.health_ok === false ? "bad" : "");
    $("health-message").textContent = event.health_message || event.apply_message || "–";
  }
}

const HISTORY_INITIAL_COUNT = 3;
const HISTORY_PAGE_SIZE = 10;
const HISTORY_FETCH_LIMIT = 90;
let historyVisibleCount = HISTORY_INITIAL_COUNT;

async function refreshHistory() {
  const res = await fetch(`api/history?limit=${HISTORY_FETCH_LIMIT}`);
  const allRows = await res.json();
  const rows = allRows.slice(0, historyVisibleCount);
  const tbody = document.querySelector("#history-table tbody");
  tbody.innerHTML = "";
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td data-label="Zeit">${fmtTime(row.created_at)}</td>
      <td data-label="Alt → Neu">${row.old_ip ?? "–"} → ${row.new_ip}</td>
      <td data-label="Dry-Run">${row.dry_run ? "ja" : "nein"}</td>
      <td data-label="Anwenden" class="${row.apply_success ? "ok" : "bad"}">${row.apply_success ? "OK" : "Fehler"}</td>
      <td data-label="Health-Check" class="${row.health_ok ? "ok" : row.health_ok === false ? "bad" : ""}">${
        row.health_ok === null ? "–" : row.health_ok ? "OK" : "Fehler"
      }</td>
      <td data-label="Rollback">${row.rolled_back ? "ja" : "–"}</td>
    `;
    tbody.appendChild(tr);
  }

  const loadMoreBtn = $("history-load-more-btn");
  const remaining = allRows.length - rows.length;
  loadMoreBtn.hidden = remaining <= 0;
  loadMoreBtn.textContent = `Weitere Verläufe laden (${remaining})`;
}

$("history-load-more-btn").addEventListener("click", () => {
  historyVisibleCount += HISTORY_PAGE_SIZE;
  refreshHistory();
});

async function refreshLogs() {
  const res = await fetch("api/logs");
  const lines = await res.json();
  const pre = $("live-log");
  const wasAtBottom = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 10;
  pre.textContent = lines.map((l) => `[${l.time}] ${l.level} ${l.logger}: ${l.message}`).join("\n");
  if (wasAtBottom) pre.scrollTop = pre.scrollHeight;
}

async function refreshAll() {
  await Promise.all([refreshStatus(), refreshHistory(), refreshLogs()]);
}

async function pollCheckNowStatus(maxMs = 300000, intervalMs = 2000) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const res = await fetch("api/check-now-status");
    const data = await res.json();
    if (!data.running) return data;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return null;
}

$("check-now-btn").addEventListener("click", async () => {
  $("action-result").textContent = "Prüfe...";
  try {
    const startRes = await fetch("api/check-now", { method: "POST" });
    const startData = await startRes.json();
    if (startData.already_running) {
      $("action-result").textContent = "Eine Prüfung läuft bereits – warte auf Ergebnis...";
    }
    const status = await pollCheckNowStatus();
    if (!status) {
      $("action-result").textContent = "Prüfung läuft weiter im Hintergrund (dauert ungewöhnlich lange) – Verlauf oben aktualisiert sich automatisch.";
    } else if (status.error) {
      $("action-result").textContent = `Fehler: ${status.error}`;
    } else {
      const data = status.result;
      $("action-result").textContent = data.changed
        ? `Änderung erkannt: ${data.checked_ip}`
        : data.skipped_reason || `Keine Änderung (${data.checked_ip ?? "n/a"})`;
    }
  } catch (err) {
    $("action-result").textContent = `Fehler: ${err.message}`;
  }
  await refreshAll();
});

$("rollback-btn").addEventListener("click", async () => {
  if (!confirm("Wirklich auf das letzte Backup zurückrollen?")) return;
  $("action-result").textContent = "Rollback läuft...";
  try {
    const res = await fetch("api/rollback", { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Rollback fehlgeschlagen");
    $("action-result").textContent = data.message;
  } catch (err) {
    $("action-result").textContent = `Fehler: ${err.message}`;
  }
  await refreshAll();
});

async function runSetupAction(resultId, url, formatSuccess) {
  const out = $(resultId);
  out.textContent = "Läuft...";
  try {
    const res = await fetch(url, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Aktion fehlgeschlagen");
    out.textContent = formatSuccess(data);
  } catch (err) {
    out.textContent = `Fehler: ${err.message}`;
  }
}

$("keyscan-btn").addEventListener("click", () =>
  runSetupAction("keyscan-result", "api/setup/ssh-keyscan", (data) => data.known_hosts_entry)
);

$("discover-btn").addEventListener("click", () =>
  runSetupAction("discover-result", "api/setup/discover-sofia", (data) =>
    data.candidates.length ? data.candidates.join("\n") : "Keine sofia*.xml gefunden."
  )
);

$("cf-test-btn").addEventListener("click", () =>
  runSetupAction("cf-test-result", "api/setup/cloudflare-test", (data) => `Erkannte IP: ${data.ip}`)
);

refreshAll();
setInterval(refreshAll, 10000);
