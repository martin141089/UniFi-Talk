// Static GitHub Pages demo: same rendering logic as the real dashboard's
// static/dashboard.js, but fed from hardcoded fake data instead of the
// live /api/* endpoints (there is no backend on GitHub Pages).
const $ = (id) => document.getElementById(id);

const now = Date.now();
const hoursAgo = (h) => new Date(now - h * 3600 * 1000).toISOString();

const FAKE_STATUS = {
  current_ip: "203.0.113.201",
  last_change_at: hoursAgo(6),
  dry_run: false,
  last_event: {
    health_ok: true,
    health_message: "2/2 Registrierungen REGED",
  },
};

const FAKE_HISTORY = [
  {
    created_at: hoursAgo(6),
    old_ip: "203.0.113.44",
    new_ip: "203.0.113.201",
    dry_run: false,
    apply_success: true,
    health_ok: true,
    rolled_back: false,
  },
  {
    created_at: hoursAgo(54),
    old_ip: "203.0.113.10",
    new_ip: "203.0.113.44",
    dry_run: false,
    apply_success: true,
    health_ok: true,
    rolled_back: false,
  },
  {
    created_at: hoursAgo(102),
    old_ip: "198.51.100.5",
    new_ip: "203.0.113.10",
    dry_run: false,
    apply_success: true,
    health_ok: false,
    rolled_back: true,
  },
];

const FAKE_LOGS = [
  { time: hoursAgo(6), level: "INFO", logger: "talkanchor.reconciler", message: "IP change detected: 203.0.113.44 -> 203.0.113.201" },
  { time: hoursAgo(6), level: "INFO", logger: "talkanchor.targets.unifi_talk", message: "Backed up external_talk.xml to /root/talkanchor-backups (remote) and ./data/backups (local)" },
  { time: hoursAgo(6), level: "INFO", logger: "talkanchor.reconciler", message: "Health check passed: 2/2 registrations REGED" },
  { time: hoursAgo(54), level: "INFO", logger: "talkanchor.reconciler", message: "IP change detected: 203.0.113.10 -> 203.0.113.44" },
  { time: hoursAgo(102), level: "WARNING", logger: "talkanchor.reconciler", message: "Health check failed after applying 203.0.113.10: profile did not show healthy registrations within 30s" },
  { time: hoursAgo(102), level: "WARNING", logger: "talkanchor.reconciler", message: "Rollback attempted: succeeded" },
];

function fmtTime(iso) {
  if (!iso) return "–";
  return new Date(iso).toLocaleString();
}

function renderStatus() {
  $("current-ip").textContent = FAKE_STATUS.current_ip;
  $("last-change").textContent = `Letzte Änderung: ${fmtTime(FAKE_STATUS.last_change_at)}`;

  const badge = $("dry-run-badge");
  badge.textContent = FAKE_STATUS.dry_run ? "DRY-RUN" : "LIVE";
  badge.className = "badge " + (FAKE_STATUS.dry_run ? "warn" : "");

  const event = FAKE_STATUS.last_event;
  $("health-status").textContent = event.health_ok ? "OK" : "FEHLER";
  $("health-status").className = "big " + (event.health_ok ? "ok" : "bad");
  $("health-message").textContent = event.health_message;
}

function renderHistory() {
  const tbody = document.querySelector("#history-table tbody");
  tbody.innerHTML = "";
  for (const row of FAKE_HISTORY) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${fmtTime(row.created_at)}</td>
      <td>${row.old_ip} → ${row.new_ip}</td>
      <td>${row.dry_run ? "ja" : "nein"}</td>
      <td class="${row.apply_success ? "ok" : "bad"}">${row.apply_success ? "OK" : "Fehler"}</td>
      <td class="${row.health_ok ? "ok" : "bad"}">${row.health_ok ? "OK" : "Fehler"}</td>
      <td>${row.rolled_back ? "ja" : "–"}</td>
    `;
    tbody.appendChild(tr);
  }
}

function renderLogs() {
  $("live-log").textContent = FAKE_LOGS.map((l) => `[${l.time}] ${l.level} ${l.logger}: ${l.message}`).join("\n");
}

for (const id of ["check-now-btn", "rollback-btn"]) {
  $(id).addEventListener("click", () => {
    $("action-result").textContent = "Dies ist eine Demo mit Beispieldaten — keine echte Aktion wird ausgeführt.";
  });
}

renderStatus();
renderHistory();
renderLogs();
