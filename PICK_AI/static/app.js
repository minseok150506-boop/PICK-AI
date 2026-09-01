
let seasonalRefreshTimer = null;

const state = {
  chats: [],
  currentChatId: null,
  messages: [],
  sending: false,
  abortController: null,
  stopRequested: false,
  jobPollers: {},
  settings: {
    selected_model: "auto",
    web_mode: "auto",
    compact_mode: 0,
    seasonal_override: "auto"
  },
  models: [],
  languages: {},
  selectedLanguage: "auto"
};

const $ = id => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || "";
}

async function api(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const method = String(options.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = csrfToken();
    if (token) headers.set("X-CSRF-Token", token);
  }

  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers
  });

  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    if (!response.ok) throw new Error(`서버 오류 (${response.status})`);
    return {ok: true, text};
  }

  if (response.status === 401) {
    location.href = "/login";
    throw new Error("로그인이 필요합니다.");
  }
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `요청 실패 (${response.status})`);
  }
  return data;
}

function showToast(message) {
  const toast = $("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(window.__pickToast);
  window.__pickToast = setTimeout(() => toast.classList.remove("show"), 2200);
}

function setScreen(id) {
  document.querySelectorAll(".screen").forEach(el => el.classList.remove("active"));
  const target = $(id);
  if (target) target.classList.add("active");
}

function openSidebar() {
  $("sidebar")?.classList.add("open");
  $("sidebarOverlay")?.classList.add("show");
}
function closeSidebar() {
  $("sidebar")?.classList.remove("open");
  $("sidebarOverlay")?.classList.remove("show");
}

function autoGrow(el) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 180) + "px";
}

function getActiveBackgroundJob() {
  const rows = state.messages
    .filter(m => Number(m.__jobId) && ["queued", "running"].includes(String(m.__jobStatus || "")))
    .filter(m => !m.__cancelRequested);
  rows.sort((a, b) => {
    const ar = a.__jobStatus === "running" ? 0 : 1;
    const br = b.__jobStatus === "running" ? 0 : 1;
    if (ar !== br) return ar - br;
    return Number(a.__jobId) - Number(b.__jobId);
  });
  return rows[0] || null;
}

function responseIsActive() {
  return Boolean(state.sending || getActiveBackgroundJob());
}

function composerAction(active, text) {
  const hasText = Boolean(String(text || "").trim());
  if (hasText) return "send";
  if (active) return "stop";
  return "disabled";
}

function updateSendButtons() {
  const h = $("homeSendBtn");
  const s = $("sendBtn");
  const active = responseIsActive();

  if (h) {
    const action = composerAction(active, $("homeInput")?.value || "");
    h.disabled = action === "disabled";
    h.textContent = action === "stop" ? "■" : "↑";
    h.setAttribute("aria-label", action === "stop" ? "답변 중지" : "전송");
    h.title = action === "stop" ? "답변 중지" : "전송";
  }

  if (s) {
    const action = composerAction(active, $("messageInput")?.value || "");
    s.disabled = action === "disabled";
    s.textContent = action === "stop" ? "■" : "↑";
    s.setAttribute("aria-label", action === "stop" ? "답변 중지" : "전송");
    s.title = action === "stop" ? "답변 중지" : "전송";
  }
}

function applyCompactMode() {
  document.body.classList.toggle("compact-chat", Boolean(state.settings?.compact_mode));
}

function startNewChatView() {
  state.currentChatId = null;
  state.messages = [];
  localStorage.removeItem("pick:lastChatId");
  if ($("homeInput")) {
    $("homeInput").value = "";
    autoGrow($("homeInput"));
  }
  renderChatList();
  setScreen("homeScreen");
  closeSidebar();
  setTimeout(() => $("homeInput")?.focus(), 30);
}

function renderChatList() {
  const box = $("chatList");
  if (!box) return;
  if (!state.chats.length) {
    box.innerHTML = '<div class="empty-chats">아직 저장된 채팅이 없습니다.</div>';
    return;
  }
  box.innerHTML = state.chats.map(chat => `
    <div class="chat-entry ${Number(chat.id) === Number(state.currentChatId) ? "active" : ""}">
      <button class="chat-open" type="button" data-open-chat="${chat.id}">
        ${escapeHtml(chat.title || "새 채팅")}
      </button>
      <button class="chat-menu-button" type="button" data-chat-menu="${chat.id}">•••</button>
    </div>
  `).join("");
}

function plainInline(text) {
  let out = escapeHtml(text);
  out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
  out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  return out;
}

function markdown(text) {
  const source = String(text || "").replace(/\r\n/g, "\n");
  const blocks = [];
  const tokenized = source.replace(/```([a-zA-Z0-9_+#.-]*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const token = `@@CODE_${blocks.length}@@`;
    blocks.push({lang: lang || "code", code});
    return token;
  });

  const lines = tokenized.split("\n");
  let html = "", list = null;
  const closeList = () => {
    if (list) html += `</${list}>`;
    list = null;
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    const token = line.match(/^@@CODE_(\d+)@@$/);
    if (token) {
      closeList();
      const b = blocks[Number(token[1])];
      html += `<div class="code-block">
        <div class="code-header"><span>${escapeHtml(b.lang)}</span><button type="button" data-copy-code>복사</button></div>
        <pre><code>${escapeHtml(b.code)}</code></pre>
      </div>`;
      continue;
    }

    if (/^###\s+/.test(line)) { closeList(); html += `<h3>${plainInline(line.replace(/^###\s+/, ""))}</h3>`; continue; }
    if (/^##\s+/.test(line)) { closeList(); html += `<h2>${plainInline(line.replace(/^##\s+/, ""))}</h2>`; continue; }
    if (/^#\s+/.test(line)) { closeList(); html += `<h1>${plainInline(line.replace(/^#\s+/, ""))}</h1>`; continue; }

    const ul = line.match(/^\s*[-*]\s+(.+)/);
    const ol = line.match(/^\s*(\d+)\.\s+(.+)/);
    if (ul) {
      if (list !== "ul") { closeList(); list = "ul"; html += "<ul>"; }
      html += `<li>${plainInline(ul[1])}</li>`;
      continue;
    }
    if (ol) {
      const itemNumber = Math.max(1, Number(ol[1]) || 1);
      if (list !== "ol") {
        closeList();
        list = "ol";
        html += `<ol start="${itemNumber}">`;
      }
      html += `<li value="${itemNumber}">${plainInline(ol[2])}</li>`;
      continue;
    }

    closeList();
    html += line.trim() ? `<p>${plainInline(line)}</p>` : "<br>";
  }
  closeList();
  return html;
}

function safeSourceUrl(value) {
  const url = String(value || "").trim();
  return /^https?:\/\//i.test(url) ? url : "";
}

function sourceIconLabel(source) {
  const kind = String(source?.source_type || "").toLowerCase();
  if (kind === "wikipedia") return "W";
  if (kind === "namuwiki") return "N";
  if (kind === "youtube") return "▶";
  if (kind === "news") return "N";
  if (kind === "weather") return "☁";
  try {
    const host = new URL(source.url).hostname.replace(/^www\./, "");
    return (host[0] || "S").toUpperCase();
  } catch (_) {
    return "S";
  }
}

function renderSourceBundle(sources) {
  const rows = Array.isArray(sources)
    ? sources.filter(s => safeSourceUrl(s?.url)).slice(0, 18)
    : [];
  if (!rows.length) return "";

  const icons = rows.slice(0, 4).map(s =>
    `<span class="pick-source-mini">${escapeHtml(sourceIconLabel(s))}</span>`
  ).join("");

  return `
    <details class="pick-sources">
      <summary>
        <span class="pick-source-stack">${icons}</span>
        <span>출처 ${rows.length}개</span>
        <span class="pick-source-chevron">⌄</span>
      </summary>
      <div class="pick-sources-panel">
        ${rows.map((s, i) => {
          const url = safeSourceUrl(s.url);
          const provider = s.provider || "PICK Search";
          const title = s.title || url;
          const published = s.published_at
            ? `<small>${escapeHtml(s.published_at)}</small>`
            : "";
          return `<a class="pick-source-item" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">
            <span class="pick-source-number">${i + 1}</span>
            <span class="pick-source-info">
              <strong>${escapeHtml(provider)}</strong>
              <span>${escapeHtml(title)}</span>
              ${published}
            </span>
            <span class="pick-source-open">↗</span>
          </a>`;
        }).join("")}
      </div>
    </details>`;
}

function renderMessages(scroll = true) {
  const box = $("messageArea");
  if (!box) return;
  if (!state.messages.length) {
    box.innerHTML = '<div class="welcome-chat">메시지를 보내 대화를 시작하세요.</div>';
    return;
  }

  box.innerHTML = state.messages.map((m, index) => {
    const assistant = m.role !== "user";
    return `
      <article class="message-row ${assistant ? "assistant" : "user"}" data-message-index="${index}">
        ${assistant ? '<div class="assistant-avatar">P</div>' : ""}
        <div class="message-body">
          <div class="message-content">${assistant ? markdown(m.content) : escapeHtml(m.content)}</div>
          ${assistant ? renderSourceBundle(m.sources) : ""}
          ${assistant ? `
          <div class="message-actions">
            <button type="button" data-copy-message="${index}">복사</button>
            <button type="button" data-rate-message="${index}" data-rating="1">👍</button>
            <button type="button" data-rate-message="${index}" data-rating="-1">👎</button>
          </div>
          ${Array.isArray(m.__followUps) && m.__followUps.length ? `
            <div class="follow-up-questions">
              ${m.__followUps.map(q => `<button type="button" data-follow-up="${escapeHtml(q)}">${escapeHtml(q)}</button>`).join("")}
            </div>` : ""}` : ""}
        </div>
      </article>`;
  }).join("");

  if (scroll) requestAnimationFrame(() => box.scrollTop = box.scrollHeight);
}

function backgroundJobText(job) {
  if (job?.cancel_requested && ["queued", "running"].includes(job?.status)) {
    return job?.partial_text || "답변 생성을 중지하고 있습니다…";
  }
  if (job?.status === "queued") return "답변을 준비하고 있습니다…";
  if (job?.status === "running") return job.partial_text || "답변을 생성하고 있습니다…";
  return job?.result_text || job?.partial_text || "답변을 준비하고 있습니다…";
}

function mergeBackgroundJobs(jobs) {
  for (const job of (Array.isArray(jobs) ? jobs : [])) {
    const id = Number(job.id);
    if (!id) continue;
    let m = state.messages.find(x => Number(x.__jobId) === id);
    if (!m) {
      m = {role: "assistant", content: "", __jobId: id};
      state.messages.push(m);
    }
    m.content = backgroundJobText(job);
    m.__cancelRequested = Boolean(job.cancel_requested);
    m.__jobStatus = m.__cancelRequested && ["queued", "running"].includes(job.status)
      ? "cancelling" : job.status;
    m.__pickActivity = ["queued", "running", "cancelling"].includes(m.__jobStatus);
    if (Array.isArray(job.sources)) m.sources = job.sources;
  }
  updateSendButtons();
}

async function refreshChatAfterBackgroundJob(chatId) {
  if (Number(state.currentChatId) !== Number(chatId)) return;
  const data = await api(`/api/chat/${chatId}`);
  state.messages = data.messages || [];
  mergeBackgroundJobs(data.jobs || []);
  renderMessages(false);
  for (const job of (data.jobs || [])) pollBackgroundJob(job.id, chatId);
  try {
    const boot = await api("/api/bootstrap");
    state.chats = boot.chats || state.chats;
    renderChatList();
  } catch (_) {}
  updateSendButtons();
}

function pollBackgroundJob(jobId, chatId) {
  const key = String(jobId);
  if (state.jobPollers[key]) return;
  state.jobPollers[key] = true;
  const tick = async () => {
    try {
      const data = await api(`/api/jobs/${jobId}`);
      const job = data.job || {};
      if (Number(state.currentChatId) === Number(chatId)) {
        mergeBackgroundJobs([job]);
        if (window.pickRenderBackgroundJob) {
          window.pickRenderBackgroundJob(job);
        } else {
          renderMessages(false);
        }
      }
      if (["done", "failed", "cancelled"].includes(job.status)) {
        delete state.jobPollers[key];
        await refreshChatAfterBackgroundJob(chatId);
        if (job.status === "done") showToast("백그라운드 답변이 완료되었습니다.");
        updateSendButtons();
        return;
      }
      setTimeout(tick, window.pickJobPollDelay ? window.pickJobPollDelay() : 1200);
    } catch (_) {
      setTimeout(tick, 1000);
    }
  };
  tick();
}

function resumeBackgroundJobs(jobs, chatId) {
  const rows = Array.isArray(jobs) ? jobs : [];
  mergeBackgroundJobs(rows);
  for (const job of rows) pollBackgroundJob(job.id, chatId);
  updateSendButtons();
}

async function cancelBackgroundJob(jobId, chatId = state.currentChatId) {
  const id = Number(jobId);
  if (!id) return false;
  const existing = state.messages.find(m => Number(m.__jobId) === id);
  if (existing) {
    existing.__cancelRequested = true;
    existing.__jobStatus = "cancelling";
    existing.__pickActivity = true;
    if (!existing.content || existing.content === "답변을 준비하고 있습니다…" || existing.content === "답변을 생성하고 있습니다…") {
      existing.content = "답변 생성을 중지하고 있습니다…";
    }
  }
  renderMessages(false);
  updateSendButtons();
  try {
    const data = await api(`/api/jobs/${id}/cancel`, {method: "POST"});
    if (data.job) {
      mergeBackgroundJobs([data.job]);
      pollBackgroundJob(id, chatId);
    }
    showToast("답변 중지를 요청했습니다.");
    return true;
  } catch (e) {
    if (existing) {
      existing.__cancelRequested = false;
      existing.__jobStatus = "running";
    }
    updateSendButtons();
    showToast(e.message);
    return false;
  }
}

async function createChat() {
  const data = await api("/api/chat/new", {method: "POST"});
  state.currentChatId = data.chat_id;
  localStorage.setItem("pick:lastChatId", String(state.currentChatId));
  state.chats = data.chats || state.chats;
  renderChatList();
  return state.currentChatId;
}

async function openChat(id) {
  const data = await api(`/api/chat/${id}`);
  state.currentChatId = Number(id);
  localStorage.setItem("pick:lastChatId", String(state.currentChatId));
  state.messages = data.messages || [];
  resumeBackgroundJobs(data.jobs || [], state.currentChatId);
  renderChatList();
  renderMessages();
  setScreen("chatScreen");
  closeSidebar();
  setTimeout(() => $("messageInput")?.focus(), 30);
}

async function deleteChat(id) {
  if (!confirm("이 채팅을 삭제할까요?")) return;
  const data = await api(`/api/chat/${id}/delete`, {method: "POST"});
  state.chats = data.chats || [];
  if (Number(id) === Number(state.currentChatId)) startNewChatView();
  else renderChatList();
}

async function renameChat(id) {
  const current = state.chats.find(c => Number(c.id) === Number(id));
  const title = prompt("새 제목을 입력하세요.", current?.title || "");
  if (title === null || !title.trim()) return;
  const data = await api(`/api/chat/${id}/rename`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title.trim()})
  });
  state.chats = data.chats || state.chats;
  renderChatList();
}

function openChatMenu(button, id) {
  closeChatMenu();
  const rect = button.getBoundingClientRect();
  const backdrop = document.createElement("div");
  backdrop.id = "chatMenuBackdrop";
  backdrop.className = "chat-popover-backdrop";
  backdrop.addEventListener("click", closeChatMenu);

  const menu = document.createElement("div");
  menu.id = "chatPopover";
  menu.className = "chat-popover";
  menu.style.top = `${Math.min(rect.bottom + 4, innerHeight - 160)}px`;
  menu.style.left = `${Math.max(8, Math.min(rect.left - 110, innerWidth - 160))}px`;
  menu.innerHTML = `
    <button type="button" data-menu-rename="${id}">이름 바꾸기</button>
    <button type="button" data-menu-export="${id}">내보내기</button>
    <button type="button" class="danger" data-menu-delete="${id}">삭제</button>`;
  document.body.append(backdrop, menu);
}

function closeChatMenu() {
  $("chatPopover")?.remove();
  $("chatMenuBackdrop")?.remove();
}


async function stopCurrentResponse() {
  const job = getActiveBackgroundJob();
  if (job) {
    await cancelBackgroundJob(job.__jobId, state.currentChatId);
    return;
  }
  if (state.sending) {
    state.stopRequested = true;
    showToast("답변 중지를 요청했습니다.");
    updateSendButtons();
  }
}

function weatherQuery(text) {
  const t = String(text || "").toLowerCase();
  return ["날씨", "기온", "온도", "바람", "풍향", "풍양", "풍량", "풍속"].some(k => t.includes(k));
}

function navigationQuery(text) {
  const t = String(text || "").toLowerCase();
  const navWord = ["네비", "내비", "내비게이션", "길찾기", "차로", "자동차로", "도보", "걸어서", "자전거", "몇 분", "몇분", "얼마나 걸"].some(k => t.includes(k));
  return navWord && (t.includes("까지") || t.includes("에서") || t.includes("네비") || t.includes("내비") || t.includes("길찾기"));
}

function getGpsForWeather(text) {
  return new Promise(resolve => {
    if (!weatherQuery(text) && !navigationQuery(text)) {
      resolve({});
      return;
    }
    if (!navigator.geolocation || !window.isSecureContext) {
      resolve({gps_error: "unavailable"});
      return;
    }

    navigator.geolocation.getCurrentPosition(
      pos => resolve({
        latitude: Number(pos.coords.latitude.toFixed(6)),
        longitude: Number(pos.coords.longitude.toFixed(6)),
        location_accuracy_m: Math.round(pos.coords.accuracy || 0)
      }),
      err => resolve({
        gps_error: err?.code === 1 ? "permission_denied" : "location_unavailable"
      }),
      {
        enableHighAccuracy: false,
        timeout: 5000,
        maximumAge: 5 * 60 * 1000
      }
    );
  });
}

function buildFollowUps(query) {
  const q = String(query || "").toLowerCase();
  if (["날씨", "기온", "온도"].some(k => q.includes(k))) {
    return ["내일 날씨도 알려줘", "비 올 가능성을 더 자세히 알려줘", "이번 주 날씨도 알려줘"];
  }
  if (q.includes("뉴스") || q.includes("소식")) {
    return ["가장 중요한 뉴스 3개만 자세히 설명해줘", "이 뉴스들이 왜 중요한지 알려줘", "관련 최신 뉴스도 더 찾아줘"];
  }
  if (["코드", "코딩", "python", "javascript", "오류", "에러", "버그"].some(k => q.includes(k))) {
    return ["전체 코드로 다시 보여줘", "오류 가능성도 확인해줘", "실행 방법까지 알려줘"];
  }
  return ["더 자세히 설명해줘", "핵심만 정리해줘", "예시를 보여줘"];
}


async function sendTextStreaming(text) {
  const clean = String(text || "").trim();

  if (!clean) {
    if (responseIsActive()) await stopCurrentResponse();
    return;
  }

  // New questions are allowed while another answer is running.
  // The server background queue processes them in FIFO order.
  if (state.sending) {
    showToast("질문을 전송 중입니다. 다시 눌러 주세요.");
    return;
  }

  if (!state.currentChatId) await createChat();
  const chatId = Number(state.currentChatId);
  state.sending = true;
  state.stopRequested = false;
  updateSendButtons();

  if ($("messageInput")) {
    $("messageInput").value = "";
    autoGrow($("messageInput"));
  }

  try {
    const gps = await getGpsForWeather(clean);
    if (state.stopRequested) return;

    const data = await api(`/api/chat/${chatId}/background`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        message: clean,
        timezone: getClientTimezone(),
        country: getClientCountry(),
        ...gps
      })
    });

    state.messages = data.messages || state.messages;
    state.chats = data.chats || state.chats;
    if (data.job) {
      mergeBackgroundJobs([data.job]);
      pollBackgroundJob(data.job.id, chatId);
      if (state.stopRequested) await cancelBackgroundJob(data.job.id, chatId);
    }
    renderChatList();
    renderMessages();
  } catch (err) {
    showToast(err.message);
  } finally {
    state.sending = false;
    state.abortController = null;
    state.stopRequested = false;
    updateSendButtons();
    $("messageInput")?.focus();
  }
}

async function sendFromHome() {
  const text = $("homeInput")?.value.trim();
  if (!text) return;
  setScreen("chatScreen");
  await sendTextStreaming(text);
  if ($("homeInput")) {
    $("homeInput").value = "";
    autoGrow($("homeInput"));
  }
}

async function searchChats(query) {
  try {
    const data = await api(`/api/chats/search?q=${encodeURIComponent(query.trim())}`);
    state.chats = data.chats || [];
    renderChatList();
  } catch (_) {}
}

async function loadModels() {
  try {
    const data = await api("/api/models");
    state.models = data.models || [];
    const selected = state.settings?.selected_model || data.selected_model || "auto";
    if ($("modelButton")) {
      $("modelButton").innerHTML = `${escapeHtml(selected === "auto" ? "PICK" : selected)} <span>⌄</span>`;
    }
  } catch (_) {}
}

async function loadLanguages() {
  try {
    const data = await api("/api/languages");
    state.languages = data.languages || {};
    state.selectedLanguage = data.selected || "auto";
    const select = $("settingsLanguage");
    if (select) {
      select.innerHTML = Object.entries(state.languages)
        .map(([code, name]) => `<option value="${escapeHtml(code)}">${escapeHtml(name)}</option>`)
        .join("");
      select.value = state.selectedLanguage;
    }
  } catch (_) {}
}

async function loadMemories() {
  const box = $("memoryManager");
  if (!box) return;
  try {
    const data = await api("/api/memories");
    const rows = data.memories || [];
    box.innerHTML = rows.length ? rows.map(m => `
      <div class="memory-item">
        <div><span class="memory-importance">중요도 ${m.importance}</span><p>${escapeHtml(m.content)}</p></div>
        <button type="button" data-delete-memory="${m.id}">삭제</button>
      </div>`).join("") : '<div class="memory-empty">저장된 장기 기억이 없습니다.</div>';
  } catch (e) {
    box.innerHTML = `<div class="memory-empty">${escapeHtml(e.message)}</div>`;
  }
}

async function openSettings() {
  try {
    const settingsData = await api("/api/settings");
    state.settings = settingsData.settings || state.settings;
    await Promise.all([loadModels(), loadLanguages(), loadMemories(), loadSeasonalMode()]);

    const model = $("settingsModel");
    if (model) {
      model.innerHTML = '<option value="auto">자동 선택</option>' +
        state.models.map(m => `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`).join("");
      model.value = state.settings.selected_model || "auto";
    }
    if ($("settingsWebMode")) $("settingsWebMode").value = state.settings.web_mode || "auto";
    if ($("settingsCompact")) $("settingsCompact").checked = Boolean(state.settings.compact_mode);
    if ($("settingsSeasonalOverride")) $("settingsSeasonalOverride").value = state.settings.seasonal_override || "auto";

    setScreen("settingsScreen");
    closeSidebar();
  } catch (e) {
    showToast(e.message);
  }
}

async function saveSettings() {
  try {
    const selectedModel = $("settingsModel")?.value || "auto";
    const webMode = $("settingsWebMode")?.value || "auto";
    const compact = Boolean($("settingsCompact")?.checked);
    const seasonalOverride = $("settingsSeasonalOverride")?.value || "auto";

    const data = await api("/api/settings", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        selected_model: selectedModel,
        web_mode: webMode,
        compact_mode: compact,
        seasonal_override: seasonalOverride
      })
    });
    state.settings = data.settings || state.settings;
    await loadSeasonalMode();

    if ($("settingsLanguage")) {
      await api("/api/language", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({language: $("settingsLanguage").value})
      });
    }

    applyCompactMode();
    await loadModels();
    showToast("설정을 저장했습니다.");
    startNewChatView();
  } catch (e) {
    showToast(e.message);
  }
}

async function addMemory() {
  const input = $("memoryInput");
  const content = input?.value.trim();
  if (!content) return showToast("기억할 내용을 입력해 주세요.");
  try {
    await api("/api/memories", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        content,
        importance: 3,
        source_chat_id: state.currentChatId
      })
    });
    input.value = "";
    await loadMemories();
  } catch (e) {
    showToast(e.message);
  }
}

async function deleteMemory(id) {
  try {
    await api(`/api/memories/${id}`, {method: "DELETE"});
    await loadMemories();
  } catch (e) {
    showToast(e.message);
  }
}

async function runManualWebSearch() {
  const q = $("manualSearchInput")?.value.trim();
  const box = $("manualSearchResults");
  if (!q || !box) return showToast("검색어를 입력해 주세요.");
  box.innerHTML = '<div class="memory-empty">인터넷에서 검색 중입니다...</div>';

  try {
    const data = await api(`/api/search/web?q=${encodeURIComponent(q)}&mode=always`);
    if (data.kind === "weather" && data.weather) {
      const w = data.weather;
      box.innerHTML = `<div class="search-weather">
        <strong>${escapeHtml(w.location || q)}</strong>
        <div class="weather-big">${escapeHtml(String(w.temperature_c ?? "-"))}°C</div>
        <span>체감 ${escapeHtml(String(w.apparent_c ?? "-"))}°C · 최고 ${escapeHtml(String(w.today_high_c ?? "-"))}°C · 최저 ${escapeHtml(String(w.today_low_c ?? "-"))}°C</span>
        <a href="${escapeHtml(w.source_url || "#")}" target="_blank" rel="noopener">Open-Meteo</a>
      </div>`;
      return;
    }
    const rows = data.results || [];
    box.innerHTML = rows.length ? rows.map(r => `
      <a class="search-result-card" href="${escapeHtml(r.url)}" target="_blank" rel="noopener">
        <span class="search-provider">${escapeHtml(r.provider || "PICK Search")}</span>
        <strong>${escapeHtml(r.title || r.url)}</strong>
        <p>${escapeHtml(r.snippet || "")}</p>
        <small>${escapeHtml(r.url || "")}</small>
      </a>`).join("") : '<div class="memory-empty">검색 결과가 없습니다.</div>';
  } catch (e) {
    box.innerHTML = `<div class="memory-empty">${escapeHtml(e.message)}</div>`;
  }
}

async function uploadAttachment(file, mode="analysis", targetLanguage="") {
  if (!file) return;
  if (!state.currentChatId) await createChat();
  setScreen("chatScreen");
  try {
    const form = new FormData();
    form.append("file", file);
    const query = mode === "translate"
      ? `?mode=translate&target_language=${encodeURIComponent(targetLanguage || "한국어")}`
      : "";
    const data = await api(`/api/chat/${state.currentChatId}/attachment${query}`, {
      method: "POST",
      body: form
    });
    state.messages = data.messages || state.messages;
    state.chats = data.chats || state.chats;
    renderChatList();
    renderMessages();
    showToast(mode === "translate" ? "이미지 번역이 완료되었습니다." : "파일 분석이 완료되었습니다.");
  } catch (e) {
    showToast(e.message);
  }
}

function startVoiceInput() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return showToast("이 브라우저는 음성 입력을 지원하지 않습니다.");

  const sr = new SR();
  sr.lang = "ko-KR";
  sr.interimResults = true;
  let finalText = "";
  const input = $("messageInput");

  sr.onresult = e => {
    let interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const text = e.results[i][0].transcript;
      if (e.results[i].isFinal) finalText += text;
      else interim += text;
    }
    input.value = finalText + interim;
    autoGrow(input);
    updateSendButtons();
  };
  sr.onerror = () => showToast("음성 입력에 실패했습니다.");
  sr.start();
}


async function refreshInferenceStatus() {
  const el = $("queueStatus");
  if (!el) return;
  try {
    const data = await api("/api/inference/status");
    const q = data.queue || {};
    if (q.circuit_open) { el.textContent = "AI 복구 중"; el.className = "queue-status danger"; }
    else if ((q.waiting || 0) > 0) { el.textContent = `대기 ${q.waiting}`; el.className = "queue-status busy"; }
    else if ((q.active || 0) > 0) { el.textContent = "AI 응답 중"; el.className = "queue-status busy"; }
    else { el.textContent = "AI 준비"; el.className = "queue-status ok"; }
  } catch (_) {
    el.textContent = "AI 상태 불명";
  }
}

async function runDiagnostics() {
  const el = $("diagnosticsText");
  if (el) el.textContent = "검사 중...";
  try {
    const d = await api("/api/diagnostics");
    if (el) {
      el.textContent = `DB ${d.database ? "정상" : "오류"} · PICK AI ${d.ollama ? "정상" : "오류"} · 모델 ${d.models?.length || 0}개 · 시간 ${d.time?.accurate ? "NTP 동기화" : "서버 시계"}`;
    }
  } catch (e) {
    if (el) el.textContent = e.message;
  }
}



async function rateAssistantMessage(index, rating) {
  const msg = state.messages[index];
  if (!msg || msg.role === "user" || !state.currentChatId) return;

  try {
    const data = await api("/api/learning/feedback", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        chat_id: state.currentChatId,
        message_id: msg.id || null,
        rating,
        assistant_answer: msg.content
      })
    });
    showToast(
      rating > 0
        ? (data.auto_approved ? "좋은 답변을 자동 학습했습니다." : "좋은 답변으로 기록했습니다.")
        : "개선이 필요한 답변으로 기록했습니다."
    );
  } catch (e) {
    showToast(e.message);
  }
}

async function loadLearningCenter() {
  const statsBox = $("learningStats");
  const list = $("learningFeedbackList");
  try {
    const data = await api("/api/learning");
    const s = data.stats || {};
    if (statsBox) {
      statsBox.innerHTML = `
        <div><strong>${s.positive || 0}</strong><span>좋아요</span></div>
        <div><strong>${s.negative || 0}</strong><span>싫어요</span></div>
        <div><strong>${s.approved_examples || 0}</strong><span>승인 학습자료</span></div>`;
    }
    const rows = data.feedback || [];
    if (list) {
      list.innerHTML = rows.length ? rows.map(f => `
        <div class="learning-feedback-item">
          <div class="feedback-top">
            <span>${f.rating > 0 ? "👍 좋은 답변" : "👎 개선 필요"}</span>
            <small>${escapeHtml(f.created_at || "")}</small>
          </div>
          <strong>${escapeHtml(f.user_prompt || "(질문 없음)")}</strong>
          <p>${escapeHtml((f.assistant_answer || "").slice(0, 600))}</p>
          ${f.rating > 0 && !f.approved_for_training
            ? `<button type="button" data-approve-feedback="${f.id}">학습 데이터로 승인</button>`
            : f.approved_for_training ? '<span class="approved-badge">승인됨</span>' : ""}
        </div>`).join("")
        : '<div class="memory-empty">아직 학습 피드백이 없습니다.</div>';
    }
  } catch (e) {
    if (list) list.innerHTML = `<div class="memory-empty">${escapeHtml(e.message)}</div>`;
  }
}

async function openLearningCenter() {
  await loadLearningCenter();
  setScreen("learningScreen");
  closeSidebar();
}

async function approveLearningFeedback(id) {
  try {
    await api(`/api/learning/feedback/${id}/approve`, {method:"POST"});
    showToast("학습 데이터로 승인했습니다.");
    await loadLearningCenter();
  } catch (e) {
    showToast(e.message);
  }
}

async function rebuildMemoryIndex() {
  try {
    const data = await api("/api/learning/rebuild-memory-index", {method:"POST"});
    showToast(`기억 ${data.indexed_memories || 0}개를 인덱싱했습니다.`);
  } catch (e) {
    showToast(e.message);
  }
}




function getClientTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Seoul";
  } catch (_) {
    return "Asia/Seoul";
  }
}

function getClientCountry() {
  try {
    const locale = Intl.DateTimeFormat().resolvedOptions().locale || navigator.language || "";
    const match = locale.match(/[-_]([A-Z]{2})\b/i);
    return match ? match[1].toUpperCase() : "";
  } catch (_) {
    return "";
  }
}

async function loadSeasonalMode() {
  try {
    const data = await api(`/api/seasonal-mode?timezone=${encodeURIComponent(getClientTimezone())}&country=${encodeURIComponent(getClientCountry())}`);
    const mode = data.mode || {};
    applySeasonalMode(mode);

    if (seasonalRefreshTimer) clearTimeout(seasonalRefreshTimer);
    const recheckSeconds = Math.max(30, Number(mode.seconds_until_recheck || 300));
    seasonalRefreshTimer = setTimeout(() => {
      loadSeasonalMode();
    }, recheckSeconds * 1000);

    const seasonalSelect = $("settingsSeasonalOverride");
    if (seasonalSelect) {
      const modes = data.modes || {};
      seasonalSelect.innerHTML = '<option value="auto">자동</option>' +
        Object.entries(modes).map(([id,name]) => `<option value="${escapeHtml(id)}">${escapeHtml(name)}</option>`).join("");
      seasonalSelect.value = state.settings?.seasonal_override || "auto";
    }

    const status = $("seasonalModeStatus");
    if (status) {
      const sourceText = mode.automatic ? "자동" : "사용자 우선";
      status.textContent = `${sourceText} · ${mode.active ? `${mode.emoji || ""} ${mode.name}`.trim() : "기본 모드"}`;
      status.title = mode.country_mismatch
        ? "브라우저 지역과 시간대가 달라 시간대 기준 국가를 사용했습니다."
        : `시간대: ${mode.timezone || getClientTimezone()}`;
    }
    return data;
  } catch (_) {
    applySeasonalMode({active:false, id:"none", accent:"default"});
    const status = $("seasonalModeStatus");
    if (status) status.textContent = "자동";
    return null;
  }
}


function renderSeasonalDecoration(mode) {
  const layer = $("celebrationLayer");
  if (!layer) return;
  layer.innerHTML = "";

  const decoration = mode?.decoration || "none";
  if (decoration === "none") return;

  const maps = {
    confetti: ["✦","•","✧","◆","•","✦"],
    sparkles: ["✦","✧","?","✦","✧","!"],
    bubbles: ["○","◌","◦","○","◌","◦"],
    taegeuk: ["🇰🇷","✦","🇰🇷","✧"],
    memorial: ["✦","·","✧","·"],
    hangul: ["가","나","다","한","글","빛"],
    pumpkins: ["🎃","✦","☾","🎃","✧"],
    snow: ["❄","✦","❅","❄","✧","❆"],
    stars: ["✦","★","✧","☆","✦"]
  };

  const items = maps[decoration] || [];
  for (let i = 0; i < 18; i++) {
    const span = document.createElement("span");
    span.textContent = items[i % items.length];
    span.style.left = `${(i * 37) % 96}%`;
    span.style.animationDelay = `${(i % 8) * 0.55}s`;
    span.style.animationDuration = `${8 + (i % 6)}s`;
    layer.appendChild(span);
  }
}

function renderSeasonalCelebration(mode) {
  const card = $("seasonalCelebration");
  const icon = $("seasonalCelebrationIcon");
  const title = $("seasonalCelebrationTitle");
  const message = $("seasonalCelebrationMessage");
  if (!card) return;

  if (!mode?.active) {
    card.classList.add("hidden");
    return;
  }

  if (icon) icon.textContent = mode.emoji || "✦";
  if (title) title.textContent = mode.celebration_title || mode.name || "";
  if (message) message.textContent = mode.celebration_message || "";
  card.classList.remove("hidden");
}

function applySeasonalMode(mode) {
  const banner = $("seasonalBanner");

  document.body.classList.remove(
    "seasonal-newyear",
    "seasonal-samil",
    "seasonal-april",
    "seasonal-children",
    "seasonal-memorial",
    "seasonal-liberation",
    "seasonal-hangul",
    "seasonal-halloween",
    "seasonal-christmas",
    "seasonal-yearend"
  );

  const classMap = {
    new_year: "seasonal-newyear",
    samil: "seasonal-samil",
    april_fools: "seasonal-april",
    childrens_day: "seasonal-children",
    memorial_day: "seasonal-memorial",
    liberation_day: "seasonal-liberation",
    hangul_day: "seasonal-hangul",
    halloween: "seasonal-halloween",
    christmas: "seasonal-christmas",
    year_end: "seasonal-yearend"
  };

  const cls = classMap[mode?.id];
  if (cls) document.body.classList.add(cls);

  renderSeasonalDecoration(mode);
  renderSeasonalCelebration(mode);

  if (banner) {
    if (mode?.active && mode?.banner) {
      banner.textContent = mode.banner;
      banner.classList.remove("hidden");
    } else {
      banner.textContent = "";
      banner.classList.add("hidden");
    }
  }
}





async function loadAccountProfileMemory(){
  try{
    const data=await api("/api/account/profile-memory");
    const p=data.profile||{};
    if($("profilePreferredName")) $("profilePreferredName").value=p.preferred_name||"";
    if($("profileLanguage")) $("profileLanguage").value=p.preferred_language||"auto";
    if($("profileResponseStyle")) $("profileResponseStyle").value=p.response_style||"";
    if($("profileMainProject")) $("profileMainProject").value=p.main_project||"";
    if($("profileImportantNote")) $("profileImportantNote").value=p.important_note||"";
    const c=data.counts||{}, info=$("accountIsolationInfo");
    if(info) info.innerHTML=`<strong>현재 계정 데이터만 표시 중</strong><span>채팅 ${c.chats||0}개 · 메시지 ${c.messages||0}개 · 파일 ${c.attachments||0}개</span>`;
  }catch(e){showToast(e.message);}
}

async function saveAccountProfileMemory(){
  try{
    await api("/api/account/profile-memory",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        preferred_name:$("profilePreferredName")?.value.trim()||"",
        preferred_language:$("profileLanguage")?.value.trim()||"auto",
        response_style:$("profileResponseStyle")?.value.trim()||"",
        main_project:$("profileMainProject")?.value.trim()||"",
        important_note:$("profileImportantNote")?.value.trim()||""
      })
    });
    showToast("이 계정의 꼭 기억할 정보를 저장했습니다.");
  }catch(e){showToast(e.message);}
}

async function loadMemoryCenter() {
  try {
    const data = await api("/api/memory/v2");
    const stats = data.stats || {};
    const settings = data.settings || {};
    const rows = data.memories || [];

    const statsBox = $("memoryStats");
    if (statsBox) {
      statsBox.innerHTML = `
        <div><strong>${stats.total || 0}</strong><span>전체 기억</span></div>
        <div><strong>${stats.pinned || 0}</strong><span>고정 기억</span></div>
        <div><strong>${stats.summaries || 0}</strong><span>대화 요약</span></div>`;
    }

    if ($("memoryEnabled")) $("memoryEnabled").checked = Boolean(settings.enabled);
    if ($("memoryAutoExtract")) $("memoryAutoExtract").checked = Boolean(settings.auto_extract);
    if ($("memoryAutoSummary")) $("memoryAutoSummary").checked = Boolean(settings.auto_summary);
    if ($("memoryPreferences")) $("memoryPreferences").checked = Boolean(settings.remember_preferences);
    if ($("memoryProjects")) $("memoryProjects").checked = Boolean(settings.remember_projects);
    if ($("memoryDecisions")) $("memoryDecisions").checked = Boolean(settings.remember_decisions);

    const box = $("memoryV2List");
    if (box) {
      box.innerHTML = rows.length ? rows.map(m => `
        <div class="memory-v2-item">
          <div class="memory-v2-head">
            <div>
              <span class="memory-kind">${escapeHtml(m.kind)}</span>
              ${m.pinned ? '<span class="memory-pin-badge">고정</span>' : ""}
            </div>
            <div class="memory-v2-actions">
              <button type="button" data-pin-memory-v2="${m.id}" data-pinned="${m.pinned ? 1 : 0}">
                ${m.pinned ? "고정 해제" : "고정"}
              </button>
              <button type="button" data-delete-memory-v2="${m.id}">삭제</button>
            </div>
          </div>
          ${m.title ? `<strong>${escapeHtml(m.title)}</strong>` : ""}
          <p>${escapeHtml(m.content)}</p>
          <small>중요도 ${m.importance} · 신뢰도 ${Math.round((m.confidence || 0) * 100)}% · 사용 ${m.use_count || 0}회</small>
        </div>
      `).join("") : '<div class="memory-empty">아직 저장된 메모리가 없습니다.</div>';
    }
  } catch (e) {
    showToast(e.message);
  }
}

async function openMemoryCenter() {
  await Promise.all([loadMemoryCenter(), loadAccountProfileMemory()]);
  setScreen("memoryCenterScreen");
  closeSidebar();
}

async function addMemoryV2() {
  const content = $("memoryV2Content")?.value.trim();
  if (!content) return showToast("기억할 내용을 입력해 주세요.");

  try {
    await api("/api/memory/v2", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        title: $("memoryV2Title")?.value.trim() || "",
        content,
        kind: $("memoryV2Kind")?.value || "fact",
        importance: 4,
        confidence: 1.0,
        source_chat_id: state.currentChatId
      })
    });
    if ($("memoryV2Content")) $("memoryV2Content").value = "";
    if ($("memoryV2Title")) $("memoryV2Title").value = "";
    await loadMemoryCenter();
    showToast("메모리에 저장했습니다.");
  } catch (e) {
    showToast(e.message);
  }
}

async function saveMemorySettings() {
  try {
    await api("/api/memory/v2/settings", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        enabled: $("memoryEnabled")?.checked,
        auto_extract: $("memoryAutoExtract")?.checked,
        auto_summary: $("memoryAutoSummary")?.checked,
        remember_preferences: $("memoryPreferences")?.checked,
        remember_projects: $("memoryProjects")?.checked,
        remember_decisions: $("memoryDecisions")?.checked
      })
    });
    showToast("메모리 설정을 저장했습니다.");
  } catch (e) {
    showToast(e.message);
  }
}

async function deleteMemoryV2(id) {
  try {
    await api(`/api/memory/v2/${id}`, {method:"DELETE"});
    await loadMemoryCenter();
  } catch (e) {
    showToast(e.message);
  }
}

async function pinMemoryV2(id, currentPinned) {
  try {
    await api(`/api/memory/v2/${id}/pin`, {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({pinned: !Boolean(Number(currentPinned))})
    });
    await loadMemoryCenter();
  } catch (e) {
    showToast(e.message);
  }
}

async function bootstrap() {
  try {
    const data = await api("/api/bootstrap");
    state.chats = data.chats || [];
    state.settings = data.settings || state.settings;
    applyCompactMode();
    renderChatList();
    await Promise.all([loadModels(), loadLanguages(), loadSeasonalMode()]);
    const savedChatId = Number(localStorage.getItem("pick:lastChatId") || 0);
    const savedChat = state.chats.find(c => Number(c.id) === savedChatId);
    const targetChat = savedChat || state.chats[0] || null;
    if (targetChat) {
      await openChat(targetChat.id);
    } else {
      startNewChatView();
    }
    refreshInferenceStatus();
  } catch (e) {
    showToast(e.message);
  }
}

// ONE delegated click handler for the whole app.
document.addEventListener("click", async event => {
  const openChatBtn = event.target.closest("[data-open-chat]");
  if (openChatBtn) return openChat(openChatBtn.dataset.openChat);

  const menuBtn = event.target.closest("[data-chat-menu]");
  if (menuBtn) return openChatMenu(menuBtn, menuBtn.dataset.chatMenu);

  const rename = event.target.closest("[data-menu-rename]");
  if (rename) { closeChatMenu(); return renameChat(rename.dataset.menuRename); }

  const remove = event.target.closest("[data-menu-delete]");
  if (remove) { closeChatMenu(); return deleteChat(remove.dataset.menuDelete); }

  const exp = event.target.closest("[data-menu-export]");
  if (exp) { closeChatMenu(); location.href = `/api/chat/${exp.dataset.menuExport}/export?format=md`; return; }

  const copyCode = event.target.closest("[data-copy-code]");
  if (copyCode) {
    const code = copyCode.closest(".code-block")?.querySelector("code")?.textContent || "";
    await navigator.clipboard.writeText(code);
    return showToast("코드를 복사했습니다.");
  }

  const copyMsg = event.target.closest("[data-copy-message]");
  if (copyMsg) {
    await navigator.clipboard.writeText(state.messages[Number(copyMsg.dataset.copyMessage)]?.content || "");
    return showToast("답변을 복사했습니다.");
  }


  const rate = event.target.closest("[data-rate-message]");
  if (rate) return rateAssistantMessage(
    Number(rate.dataset.rateMessage),
    Number(rate.dataset.rating)
  );

  const approveFeedback = event.target.closest("[data-approve-feedback]");
  if (approveFeedback) return approveLearningFeedback(approveFeedback.dataset.approveFeedback);

  const delMemory = event.target.closest("[data-delete-memory]");
  if (delMemory) return deleteMemory(delMemory.dataset.deleteMemory);

  const delMemoryV2 = event.target.closest("[data-delete-memory-v2]");
  if (delMemoryV2) return deleteMemoryV2(delMemoryV2.dataset.deleteMemoryV2);

  const pinMemoryBtn = event.target.closest("[data-pin-memory-v2]");
  if (pinMemoryBtn) return pinMemoryV2(
    pinMemoryBtn.dataset.pinMemoryV2,
    pinMemoryBtn.dataset.pinned
  );

  const followUpBtn = event.target.closest("[data-follow-up]");
  if (followUpBtn) {
    const followText = followUpBtn.dataset.followUp || "";
    if (!followText) return;
    setScreen("chatScreen");
    return sendTextStreaming(followText);
  }

  const promptBtn = event.target.closest("[data-prompt]");
  if (promptBtn) {
    const promptText = promptBtn.dataset.prompt || "";
    if ($("homeScreen")?.classList.contains("active")) {
      $("homeInput").value = promptText;
      updateSendButtons();
      return sendFromHome();
    }
    $("messageInput").value = promptText;
    autoGrow($("messageInput"));
    updateSendButtons();
    return;
  }

  const fileTool = event.target.closest("[data-tool]");
  if (fileTool) {
    $("toolsMenu")?.classList.add("hidden");
    window.__pickFileToolMode = fileTool.dataset.tool || "file";
    window.__pickTranslateTarget = "";
    if (window.__pickFileToolMode === "image-translate") {
      const target = window.prompt("번역할 언어를 입력하세요.", "한국어");
      if (target === null) return;
      window.__pickTranslateTarget = target.trim() || "한국어";
    }
    $("filePicker")?.click();
    return;
  }

  if (event.target.closest("[data-file-button]")) {
    $("filePicker")?.click();
    return;
  }
});

// Direct listeners: bind only if the element exists.
$("newChatBtn")?.addEventListener("click", startNewChatView);
$("topNewChatBtn")?.addEventListener("click", startNewChatView);
$("homeSendBtn")?.addEventListener("click", () => {
  const text = $("homeInput")?.value || "";
  const action = composerAction(responseIsActive(), text);
  if (action === "send") return sendFromHome();
  if (action === "stop") return stopCurrentResponse();
});
$("sendBtn")?.addEventListener("click", () => {
  const text = $("messageInput")?.value || "";
  const action = composerAction(responseIsActive(), text);
  if (action === "send") return sendTextStreaming(text);
  if (action === "stop") return stopCurrentResponse();
});
$("memoryCenterBtn")?.addEventListener("click", openMemoryCenter);
$("learningBtn")?.addEventListener("click", openLearningCenter);
$("settingsBtn")?.addEventListener("click", openSettings);
$("modelButton")?.addEventListener("click", openSettings);
$("closeMemoryCenterBtn")?.addEventListener("click", startNewChatView);
$("closeLearningBtn")?.addEventListener("click", startNewChatView);
$("closeSettingsBtn")?.addEventListener("click", startNewChatView);
$("saveSettingsBtn")?.addEventListener("click", saveSettings);
$("memoryAddBtn")?.addEventListener("click", addMemory);
$("accountExportBtn")?.addEventListener("click", () => { location.href = "/api/account/export"; });
$("webSearchBtn")?.addEventListener("click", () => { setScreen("searchPanel"); $("manualSearchInput")?.focus(); });
$("closeSearchBtn")?.addEventListener("click", startNewChatView);
$("manualSearchBtn")?.addEventListener("click", runManualWebSearch);
$("voiceBtn")?.addEventListener("click", startVoiceInput);
$("diagnosticsBtn")?.addEventListener("click", runDiagnostics);
$("exportTrainingBtn")?.addEventListener("click", () => { location.href="/api/learning/export"; });
$("rebuildMemoryIndexBtn")?.addEventListener("click", rebuildMemoryIndex);
$("memoryV2AddBtn")?.addEventListener("click", addMemoryV2);
$("memorySettingsSaveBtn")?.addEventListener("click", saveMemorySettings);
$("memoryExportBtn")?.addEventListener("click", () => { location.href="/api/memory/v2/export"; });
$("profileMemorySaveBtn")?.addEventListener("click", saveAccountProfileMemory);
$("toolsBtn")?.addEventListener("click", () => $("toolsMenu")?.classList.toggle("hidden"));
$("openSidebarBtn")?.addEventListener("click", openSidebar);
$("closeSidebarBtn")?.addEventListener("click", closeSidebar);
$("sidebarOverlay")?.addEventListener("click", closeSidebar);

$("chatSearchInput")?.addEventListener("input", e => {
  clearTimeout(window.__pickSearchTimer);
  window.__pickSearchTimer = setTimeout(() => searchChats(e.target.value), 180);
});

$("manualSearchInput")?.addEventListener("keydown", e => {
  if (e.key === "Enter") {
    e.preventDefault();
    runManualWebSearch();
  }
});

["homeInput", "messageInput"].forEach(id => {
  const el = $(id);
  if (!el) return;
  el.addEventListener("input", e => {
    autoGrow(e.target);
    updateSendButtons();
  });
  el.addEventListener("keydown", e => {
    if (e.isComposing) return;
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const text = el.value || "";
      const action = composerAction(responseIsActive(), text);
      if (action === "send") {
        id === "homeInput" ? sendFromHome() : sendTextStreaming(text);
      } else if (action === "stop") {
        stopCurrentResponse();
      }
    }
  });
});

$("filePicker")?.addEventListener("change", e => {
  const file = e.target.files?.[0];
  e.target.value = "";
  if (!file) return;
  const mode = window.__pickFileToolMode === "image-translate" ? "translate" : "analysis";
  const target = window.__pickTranslateTarget || "한국어";
  window.__pickFileToolMode = "file";
  window.__pickTranslateTarget = "";
  uploadAttachment(file, mode, target);
});

document.addEventListener("paste", e => {
  const file = [...(e.clipboardData?.items || [])]
    .find(item => item.kind === "file")?.getAsFile();
  if (file) {
    e.preventDefault();
    uploadAttachment(file);
  }
});

document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    startNewChatView();
  }
  if (e.key === "Escape") {
    closeChatMenu();
    $("toolsMenu")?.classList.add("hidden");
    closeSidebar();
  }
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  });
}

document.addEventListener("mouseover", event => {
  if (!window.matchMedia?.("(hover: hover) and (pointer: fine)")?.matches) return;
  const details = event.target.closest(".pick-sources");
  if (details) details.open = true;
});

document.addEventListener("mouseout", event => {
  if (!window.matchMedia?.("(hover: hover) and (pointer: fine)")?.matches) return;
  const details = event.target.closest(".pick-sources");
  if (!details) return;
  if (event.relatedTarget && details.contains(event.relatedTarget)) return;
  details.open = false;
});

setInterval(refreshInferenceStatus, 5000);
bootstrap();
updateSendButtons();



async function analyzeCurrentQuestion() {
  const input = $("messageInput");
  const fallback = $("homeInput");
  const text = (input?.value || fallback?.value || "").trim();
  if (!text) return showToast("먼저 질문을 입력해 주세요.");

  try {
    const data = await api("/api/question/orchestrate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        message: text,
        chat_id: state.currentChatId
      })
    });

    const r = data.result || {};
    const a = r.analysis || {};
    const panel = $("questionPreview");
    if (!panel) return;

    const tags = [
      a.coding ? "코딩" : null,
      a.needs_web ? "인터넷 검색 필요" : null,
      a.error_report ? "오류 분석" : null,
      a.refers_to_context ? "이전 대화 참고" : null,
    ].filter(Boolean);

    panel.innerHTML = `
      <div class="question-preview-head">
        <strong>질문 이해</strong>
        <button type="button" data-close-question-preview>✕</button>
      </div>
      <p><b>의도:</b> ${escapeHtml(a.intent || "question")}</p>
      <p><b>정리된 의미:</b> ${escapeHtml(a.normalized || text)}</p>
      ${tags.length ? `<div class="question-tags">${tags.map(t => `<span>${escapeHtml(t)}</span>`).join("")}</div>` : ""}
      ${r.route ? `<p><b>처리 방식:</b> ${escapeHtml(r.route.primary || "chat")} · ${escapeHtml(r.route.reason || "")}</p>` : ""}
      ${r.context?.resolved ? `<p><b>연결된 이전 문맥:</b> ${escapeHtml(r.context.referent_summary || "")}</p>` : ""}
      ${r.clarification
        ? `<div class="question-warning">${escapeHtml(r.clarification)}</div>`
        : '<div class="question-ok">현재 문맥으로 바로 답변 가능한 것으로 판단했습니다.</div>'}
    `;
    panel.classList.remove("hidden");
  } catch (e) {
    showToast(e.message);
  }
}

$("refineQuestionBtn")?.addEventListener("click", analyzeCurrentQuestion);

document.addEventListener("click", e => {
  if (e.target.closest("[data-close-question-preview]")) {
    $("questionPreview")?.classList.add("hidden");
  }
});

/* ==========================================================
   PICK MOBILE V10.18
   Visual viewport + lightweight job rendering
   ========================================================== */
(function pickMobileV1018() {
  if (window.__pickMobileV1018) return;
  window.__pickMobileV1018 = true;

  const widthQuery = window.matchMedia("(max-width: 820px)");
  const coarseQuery = window.matchMedia("(hover: none) and (pointer: coarse)");

  function isMobile() {
    return Boolean(
      widthQuery.matches ||
      (coarseQuery.matches && window.innerWidth <= 1100)
    );
  }

  window.pickIsMobileDevice = isMobile;
  window.pickJobPollDelay = function () {
    return isMobile() ? 1800 : 1200;
  };

  function syncViewport() {
    const body = document.body;
    if (!body) return;

    const mobile = isMobile();
    body.classList.toggle("pick-mobile-ui", mobile);

    const vv = window.visualViewport;
    const height = Math.max(
      320,
      Math.round((vv && vv.height) || window.innerHeight || 0)
    );
    document.documentElement.style.setProperty(
      "--pick-mobile-height",
      `${height}px`
    );

    const full = Math.round(window.innerHeight || height);
    body.classList.toggle(
      "pick-keyboard-open",
      mobile && full - height > 120
    );
  }

  function attach() {
    syncViewport();

    window.addEventListener("resize", syncViewport, {passive: true});
    window.addEventListener("orientationchange", () => {
      setTimeout(syncViewport, 120);
      setTimeout(syncViewport, 420);
    }, {passive: true});

    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", syncViewport, {passive: true});
      window.visualViewport.addEventListener("scroll", syncViewport, {passive: true});
    }

    document.addEventListener("focusin", event => {
      if (
        isMobile() &&
        event.target &&
        event.target.matches("textarea,input,select")
      ) {
        document.body.classList.add("pick-keyboard-open");
        setTimeout(syncViewport, 40);
      }
    });

    document.addEventListener("focusout", () => {
      setTimeout(syncViewport, 180);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", attach, {once: true});
  } else {
    attach();
  }

  window.pickRenderBackgroundJob = function (job) {
    if (!isMobile()) {
      renderMessages(false);
      return;
    }

    const id = Number(job && job.id);
    const message = state.messages.find(
      item => Number(item.__jobId) === id
    );
    if (!message) {
      renderMessages(false);
      return;
    }

    const index = state.messages.indexOf(message);
    const row = document.querySelector(
      `.message-row[data-message-index="${index}"]`
    );
    const content = row && row.querySelector(".message-content");

    if (!row || !content) {
      renderMessages(false);
      return;
    }

    const box = document.getElementById("messageArea");
    const nearBottom = box
      ? (box.scrollHeight - box.scrollTop - box.clientHeight) < 180
      : false;

    content.innerHTML = markdown(message.content || "");

    if (nearBottom && box) {
      requestAnimationFrame(() => {
        box.scrollTop = box.scrollHeight;
      });
    }

    updateSendButtons();
  };
})();
