/**
 * AEG FSE73768P Lovelace card — Tesla-style hero graphic for the running dishwasher.
 * Registered as custom:aeg-fse73768p-card and served by the integration.
 */
const CARD_TAG = "aeg-fse73768p-card";
const EDITOR_TAG = "aeg-fse73768p-card-editor";
const DOMAIN = "aeg_fse73768p";
const RED = "#C8102E";

const PHASE_COPY = {
  idle: "Idle",
  delay: "Delayed start",
  prewash: "Prewash",
  main_wash: "Main wash",
  intermediate_rinse: "Intermediate rinse",
  final_rinse: "Final rinse",
  drying: "Drying",
  airdry: "AirDry",
  complete: "Complete",
  paused: "Paused",
};

function formatRemaining(seconds) {
  const s = Math.max(0, Number(seconds) || 0);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
  return `${m} min`;
}

function findStateEntity(hass, config) {
  if (config?.entity && hass.states[config.entity]) return config.entity;
  const match = Object.values(hass.states).find(
    (st) => st.attributes?.model === "FSE73768P" && st.attributes?.state
  );
  return match?.entity_id ?? null;
}

function deviceIdFor(hass, entityId) {
  return hass.entities?.[entityId]?.device_id;
}

class AEGFSE73768PCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement(EDITOR_TAG);
  }

  static getStubConfig() {
    return {};
  }

  constructor() {
    super();
    this._config = {};
    this._hass = null;
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 9;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: 8, min_rows: 6 };
  }

  _data() {
    if (!this._hass) return null;
    const entityId = findStateEntity(this._hass, this._config);
    if (!entityId) return null;
    const state = this._hass.states[entityId];
    return { entityId, deviceId: deviceIdFor(this._hass, entityId), ...state.attributes, haState: state.state };
  }

  _call(service, data = {}) {
    if (!this._hass) return;
    const payload = { ...data };
    const info = this._data();
    if (info?.deviceId) payload.device_id = info.deviceId;
    this._hass.callService(DOMAIN, service, payload);
  }

  _toggle(domain, entityId) {
    if (!this._hass || !entityId) return;
    this._hass.callService(domain, "toggle", { entity_id: entityId });
  }

  _entity(suffix) {
    const info = this._data();
    if (!this._hass) return null;
    const hit = Object.entries(this._hass.entities || {}).find(([, ent]) => {
      if (info?.deviceId && ent.device_id !== info.deviceId) return false;
      const unique = ent.unique_id || "";
      return unique.endsWith(`_${suffix}`);
    });
    if (hit) return hit[0];
    return Object.keys(this._hass.states).find((id) => id.endsWith(`_${suffix}`)) || null;
  }

  _render() {
    if (!this.shadowRoot) return;
    const data = this._data();
    this.shadowRoot.innerHTML = `
      <style>${styles()}</style>
      ${data ? this._card(data) : this._empty()}
    `;
    this._bind(data);
  }

  _empty() {
    return `
      <ha-card>
        <div class="empty">
          <div class="mark"></div>
          <h2>AEG FSE73768P</h2>
          <p>Add the integration first. This card auto-detects the FSE73768P.</p>
        </div>
      </ha-card>`;
  }

  _card(data) {
    const running = ["running", "airdry", "paused", "delayed"].includes(data.state);
    const live = data.state === "running" || data.state === "airdry";
    return `
      <ha-card class="${live ? "is-running" : ""} ${data.state}">
        <div class="hero">
          <div class="topline">
            <div>
              <div class="eyebrow">AEG · 7000 ComfortLift</div>
              <div class="title">${this._config.name || data.name || "FSE73768P"}</div>
            </div>
            <div class="status-pill ${data.state}">${labelState(data.state)}</div>
          </div>
          <div class="stage">
            ${progressRing(data.progress || 0, live)}
            ${dishwasherSvg(data)}
            <div class="readout">
              <div class="time">${formatRemaining(data.remaining_seconds)}</div>
              <div class="phase">${data.phase_label || PHASE_COPY[data.phase] || "Ready"}</div>
              ${data.current_temperature ? `<div class="temp">${data.current_temperature}°C</div>` : ""}
            </div>
          </div>
          ${ecometer(data.ecometer || 0)}
        </div>
        <div class="programs" role="list">
          ${(data.programs || []).map((p) => programChip(p, data)).join("")}
        </div>
        <div class="extras">
          ${extraBtn("ExtraPower", "extra_power", data)}
          ${extraBtn("GlassCare", "glass_care", data)}
          ${extraBtn("ExtraSilent", "extra_silent", data)}
        </div>
        <div class="actions">
          <button class="ghost" data-act="door">${data.door_open ? "Close door" : "Open door"}</button>
          <button class="ghost" data-act="lift" ${data.door_open ? "" : "disabled"}>ComfortLift</button>
          ${running
            ? `<button class="primary" data-act="pause">${data.state === "paused" ? "Resume" : "Pause"}</button>
               <button class="danger" data-act="cancel">Cancel</button>`
            : `<button class="primary" data-act="start">Start ${data.program_name || "ECO"}</button>`}
        </div>
        <div class="meta">
          <span>${(data.water_l || 0).toFixed(1)} L</span>
          <span>${(data.energy_kwh || 0).toFixed(2)} kWh</span>
          <span>${data.noise_db || 39} dB</span>
          <span class="beam ${data.beam}">TimeBeam</span>
        </div>
      </ha-card>`;
  }

  _bind(data) {
    this.shadowRoot.querySelectorAll("[data-program]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.getAttribute("data-program");
        if (["running", "paused", "airdry", "delayed"].includes(data?.state)) return;
        this._call("start_program", { program: key });
      });
    });
    this.shadowRoot.querySelectorAll("[data-extra]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const extra = btn.getAttribute("data-extra");
        const switchId = this._entity(extra);
        if (switchId) {
          this._hass.callService("switch", "toggle", { entity_id: switchId });
        }
      });
    });
    const act = (name, fn) => {
      const el = this.shadowRoot.querySelector(`[data-act="${name}"]`);
      if (el) el.addEventListener("click", fn);
    };
    act("start", () => this._call("start_program", { program: data?.program }));
    act("pause", () => this._call(data?.state === "paused" ? "resume" : "pause"));
    act("cancel", () => this._call("cancel"));
    act("door", () => this._call("set_door", { open: !data?.door_open }));
    act("lift", () => {
      const id = this._entity("comfort_lift");
      if (id) this._hass.callService("switch", "toggle", { entity_id: id });
    });
  }
}

function labelState(state) {
  return (
    {
      off: "Off",
      idle: "Ready",
      delayed: "Delayed",
      running: "Running",
      paused: "Paused",
      airdry: "AirDry",
      complete: "Finished",
      error: "Fault",
    }[state] || state
  );
}

function extraBtn(label, key, data) {
  const allowed = (data.available_extras || []).includes(key);
  const on = !!data.extras?.[key];
  return `<button class="chip ${on ? "on" : ""}" data-extra="${key}" ${allowed ? "" : "disabled"}>${label}</button>`;
}

function programChip(program, data) {
  const selected = program.selected || program.key === data.program;
  return `
    <button class="prog ${selected ? "selected" : ""} ${program.my_time ? "mytime" : ""}" data-program="${program.key}" role="listitem">
      <span class="pname">${program.name}</span>
      <span class="ptime">${program.duration_min} min</span>
    </button>`;
}

function ecometer(bars) {
  const n = Math.max(0, Math.min(5, bars));
  return `<div class="eco" title="Ecometer">${[1, 2, 3, 4, 5]
    .map((i) => `<i class="${i <= n ? "lit" : ""}"></i>`)
    .join("")}<span>ECO</span></div>`;
}

function progressRing(progress, live) {
  const r = 148;
  const c = 2 * Math.PI * r;
  const dash = (Math.max(0, Math.min(100, progress)) / 100) * c;
  return `
    <svg class="ring ${live ? "live" : ""}" viewBox="0 0 320 320" aria-hidden="true">
      <circle class="track" cx="160" cy="160" r="${r}" />
      <circle class="value" cx="160" cy="160" r="${r}"
        stroke-dasharray="${dash} ${c}" transform="rotate(-90 160 160)" />
    </svg>`;
}

function dishwasherSvg(data) {
  const running = data.state === "running";
  const airdry = data.state === "airdry";
  const paused = data.state === "paused";
  const open = !!data.door_open;
  const lift = !!data.comfort_lift && open;
  const complete = data.state === "complete";
  const beam = data.beam || "off";
  const light = !!data.interior_light;
  const spray = running && !open;
  return `
    <svg class="machine ${data.state}" viewBox="0 0 320 390" role="img" aria-label="AEG FSE73768P">
      <defs>
        <linearGradient id="cab" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#2a2c31"/>
          <stop offset="1" stop-color="#121316"/>
        </linearGradient>
        <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#d9dde3"/>
          <stop offset="1" stop-color="#8b929c"/>
        </linearGradient>
        <linearGradient id="warm" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#ffe7c2"/>
          <stop offset="1" stop-color="#c9894a"/>
        </linearGradient>
        <radialGradient id="glow" cx="50%" cy="40%" r="60%">
          <stop offset="0" stop-color="#7ad7ff" stop-opacity="0.55"/>
          <stop offset="1" stop-color="#0a3a52" stop-opacity="0"/>
        </radialGradient>
        <filter id="soft" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="6"/>
        </filter>
      </defs>
      <ellipse class="floor-beam ${beam}" cx="160" cy="368" rx="92" ry="14" filter="url(#soft)"/>
      <rect x="54" y="46" width="212" height="292" rx="18" fill="url(#cab)" stroke="#3a3d44" stroke-width="2"/>
      <rect class="panel" x="62" y="54" width="196" height="26" rx="6" fill="#0b0c0e"/>
      <g class="mytime">
        ${[0, 1, 2, 3, 4].map((i) => `<circle cx="${92 + i * 34}" cy="67" r="4.2" fill="${i === myTimeIndex(data.program) ? RED : "#3d4148"}"/>`).join("")}
      </g>
      <text x="248" y="71" text-anchor="end" fill="#8b9098" font-size="8" font-family="ui-sans-serif,system-ui">FSE73768P</text>
      <g class="cavity">
        <rect x="74" y="92" width="172" height="228" rx="8" fill="${open || spray || airdry ? "#1c242c" : "#17181c"}"/>
        ${(open || spray || airdry || paused) ? `<rect x="78" y="96" width="164" height="220" rx="6" fill="${light ? "url(#warm)" : "url(#steel)"}" opacity="${light ? 0.55 : 0.22}"/>` : ""}
        ${spray ? `<ellipse cx="160" cy="210" rx="70" ry="18" fill="url(#glow)"/>` : ""}
        ${spray ? sprayArms() : ""}
        ${spray ? droplets() : ""}
        ${open ? baskets(lift, light) : ""}
        ${airdry || complete ? steam() : ""}
      </g>
      ${door(open, airdry || complete, spray)}
      <rect x="148" y="318" width="24" height="8" rx="3" fill="#4a4e56"/>
    </svg>`;
}

function myTimeIndex(program) {
  return { quick: 0, "1h": 1, "1h30": 2, "2h40": 3, eco: 4 }[program] ?? -1;
}

function sprayArms() {
  return `
    <g transform="translate(160 150)">
      <g class="arm-spin upper">
        <rect x="-52" y="-3" width="104" height="6" rx="3" fill="#b9c2cc"/>
        <circle r="7" fill="#e8eef4"/>
        <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="2.8s" repeatCount="indefinite"/>
      </g>
    </g>
    <g transform="translate(160 268)">
      <g class="arm-spin lower">
        <rect x="-60" y="-3.5" width="120" height="7" rx="3.5" fill="#c5ced8"/>
        <circle r="8" fill="#eef3f7"/>
        <animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="3.6s" repeatCount="indefinite"/>
      </g>
    </g>`;
}

function droplets() {
  return Array.from({ length: 10 }, (_, i) => {
    const x = 100 + (i * 13) % 120;
    const delay = (i * 0.18).toFixed(2);
    return `<circle class="drop" cx="${x}" cy="130" r="2.4" style="animation-delay:${delay}s"/>`;
  }).join("");
}

function baskets(lift, light) {
  const y = lift ? 168 : 214;
  return `
    <g class="baskets">
      <rect x="92" y="118" width="136" height="36" rx="3" fill="none" stroke="${light ? "#fff6e8" : "#9aa4b0"}" stroke-width="1.4"/>
      <rect class="lower-basket" x="88" y="${y}" width="144" height="44" rx="3" fill="none" stroke="${light ? "#fff6e8" : "#9aa4b0"}" stroke-width="1.6"/>
      ${lift ? `<path d="M96 ${y + 44} L96 258 L224 258 L224 ${y + 44}" fill="none" stroke="#6f7782" stroke-width="1.2"/>` : ""}
    </g>`;
}

function steam() {
  return `
    <g class="steam">
      <path d="M120 120 c8 -18 4 -28 0 -40" />
      <path d="M160 112 c10 -20 2 -32 -2 -46" />
      <path d="M200 124 c7 -16 3 -26 -1 -38" />
    </g>`;
}

function door(open, ajar, cutaway) {
  if (cutaway && !open) {
    return `
      <g class="door cutaway" opacity="0.18">
        <rect x="74" y="92" width="172" height="228" rx="8" fill="none" stroke="#9aa4b0" stroke-dasharray="6 6"/>
      </g>`;
  }
  if (open) {
    const tilt = ajar ? 18 : 0;
    return `
      <g class="door open" transform="translate(74 320) rotate(${26 + tilt})">
        <rect x="0" y="-8" width="172" height="118" rx="6" fill="#1a1c20" stroke="#4a4e56"/>
        <rect x="12" y="70" width="40" height="6" rx="3" fill="#6a707a"/>
      </g>`;
  }
  return `
    <g class="door closed">
      <rect x="74" y="92" width="172" height="228" rx="8" fill="#1e2025" stroke="#3e424a" opacity="0.92"/>
      <rect x="146" y="196" width="28" height="6" rx="3" fill="#6a707a"/>
    </g>`;
}

function styles() {
  return `
    :host { display: block; }
    ha-card {
      background:
        radial-gradient(1200px 280px at 50% -40%, rgba(200,16,46,0.22), transparent 55%),
        linear-gradient(180deg, #16171b 0%, #0e0f12 100%);
      color: #f4f5f7;
      border-radius: 24px;
      overflow: hidden;
      padding: 18px 18px 16px;
      border: 1px solid rgba(255,255,255,0.06);
    }
    ha-card.is-running {
      box-shadow: 0 0 0 1px rgba(200,16,46,0.35), 0 18px 50px rgba(200,16,46,0.18);
    }
    .topline { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
    .eyebrow { font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: #9aa0aa; }
    .title { font-size: 22px; font-weight: 650; margin-top: 2px; }
    .status-pill {
      border-radius: 999px; padding: 6px 12px; font-size: 12px; font-weight: 600;
      background: rgba(255,255,255,0.08); color: #d0d4dc;
    }
    .status-pill.running, .status-pill.airdry { background: ${RED}; color: white; }
    .status-pill.complete { background: #1f8a4c; color: white; }
    .status-pill.error { background: #a61b1b; color: white; }
    .stage { position: relative; height: 340px; display: grid; place-items: center; margin-top: 4px; }
    .ring { position: absolute; width: 300px; height: 300px; top: 8px; pointer-events: none; }
    .ring .track { fill: none; stroke: rgba(255,255,255,0.08); stroke-width: 7; }
    .ring .value { fill: none; stroke: ${RED}; stroke-width: 7; stroke-linecap: round; transition: stroke-dasharray 0.6s ease; }
    .ring.live .value { filter: drop-shadow(0 0 8px ${RED}); }
    .machine { width: 250px; height: 304px; position: relative; z-index: 1; }
    .readout { position: absolute; right: 8px; bottom: 18px; text-align: right; }
    .time { font-size: 28px; font-weight: 700; letter-spacing: -0.03em; }
    .phase { font-size: 13px; color: #b4b9c2; }
    .temp { font-size: 12px; color: ${RED}; font-weight: 600; margin-top: 2px; }
    .eco { display: flex; align-items: center; gap: 6px; justify-content: center; margin: 2px 0 12px; }
    .eco i { width: 18px; height: 8px; border-radius: 99px; background: #2a2e34; display: block; }
    .eco i.lit { background: #3ddc84; box-shadow: 0 0 8px #3ddc84; }
    .eco span { font-size: 11px; letter-spacing: 0.14em; color: #8b9098; }
    .programs { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
    .prog {
      background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.06);
      color: inherit; border-radius: 14px; padding: 10px 8px; cursor: pointer; text-align: left;
    }
    .prog.selected { border-color: ${RED}; background: rgba(200,16,46,0.18); }
    .pname { display: block; font-weight: 650; font-size: 13px; }
    .ptime { display: block; font-size: 11px; color: #9aa0aa; margin-top: 2px; }
    .extras, .actions, .meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    .chip, .ghost, .primary, .danger {
      border: 0; border-radius: 999px; padding: 9px 14px; cursor: pointer; font-weight: 600; color: inherit;
    }
    .chip { background: rgba(255,255,255,0.06); }
    .chip.on { background: ${RED}; }
    .chip:disabled, .ghost:disabled { opacity: 0.35; cursor: not-allowed; }
    .ghost { background: rgba(255,255,255,0.08); }
    .primary { background: ${RED}; color: white; margin-left: auto; }
    .danger { background: #3a1216; color: #ffb4b4; }
    .meta { color: #9aa0aa; font-size: 12px; justify-content: space-between; }
    .beam.red { color: #ff5a5a; }
    .beam.green { color: #3ddc84; }
    .empty { padding: 28px 12px 18px; text-align: center; }
    .mark { width: 42px; height: 8px; background: ${RED}; border-radius: 99px; margin: 0 auto 12px; }
    .arm { transform-origin: 0 0; transform-box: fill-box; }
    .is-running .arm.upper { animation: spin 2.8s linear infinite; }
    .is-running .arm.lower { animation: spin 3.6s linear infinite reverse; }
    .drop { fill: #8be7ff; animation: fall 1.6s linear infinite; }
    .steam path { fill: none; stroke: rgba(255,255,255,0.45); stroke-width: 2; stroke-linecap: round;
      animation: rise 2.8s ease-in-out infinite; }
    .floor-beam { fill: transparent; }
    .floor-beam.red { fill: ${RED}; opacity: 0.85; animation: pulse 1.6s ease-in-out infinite; }
    .floor-beam.green { fill: #3ddc84; opacity: 0.9; }
    .floor-beam.flash { fill: ${RED}; animation: flash 0.7s step-end infinite; }
    .lower-basket { transition: y 0.45s ease; }
    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes fall { from { transform: translateY(0); opacity: 0.9; } to { transform: translateY(140px); opacity: 0; } }
    @keyframes rise { 0%,100% { opacity: 0.15; } 50% { opacity: 0.7; } }
    @keyframes pulse { 0%,100% { opacity: 0.35; } 50% { opacity: 0.95; } }
    @keyframes flash { 50% { opacity: 0.15; } }
    @media (max-width: 520px) {
      .programs { grid-template-columns: repeat(2, 1fr); }
      .readout { right: 0; left: 0; text-align: center; bottom: 0; }
    }
    @media (prefers-reduced-motion: reduce) {
      .arm, .drop, .steam path, .floor-beam { animation: none !important; }
    }
  `;
}

class AEGCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._render();
  }
  set hass(hass) {
    this._hass = hass;
    this._render();
  }
  _render() {
    if (!this.isConnected) return;
    const entities = this._hass
      ? Object.values(this._hass.states)
          .filter((s) => s.attributes?.model === "FSE73768P")
          .map((s) => s.entity_id)
      : [];
    this.innerHTML = `
      <div style="padding:8px 0;display:grid;gap:8px;">
        <label>Name<br><input id="n" type="text" value="${this._config?.name || ""}" style="width:100%"></label>
        <label>State entity<br>
          <select id="e" style="width:100%">
            <option value="">Auto-detect</option>
            ${entities.map((id) => `<option value="${id}" ${this._config?.entity === id ? "selected" : ""}>${id}</option>`).join("")}
          </select>
        </label>
      </div>`;
    this.querySelector("#n")?.addEventListener("change", (ev) => this._fire({ ...this._config, name: ev.target.value }));
    this.querySelector("#e")?.addEventListener("change", (ev) => this._fire({ ...this._config, entity: ev.target.value || undefined }));
  }
  _fire(config) {
    this._config = config;
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
  }
}

customElements.define(CARD_TAG, AEGFSE73768PCard);
customElements.define(EDITOR_TAG, AEGCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: CARD_TAG,
  name: "AEG FSE73768P",
  description: "Tesla-style visual card for the AEG FSE73768P dishwasher.",
  preview: true,
});
