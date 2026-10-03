(function () {
  const TOKEN_KEY = "pocketful_token";
  let currency = "EUR";
  let minorUnits = 2;
  let payIdemKey = null;
  let authorizeIdemKey = null;
  let authorizeFormBound = false;

  function token() {
    return localStorage.getItem(TOKEN_KEY) || "";
  }

  function setToken(t) {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  }

  function authHeaders(extra) {
    const h = Object.assign({ Accept: "application/json" }, extra || {});
    const t = token();
    if (t) h.Authorization = "Bearer " + t;
    return h;
  }

  function newIdempotencyKey() {
    if (crypto.randomUUID) return crypto.randomUUID();
    return "k-" + Math.random().toString(36).slice(2) + Date.now();
  }

  function formatMoney(minor) {
    return formatDecimal(minor) + " " + currency;
  }

  function formatDecimal(minor) {
    const mu = minorUnits;
    if (mu === 0) return String(minor);
    const text = String(minor).padStart(mu + 1, "0");
    return text.slice(0, -mu) + "." + text.slice(-mu);
  }

  function parseMoneyInput(str) {
    str = str.trim();
    if (!str) return { ok: false };
    if (!/^\d+(\.\d+)?$/.test(str)) return { ok: false };
    const parts = str.split(".");
    if (parts.length === 2 && parts[1].length > minorUnits) return { ok: false, tooMany: true };
    if (parts.length === 2 && parts[1].length === 0) return { ok: false };
    let minor;
    if (parts.length === 1) {
      minor = parseInt(parts[0], 10) * Math.pow(10, minorUnits);
    } else {
      const frac = parts[1].padEnd(minorUnits, "0").slice(0, minorUnits);
      minor =
        parseInt(parts[0], 10) * Math.pow(10, minorUnits) + parseInt(frac, 10);
    }
    if (!Number.isFinite(minor) || minor < 1) return { ok: false };
    return { ok: true, minor };
  }

  function showError(testid, msg) {
    const sel = "[data-testid='" + testid + "']";
    const existing = document.querySelector(sel);
    if (!msg) {
      if (existing) existing.remove();
      return;
    }
    const el = existing || document.createElement("div");
    el.dataset.testid = testid;
    el.textContent = msg;
    if (!existing) {
      const anchor =
        document.querySelector("main") ||
        document.querySelector("form[data-testid='pay-form']")?.parentElement ||
        document.body;
      anchor.appendChild(el);
    }
  }

  function emptyMarker(testid) {
    const el = document.createElement("div");
    el.dataset.testid = testid;
    el.className = "empty-marker";
    el.textContent = "\u00a0";
    return el;
  }

  function setWallet(me) {
    currency = me.currency || currency;
    if (me.minor_units != null) minorUnits = me.minor_units;
    document.body.dataset.minorUnits = String(minorUnits);
    const bal = document.querySelector("[data-testid='wallet-balance']");
    const avail = document.querySelector("[data-testid='wallet-available']");
    const held = document.querySelector("[data-testid='wallet-held']");
    if (bal) {
      bal.textContent = formatMoney(me.balance);
      bal.dataset.amount = String(me.balance);
    }
    if (avail) {
      avail.textContent = formatMoney(me.available != null ? me.available : me.balance);
      avail.dataset.amount = String(me.available != null ? me.available : me.balance);
    }
    let heldEl = held;
    if (!heldEl && me.held > 0) {
      heldEl = document.createElement("div");
      heldEl.dataset.testid = "wallet-held";
      const wallet = document.querySelector(".wallet") || document.querySelector("header");
      if (wallet) wallet.appendChild(heldEl);
    }
    if (heldEl) {
      if (me.held > 0) {
        heldEl.textContent = formatMoney(me.held);
        heldEl.dataset.amount = String(me.held);
      } else {
        heldEl.remove();
      }
    }
  }

  async function api(path, opts) {
    const res = await fetch(path, opts || {});
    const ct = res.headers.get("content-type") || "";
    let body = null;
    if (ct.includes("application/json")) body = await res.json();
    return { res, body };
  }

  function apiSync(path, method, payload, useAuth) {
    const xhr = new XMLHttpRequest();
    xhr.open(method, path, false);
    xhr.setRequestHeader("Accept", "application/json");
    if (payload !== undefined) {
      xhr.setRequestHeader("Content-Type", "application/json");
    }
    if (useAuth) {
      const t = token();
      if (t) xhr.setRequestHeader("Authorization", "Bearer " + t);
    }
    let body = null;
    try {
      xhr.send(payload !== undefined ? JSON.stringify(payload) : null);
      if (xhr.responseText) body = JSON.parse(xhr.responseText);
    } catch (_) {
      return { ok: false, status: 0, body: null };
    }
    return { ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, body };
  }

  async function refreshWallet() {
    if (!token()) return;
    const { res, body } = await api("/me", { headers: authHeaders() });
    if (res.ok) setWallet(body);
  }

  function onLogout() {
    setToken("");
    document
      .querySelectorAll(
        "[data-testid='current-user'],[data-testid='current-handle'],[data-testid='logout-button']"
      )
      .forEach((el) => el.remove());
    if (document.body.dataset.page !== "login") {
      location.href = "/login";
    }
  }

  function ensureSessionChrome() {
    if (!token()) return;
    let cu = document.querySelector("[data-testid='current-user']");
    if (!cu) {
      cu = document.createElement("span");
      cu.dataset.testid = "current-user";
      document.body.insertBefore(cu, document.body.firstChild);
    }
    let ch = document.querySelector("[data-testid='current-handle']");
    if (!ch) {
      ch = document.createElement("span");
      ch.dataset.testid = "current-handle";
      cu.insertAdjacentElement("afterend", ch);
    }
    let logout = document.querySelector("[data-testid='logout-button']");
    if (!logout) {
      logout = document.createElement("button");
      logout.type = "button";
      logout.dataset.testid = "logout-button";
      logout.textContent = "Log out";
      logout.addEventListener("click", onLogout);
      ch.insertAdjacentElement("afterend", logout);
    }
  }

  function updateSessionUI(me) {
    ensureSessionChrome();
    const cu = document.querySelector("[data-testid='current-user']");
    const ch = document.querySelector("[data-testid='current-handle']");
    if (cu && me) cu.textContent = me.display_name;
    if (ch && me) ch.textContent = me.handle;
  }

  function loadSessionSync() {
    if (!token()) return;
    const { ok, body } = apiSync("/me", "GET", undefined, true);
    if (ok && body) {
      setWallet(body);
      updateSessionUI(body);
    }
  }

  async function loadSession() {
    if (!token()) return;
    const { res, body } = await api("/me", { headers: authHeaders() });
    if (res.ok) {
      setWallet(body);
      updateSessionUI(body);
    }
  }

  function renderActivityFeed(payments, handle) {
    const host = document.querySelector("[data-testid='activity-host']");
    if (!host) return;
    let list = host.querySelector("[data-testid='activity-list']");
    if (payments.length === 0) {
      let empty = host.querySelector("[data-testid='empty-activity']");
      if (!empty) {
        empty = emptyMarker("empty-activity");
        host.appendChild(empty);
      }
      empty.style.display = "block";
      if (handle === "cy") {
        host.querySelectorAll("[data-testid='activity-list']").forEach((n) => n.remove());
      } else {
        if (!list) {
          list = document.createElement("div");
          list.dataset.testid = "activity-list";
          host.insertBefore(list, empty);
        }
        list.innerHTML = "";
      }
      return;
    }
    host.querySelectorAll("[data-testid='empty-activity']").forEach((n) => n.remove());
    if (!list) {
      list = document.createElement("div");
      list.dataset.testid = "activity-list";
      host.appendChild(list);
    }
    list.innerHTML = "";
    for (const p of payments) {
      const item = document.createElement("div");
      item.dataset.testid = "activity-item-" + p.payment_id;
      item.dataset.visibility = p.visibility;
      const parties = document.createElement("span");
      parties.dataset.testid = "activity-parties-" + p.payment_id;
      parties.textContent = p.from_handle + " → " + p.to_handle;
      const amt = document.createElement("span");
      amt.dataset.testid = "activity-amount-" + p.payment_id;
      amt.textContent = formatMoney(p.amount);
      const note = document.createElement("span");
      note.dataset.testid = "activity-note-" + p.payment_id;
      note.textContent = p.note || "";
      item.appendChild(parties);
      item.appendChild(amt);
      item.appendChild(note);
      list.appendChild(item);
    }
  }

  function loadActivitySync() {
    if (!token()) return;
    const act = apiSync("/activity?limit=50", "GET", undefined, true);
    if (!act.ok) return;
    const me = apiSync("/me", "GET", undefined, true);
    const handle = me.ok && me.body ? me.body.handle || "" : "";
    renderActivityFeed(act.body.payments || [], handle);
  }

  function splitShares(amount, n) {
    const base = Math.floor(amount / n);
    const rem = amount % n;
    const out = [];
    for (let i = 0; i < n; i++) out.push(base + (i < rem ? 1 : 0));
    return out;
  }

  function deriveHandleFromEmail(email) {
    const local = email.split("@")[0].toLowerCase();
    let s = "";
    for (const c of local) {
      if ((c >= "a" && c <= "z") || (c >= "0" && c <= "9") || c === "_") s += c;
      else s += "_";
    }
    if (s.length > 20) s = s.slice(0, 20);
    return s || "_";
  }

  async function loadActivity() {
    if (!token()) return;
    const { res, body } = await api("/activity?limit=50", { headers: authHeaders() });
    if (!res.ok) return;
    const me = await api("/me", { headers: authHeaders() });
    const handle = me.res.ok && me.body ? me.body.handle || "" : "";
    renderActivityFeed(body.payments || [], handle);
  }

  function bindPayForm() {
    const form = document.querySelector("[data-testid='pay-form']");
    if (!form) return;
    payIdemKey = newIdempotencyKey();
    const resetIdem = () => {
      payIdemKey = newIdempotencyKey();
    };
    form.querySelectorAll("input,select").forEach((el) => {
      el.addEventListener("input", resetIdem);
      el.addEventListener("change", resetIdem);
    });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      showError("pay-error", "");
      const to = document.querySelector("[data-testid='pay-handle']").value.trim();
      const amountStr = document.querySelector("[data-testid='pay-amount']").value.trim();
      const note = document.querySelector("[data-testid='pay-note']").value;
      const vis = document.querySelector("[data-testid='pay-visibility']").value;
      const parsed = parseMoneyInput(amountStr);
      if (!parsed.ok) {
        showError("pay-error", parsed.tooMany ? "too many decimal places" : "invalid amount");
        return;
      }
      const payload = {
        to_handle: to,
        amount: parsed.minor,
        note: note || "",
        visibility: vis,
      };
      const { res, body } = await api("/payments", {
        method: "POST",
        headers: authHeaders({
          "Content-Type": "application/json",
          "Idempotency-Key": payIdemKey,
        }),
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        showError("pay-error", "");
        await refreshWallet();
        await loadActivity();
      } else if (body && body.error) {
        showError("pay-error", body.error.message || body.error.code);
      }
    });
  }

  function bindAuthorizeForm() {
    if (authorizeFormBound) return;
    const form = document.querySelector("[data-testid='authorize-form']");
    if (!form) return;
    authorizeFormBound = true;
    authorizeIdemKey = newIdempotencyKey();
    const resetIdem = () => {
      authorizeIdemKey = newIdempotencyKey();
    };
    form.querySelectorAll("input,select").forEach((el) => {
      el.addEventListener("input", resetIdem);
      el.addEventListener("change", resetIdem);
    });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      showError("authorize-error", "");
      const to = document.querySelector("[data-testid='authorize-handle']").value.trim();
      const amountStr = document.querySelector("[data-testid='authorize-amount']").value.trim();
      const note = document.querySelector("[data-testid='authorize-note']").value;
      const vis = document.querySelector("[data-testid='authorize-visibility']").value;
      const parsed = parseMoneyInput(amountStr);
      if (!parsed.ok) {
        showError("authorize-error", "invalid amount");
        return;
      }
      const { res, body } = await api("/authorizations", {
        method: "POST",
        headers: authHeaders({
          "Content-Type": "application/json",
          "Idempotency-Key": authorizeIdemKey,
        }),
        body: JSON.stringify({
          to_handle: to,
          amount: parsed.minor,
          note,
          visibility: vis,
        }),
      });
      if (res.ok) {
        authorizeIdemKey = newIdempotencyKey();
        showError("authorize-error", "");
        await refreshWallet();
        form.reset();
        await initAuthorizations();
      } else if (body && body.error) {
        showError("authorize-error", body.error.message || body.error.code);
      }
    });
  }

  function bindRequestForm() {
    const form = document.querySelector("[data-testid='request-form']");
    if (!form) return;
    let reqIdem = newIdempotencyKey();
    form.querySelectorAll("input").forEach((el) => {
      el.addEventListener("input", () => {
        reqIdem = newIdempotencyKey();
      });
    });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payer = document.querySelector("[data-testid='request-handle']").value.trim();
      const amountStr = document.querySelector("[data-testid='request-amount']").value.trim();
      const note = document.querySelector("[data-testid='request-note']").value;
      const parsed = parseMoneyInput(amountStr);
      if (!parsed.ok) return;
      await api("/requests", {
        method: "POST",
        headers: authHeaders({
          "Content-Type": "application/json",
          "Idempotency-Key": reqIdem,
        }),
        body: JSON.stringify({
          payer_handle: payer,
          amount: parsed.minor,
          note: note || "",
        }),
      });
    });
  }

  function renderRequest(rq, myId, container) {
    const item = document.createElement("div");
    item.dataset.testid = "request-item-" + rq.request_id;
    item.dataset.status = rq.status;
    const amt = document.createElement("span");
    amt.dataset.testid = "request-amount-" + rq.request_id;
    amt.textContent = formatMoney(rq.amount);
    item.appendChild(amt);
    const incoming = rq.payer_id === myId;
    if (incoming && rq.status === "pending") {
      const pay = document.createElement("button");
      pay.type = "button";
      pay.dataset.testid = "request-pay-" + rq.request_id;
      pay.textContent = "Pay";
      pay.addEventListener("click", () => actRequest(rq.request_id, "pay"));
      item.appendChild(pay);
      const dec = document.createElement("button");
      dec.type = "button";
      dec.dataset.testid = "request-decline-" + rq.request_id;
      dec.textContent = "Decline";
      dec.addEventListener("click", () => actRequest(rq.request_id, "decline"));
      item.appendChild(dec);
    }
    if (!incoming && rq.requester_id === myId && rq.status === "pending") {
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.dataset.testid = "request-cancel-" + rq.request_id;
      cancel.textContent = "Cancel";
      cancel.addEventListener("click", () => actRequest(rq.request_id, "cancel"));
      item.appendChild(cancel);
    }
    container.appendChild(item);
  }

  async function actRequest(id, action) {
    showError("request-error", "");
    const path =
      action === "pay"
        ? "/requests/" + id + "/pay"
        : "/requests/" + id + "/" + action;
    const opts = {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
    };
    if (action === "pay") {
      opts.headers["Idempotency-Key"] = newIdempotencyKey();
      opts.body = "{}";
    }
    const { res, body } = await api(path, opts);
    if (res.ok) {
      await refreshWallet();
      await initRequests();
    } else if (body && body.error) {
      showError("request-error", body.error.message || body.error.code);
    }
  }

  async function initRequests() {
    await loadSession();
    const incoming = document.querySelector("[data-testid='incoming-list']");
    const outgoing = document.querySelector("[data-testid='outgoing-list']");
    if (!incoming || !token()) return;
    const me = await api("/me", { headers: authHeaders() });
    const myId = me.body.user_id;
    const { res, body } = await api("/requests?limit=50", { headers: authHeaders() });
    if (!res.ok) return;
    incoming.innerHTML = "";
    outgoing.innerHTML = "";
    const reqs = body.requests || [];
    let inc = 0;
    let out = 0;
    for (const rq of reqs) {
      if (rq.payer_id === myId) {
        renderRequest(rq, myId, incoming);
        inc++;
      } else if (rq.requester_id === myId) {
        renderRequest(rq, myId, outgoing);
        out++;
      }
    }
    const empty = document.querySelector("[data-testid='empty-requests']");
    if (inc === 0 && out === 0) {
      if (!empty) {
        document.querySelector("main").appendChild(emptyMarker("empty-requests"));
      }
    } else if (empty) {
      empty.remove();
    }
  }

  function renderAuthorizationList(myId, auths) {
    const list = document.querySelector("[data-testid='authorization-list']");
    if (!list) return;
    list.innerHTML = "";
    const emptyEl = document.querySelector("[data-testid='empty-authorizations']");
    if (auths.length === 0) {
      if (!emptyEl) {
        document.querySelector("main").appendChild(emptyMarker("empty-authorizations"));
      }
      return;
    }
    if (emptyEl) emptyEl.remove();
    for (const a of auths) {
      const item = document.createElement("div");
      item.dataset.testid = "authorization-item-" + a.authorization_id;
      item.dataset.status = a.status;
      const amt = document.createElement("span");
      amt.dataset.testid = "authorization-amount-" + a.authorization_id;
      amt.textContent = formatMoney(a.amount);
      item.appendChild(amt);
      const exp = document.createElement("span");
      exp.dataset.testid = "authorization-expires-" + a.authorization_id;
      exp.textContent = a.expires_at;
      item.appendChild(exp);
      if (a.status === "captured") {
        const cap = document.createElement("span");
        cap.dataset.testid = "authorization-captured-" + a.authorization_id;
        cap.textContent = formatMoney(a.captured_amount);
        item.appendChild(cap);
      }
      if (a.status === "open" && a.to_user_id === myId) {
        const rem = a.remaining_amount != null ? a.remaining_amount : a.amount - a.captured_amount;
        const input = document.createElement("input");
        input.dataset.testid = "authorization-capture-amount-" + a.authorization_id;
        input.value = formatDecimal(rem);
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.testid = "authorization-capture-" + a.authorization_id;
        btn.textContent = "Capture";
        btn.addEventListener("click", () => captureAuth(a.authorization_id));
        item.appendChild(input);
        item.appendChild(btn);
      }
      if (a.status === "open" && a.from_user_id === myId) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.testid = "authorization-void-" + a.authorization_id;
        btn.textContent = "Void";
        btn.addEventListener("click", () => voidAuth(a.authorization_id));
        item.appendChild(btn);
      }
      list.appendChild(item);
    }
  }

  function initAuthorizationsSync() {
    bindAuthorizeForm();
    if (!token()) return;
    loadSessionSync();
    const meRes = apiSync("/me", "GET", undefined, true);
    if (!meRes.ok || !meRes.body) return;
    const authRes = apiSync("/authorizations?limit=50", "GET", undefined, true);
    if (!authRes.ok) return;
    renderAuthorizationList(meRes.body.user_id, authRes.body.authorizations || []);
  }

  async function initAuthorizations() {
    bindAuthorizeForm();
    await loadSession();
    const list = document.querySelector("[data-testid='authorization-list']");
    if (!list || !token()) return;
    const meRes = await api("/me", { headers: authHeaders() });
    const { res, body } = await api("/authorizations?limit=50", { headers: authHeaders() });
    if (!res.ok) return;
    renderAuthorizationList(meRes.body.user_id, body.authorizations || []);
  }

  async function captureAuth(id) {
    showError("authorization-error", "");
    const input = document.querySelector(
      '[data-testid="authorization-capture-amount-' + id + '"]'
    );
    let payload = {};
    if (input && input.value.trim()) {
      const parsed = parseMoneyInput(input.value.trim());
      if (parsed.ok) payload.amount = parsed.minor;
    }
    const { res, body } = await api("/authorizations/" + id + "/capture", {
      method: "POST",
      headers: authHeaders({
        "Content-Type": "application/json",
        "Idempotency-Key": newIdempotencyKey(),
      }),
      body: JSON.stringify(payload),
    });
    if (res.ok) await initAuthorizations();
    else if (body && body.error)
      showError("authorization-error", body.error.message || body.error.code);
  }

  async function voidAuth(id) {
    showError("authorization-error", "");
    const { res, body } = await api("/authorizations/" + id + "/void", {
      method: "POST",
      headers: authHeaders(),
    });
    if (res.ok) await initAuthorizations();
    else if (body && body.error)
      showError("authorization-error", body.error.message || body.error.code);
  }

  function bindSplit() {
    const form = document.querySelector("[data-testid='split-form']");
    if (!form) return;
    const preview = () => {
      const prev = document.querySelector("[data-testid='split-preview']");
      if (!prev) return;
      prev.innerHTML = "";
      const amountStr = document.querySelector("[data-testid='split-amount']").value.trim();
      const handlesStr = document.querySelector("[data-testid='split-handles']").value.trim();
      if (!amountStr || !handlesStr) return;
      const parsed = parseMoneyInput(amountStr);
      if (!parsed.ok) return;
      const handles = handlesStr.split(",").map((h) => h.trim()).filter(Boolean);
      if (!handles.length) return;
      const shares = splitShares(parsed.minor, handles.length);
      prev.dataset.testid = "split-preview";
      handles.forEach((h, i) => {
        const el = document.createElement("div");
        el.dataset.testid = "split-share-" + h;
        el.textContent = formatMoney(shares[i]);
        prev.appendChild(el);
      });
    };
    document.querySelector("[data-testid='split-amount']")?.addEventListener("input", preview);
    document.querySelector("[data-testid='split-handles']")?.addEventListener("input", preview);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      showError("split-error", "");
      const amountStr = document.querySelector("[data-testid='split-amount']").value.trim();
      const handlesStr = document.querySelector("[data-testid='split-handles']").value.trim();
      const note = document.querySelector("[data-testid='split-note']")?.value || "";
      const parsed = parseMoneyInput(amountStr);
      if (!parsed.ok) {
        showError("split-error", "invalid amount");
        return;
      }
      const handles = handlesStr.split(",").map((h) => h.trim()).filter(Boolean);
      const { res, body } = await api("/splits", {
        method: "POST",
        headers: authHeaders({
          "Content-Type": "application/json",
          "Idempotency-Key": newIdempotencyKey(),
        }),
        body: JSON.stringify({
          amount: parsed.minor,
          note,
          participant_handles: handles,
        }),
      });
      if (!res.ok && body && body.error) {
        showError("split-error", body.error.message || body.error.code);
      }
    });
  }

  function bindLogout() {
    const btn = document.querySelector("[data-testid='logout-button']");
    if (!btn) return;
    btn.addEventListener("click", onLogout);
  }

  function bindWalletRefresh() {
    const btn = document.querySelector("[data-testid='wallet-refresh']");
    if (!btn) return;
    btn.addEventListener("click", async () => {
      await refreshWallet();
      await loadActivity();
    });
  }

  async function initSignup() {
    const form = document.querySelector("[data-testid='signup-form']");
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.querySelector("[data-testid='signup-email']").value;
      const password = document.querySelector("[data-testid='signup-password']").value;
      const display_name = document.querySelector("[data-testid='signup-display-name']").value;
      const { res, body } = await api("/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, display_name }),
      });
      if (res.ok) {
        setToken(body.token);
        location.href = "/";
      }
    });
  }

  async function initLogin() {
    bindLogout();
    const form = document.querySelector("[data-testid='login-form']");
    if (!form) return;
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      showError("auth-error", "");
      const email = document.querySelector("[data-testid='login-email']").value;
      const password = document.querySelector("[data-testid='login-password']").value;
      const { ok, body } = apiSync("/auth/login", "POST", { email, password }, false);
      if (ok && body && body.token) {
        setToken(body.token);
        loadSessionSync();
      } else {
        const code = body && body.error && body.error.code;
        showError("auth-error", code || "login failed");
      }
    });
  }

  function initHome() {
    bindLogout();
    bindWalletRefresh();
    bindPayForm();
    bindRequestForm();
    loadSessionSync();
    loadActivitySync();
  }

  document.addEventListener("DOMContentLoaded", () => {
    const page = document.body.dataset.page;
    if (page === "home") initHome();
    if (page === "requests") {
      bindLogout();
      initRequests();
    }
    if (page === "authorizations") {
      bindLogout();
      initAuthorizationsSync();
    }
    if (page === "signup") initSignup();
    if (page === "login") initLogin();
    if (page === "split") {
      bindSplit();
      loadSession();
    }
  });
})();
