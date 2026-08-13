const $ = (id) => document.getElementById(id);
const TOTAL_STEPS = 5;
let currentStep = 1;
let hostKeyConfirmed = false;

// -- draft autosave --------------------------------------------------------
// Field values only ever reached the server on an explicit test/save click;
// simply navigating between steps, reloading, or the Ingress session
// dropping wiped everything typed so far. Mirror every field into
// localStorage on change and restore it on load so a reload resumes where
// you left off instead of starting over.

const DRAFT_STORAGE_KEY = "talkanchor-wizard-draft";
const DRAFT_FIELD_IDS = [
  "cf-token", "cf-account", "cf-tunnel",
  "echo-url", "echo-field",
  "udm-host", "udm-port", "udm-user", "udm-key",
  "udm-config-path", "udm-profile", "udm-backup-dir", "udm-health-timeout",
  "notify-channel", "notify-ntfy", "notify-webhook",
  "poll-interval", "min-seconds",
];

function saveDraft() {
  const draft = { currentStep, hostKeyConfirmed, lastKeyscanEntry, "cf-enabled": $("cf-enabled").checked };
  for (const id of DRAFT_FIELD_IDS) {
    const el = $(id);
    if (el) draft[id] = el.value;
  }
  localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
}

function loadDraft() {
  const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
  if (!raw) return;
  let draft;
  try {
    draft = JSON.parse(raw);
  } catch {
    localStorage.removeItem(DRAFT_STORAGE_KEY);
    return;
  }
  for (const id of DRAFT_FIELD_IDS) {
    if (draft[id] !== undefined && $(id)) $(id).value = draft[id];
  }
  if (draft["cf-enabled"] !== undefined) $("cf-enabled").checked = draft["cf-enabled"];
  if (draft.currentStep) currentStep = draft.currentStep;
  if (draft.hostKeyConfirmed) hostKeyConfirmed = draft.hostKeyConfirmed;
  if (draft.lastKeyscanEntry) lastKeyscanEntry = draft.lastKeyscanEntry;
}

function clearDraft() {
  localStorage.removeItem(DRAFT_STORAGE_KEY);
}

document.querySelector(".wizard-main").addEventListener("input", saveDraft);
document.querySelector(".wizard-main").addEventListener("change", saveDraft);

// -- server-side prefill ----------------------------------------------------
// The localStorage draft above only survives in the same browser/tab; a
// different Ingress session (e.g. reopening from the HA app vs. a browser
// tab) or the browser clearing site data loses it even though the values
// were genuinely saved server-side already. Fetch the already-saved config
// as a baseline on load; loadDraft() below then overlays anything newer
// that was typed but never saved.

const PREFILL_ID_MAP = {
  "cf-token": "cloudflare_api_token",
  "cf-account": "cloudflare_account_id",
  "cf-tunnel": "cloudflare_tunnel_id",
  "echo-url": "http_echo_url",
  "echo-field": "http_echo_json_field",
  "udm-host": "unifi_host",
  "udm-port": "unifi_ssh_port",
  "udm-user": "unifi_ssh_user",
  "udm-key": "unifi_ssh_private_key",
  "udm-config-path": "unifi_config_path",
  "udm-profile": "unifi_sofia_profile",
  "udm-backup-dir": "unifi_backup_dir_remote",
  "udm-health-timeout": "health_check_timeout_seconds",
  "notify-channel": "notify_channel",
  "notify-ntfy": "notify_ntfy_topic_url",
  "notify-webhook": "notify_webhook_url",
  "poll-interval": "poll_interval_seconds",
  "min-seconds": "min_seconds_between_changes",
};

async function prefillFromSettings() {
  let data;
  try {
    const res = await fetch("api/wizard/prefill");
    if (!res.ok) return;
    data = await res.json();
  } catch {
    return;
  }
  for (const [id, key] of Object.entries(PREFILL_ID_MAP)) {
    const value = data[key];
    if (value !== undefined && value !== "" && $(id)) $(id).value = value;
  }
  if (data.cloudflare_enabled !== undefined) $("cf-enabled").checked = data.cloudflare_enabled;
  if (data.unifi_ssh_known_hosts_entry) {
    lastKeyscanEntry = data.unifi_ssh_known_hosts_entry;
    hostKeyConfirmed = true;
  }
}

$("cf-enabled").addEventListener("change", () => {
  $("cf-fields").hidden = !$("cf-enabled").checked;
});

function showResult(id, text, ok) {
  const el = $(id);
  el.textContent = text;
  el.className = "wizard-result " + (ok === true ? "ok" : ok === false ? "bad" : "");
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Fehler (HTTP ${res.status})`);
  return data;
}

function renderStep() {
  document.querySelectorAll(".wizard-panel").forEach((panel) => {
    panel.hidden = Number(panel.dataset.step) !== currentStep;
  });
  document.querySelectorAll("#step-indicator li").forEach((li) => {
    const step = Number(li.dataset.step);
    li.classList.toggle("active", step === currentStep);
    li.classList.toggle("done", step < currentStep);
  });
  $("back-btn").disabled = currentStep === 1;
  $("next-btn").textContent = currentStep === TOTAL_STEPS ? "Fertig" : "Weiter";
  if (currentStep === TOTAL_STEPS) renderSummary();
}

$("back-btn").addEventListener("click", () => {
  if (currentStep > 1) {
    currentStep -= 1;
    renderStep();
  }
});

$("next-btn").addEventListener("click", () => {
  if (currentStep < TOTAL_STEPS) {
    currentStep += 1;
    renderStep();
  }
});

document.querySelectorAll("#step-indicator li").forEach((li) => {
  li.addEventListener("click", () => {
    currentStep = Number(li.dataset.step);
    renderStep();
  });
});

// -- Step 1: Cloudflare -------------------------------------------------

// Cloudflare tokens never contain whitespace. Users sometimes paste more
// than the token itself (e.g. the whole "curl -H 'Authorization: Bearer
// <token>' ..." example Cloudflare shows next to it), which breaks the
// Authorization header entirely. Extract just the token in that case,
// otherwise strip any accidental whitespace/newlines from the paste.
function sanitizeCloudflareToken(raw) {
  const trimmed = raw.trim();
  const bearerMatch = trimmed.match(/Bearer\s+([A-Za-z0-9_\-.]+)/i);
  if (bearerMatch) return bearerMatch[1];
  return trimmed.replace(/\s+/g, "");
}

$("cf-token-toggle").addEventListener("click", () => {
  const field = $("cf-token");
  const revealed = field.type === "text";
  field.type = revealed ? "password" : "text";
  $("cf-token-toggle").textContent = revealed ? "Anzeigen" : "Verbergen";
});

$("cf-test-btn").addEventListener("click", async () => {
  showResult("cf-test-result", "Prüfe...");
  try {
    const data = await postJson("api/wizard/cloudflare-test", {
      api_token: sanitizeCloudflareToken($("cf-token").value),
      account_id: $("cf-account").value.trim(),
      tunnel_id: $("cf-tunnel").value.trim(),
    });
    showResult("cf-test-result", `Erkannte IP: ${data.ip}`, true);
  } catch (err) {
    showResult("cf-test-result", err.message, false);
  }
});

// -- Step 2: fallback source ---------------------------------------------

$("echo-test-btn").addEventListener("click", async () => {
  showResult("echo-test-result", "Prüfe...");
  try {
    const data = await postJson("api/wizard/http-echo-test", {
      url: $("echo-url").value.trim(),
      json_field: $("echo-field").value.trim(),
    });
    showResult("echo-test-result", `Erkannte IP: ${data.ip}`, true);
  } catch (err) {
    showResult("echo-test-result", err.message, false);
  }
});

// -- Step 3: UniFi SSH -----------------------------------------------------

$("key-generate-btn").addEventListener("click", async () => {
  showResult("key-generate-result", "Erzeuge Schlüssel...");
  try {
    const data = await postJson("api/wizard/ssh-generate-key", {});
    $("udm-key").value = data.private_key;
    $("key-generate-pub").value = data.public_key;
    $("key-generate-pub-row").hidden = false;
    showResult("key-generate-result", `Gespeichert: ${data.path}`, true);
  } catch (err) {
    showResult("key-generate-result", err.message, false);
  }
});

$("key-generate-pub-copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("key-generate-pub").value);
    $("key-generate-pub-copy").textContent = "Kopiert!";
    setTimeout(() => { $("key-generate-pub-copy").textContent = "Kopieren"; }, 1500);
  } catch {
    $("key-generate-pub").select();
  }
});

$("key-save-btn").addEventListener("click", async () => {
  showResult("key-save-result", "Speichere...");
  try {
    const data = await postJson("api/wizard/ssh-key", { private_key: $("udm-key").value });
    showResult("key-save-result", `Gespeichert: ${data.path}`, true);
  } catch (err) {
    showResult("key-save-result", err.message, false);
  }
});

let lastKeyscanEntry = "";

$("keyscan-btn").addEventListener("click", async () => {
  showResult("keyscan-result", "Rufe Host-Key ab...");
  $("keyscan-confirm").hidden = true;
  try {
    const data = await postJson("api/wizard/ssh-keyscan", {
      host: $("udm-host").value.trim(),
      port: Number($("udm-port").value) || 22,
    });
    lastKeyscanEntry = data.known_hosts_entry;
    showResult("keyscan-result", data.known_hosts_entry, true);
    $("keyscan-confirm").hidden = false;
  } catch (err) {
    showResult("keyscan-result", err.message, false);
  }
});

$("keyscan-confirm-btn").addEventListener("click", async () => {
  showResult("keyscan-confirm-result", "Übernehme...");
  try {
    await postJson("api/wizard/known-hosts", { entry: lastKeyscanEntry });
    hostKeyConfirmed = true;
    showResult("keyscan-confirm-result", "Host-Key übernommen.", true);
  } catch (err) {
    showResult("keyscan-confirm-result", err.message, false);
  }
});

$("discover-btn").addEventListener("click", async () => {
  showResult("discover-result", "Suche...");
  $("discover-select").hidden = true;
  try {
    const data = await postJson("api/wizard/discover-sofia", {
      host: $("udm-host").value.trim(),
      port: Number($("udm-port").value) || 22,
      username: $("udm-user").value.trim() || "root",
    });
    if (!data.candidates.length) {
      showResult("discover-result", "Keine passende Config gefunden.", false);
      return;
    }
    const select = $("discover-select");
    select.innerHTML = data.candidates.map((c) => `<option value="${c}">${c}</option>`).join("");
    select.hidden = false;
    select.onchange = () => {
      $("udm-config-path").value = select.value;
    };

    // FreeSWITCH setups almost always have multiple profiles (internal +
    // external, at least); blindly taking the first result risks silently
    // picking the wrong one. Prefer a candidate whose path mentions the
    // configured profile name — still just a heuristic, so always ask the
    // user to double-check when there's more than one candidate.
    const profileName = $("udm-profile").value.trim().toLowerCase();
    const preferred = profileName && data.candidates.find((c) => c.toLowerCase().includes(profileName));
    const picked = preferred || data.candidates[0];
    select.value = picked;
    $("udm-config-path").value = picked;

    if (data.candidates.length > 1) {
      showResult(
        "discover-result",
        `${data.candidates.length} Kandidaten gefunden, "${picked}" ${preferred ? "passt zum Profilnamen" : "wurde als erstes übernommen"} — bitte in der Liste prüfen, ob das wirklich der richtige ist.`,
        Boolean(preferred)
      );
    } else {
      showResult("discover-result", `Gefunden: ${picked}`, true);
    }
  } catch (err) {
    showResult("discover-result", err.message, false);
  }
});

// -- Step 4: notifications -----------------------------------------------

$("notify-channel").addEventListener("change", () => {
  const channel = $("notify-channel").value;
  $("notify-ntfy-row").hidden = channel !== "ntfy";
  $("notify-webhook-row").hidden = channel !== "webhook";
});

// -- Step 5: summary + save ------------------------------------------------

function collectAnswers() {
  return {
    dry_run: true,
    poll_interval_seconds: Number($("poll-interval").value) || 300,
    min_seconds_between_changes: Number($("min-seconds").value) || 300,
    cloudflare_enabled: $("cf-enabled").checked,
    cloudflare_api_token: sanitizeCloudflareToken($("cf-token").value),
    cloudflare_account_id: $("cf-account").value.trim(),
    cloudflare_tunnel_id: $("cf-tunnel").value.trim(),
    http_echo_url: $("echo-url").value.trim(),
    http_echo_json_field: $("echo-field").value.trim(),
    unifi_host: $("udm-host").value.trim(),
    unifi_ssh_port: Number($("udm-port").value) || 22,
    unifi_ssh_user: $("udm-user").value.trim() || "root",
    unifi_ssh_private_key: $("udm-key").value,
    unifi_ssh_known_hosts_entry: lastKeyscanEntry,
    unifi_sofia_profile: $("udm-profile").value.trim() || "external_talk",
    unifi_config_path: $("udm-config-path").value.trim(),
    unifi_backup_dir_remote: $("udm-backup-dir").value.trim(),
    health_check_timeout_seconds: Number($("udm-health-timeout").value) || 30,
    notify_channel: $("notify-channel").value,
    notify_ntfy_topic_url: $("notify-ntfy").value.trim(),
    notify_webhook_url: $("notify-webhook").value.trim(),
  };
}

function renderSummary() {
  const a = collectAnswers();
  const rows = [
    ["Cloudflare", a.cloudflare_enabled ? `${a.cloudflare_account_id || "–"} / ${a.cloudflare_tunnel_id || "–"}` : "deaktiviert"],
    ["Fallback-Quelle", a.http_echo_url],
    ["UniFi Host", a.unifi_host || "–"],
    ["SSH-Host-Key übernommen", hostKeyConfirmed ? "ja" : "nein"],
    ["Sofia-Profil", a.unifi_sofia_profile],
    ["Sofia-Config-Pfad", a.unifi_config_path || "–"],
    ["Polling-Intervall", `${a.poll_interval_seconds}s`],
    ["Rate-Limit", `${a.min_seconds_between_changes}s`],
    ["Benachrichtigung", a.notify_channel],
  ];
  $("summary-table").innerHTML = rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("");
}

$("save-btn").addEventListener("click", async () => {
  showResult("save-result", "Speichere...");
  try {
    const answers = collectAnswers();
    answers.dry_run = true;
    const data = await postJson("api/wizard/save", answers);
    showResult("save-result", data.message, true);
    $("check-now-wizard-btn").disabled = false;
    $("golive-confirm").disabled = false;
  } catch (err) {
    showResult("save-result", err.message, false);
  }
});

$("check-now-wizard-btn").addEventListener("click", async () => {
  showResult("check-now-wizard-result", "Prüfe...");
  try {
    const res = await fetch("api/check-now", { method: "POST" });
    const data = await res.json();
    showResult(
      "check-now-wizard-result",
      data.changed ? `Änderung erkannt: ${data.checked_ip}` : data.skipped_reason || `Keine Änderung (${data.checked_ip ?? "n/a"})`,
      true
    );
  } catch (err) {
    showResult("check-now-wizard-result", err.message, false);
  }
});

$("golive-confirm").addEventListener("input", () => {
  $("golive-btn").disabled = $("golive-confirm").value !== "GO LIVE";
});

$("golive-btn").addEventListener("click", async () => {
  if ($("golive-confirm").value !== "GO LIVE") return;
  showResult("golive-result", "Schalte scharf...");
  try {
    const answers = collectAnswers();
    answers.dry_run = false;
    const data = await postJson("api/wizard/save", answers);
    showResult("golive-result", `Scharf geschaltet. ${data.message}`, true);
    clearDraft();
  } catch (err) {
    showResult("golive-result", err.message, false);
  }
});

(async () => {
  await prefillFromSettings();
  loadDraft();
  $("notify-channel").dispatchEvent(new Event("change"));
  $("cf-enabled").dispatchEvent(new Event("change"));
  renderStep();
})();
