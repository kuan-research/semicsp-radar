const state = {
  items: [],
  history: [],
  market: {},
  activeDate: "",
  activeView: "semiconductor",
  filters: {
    search: "",
    region: "all",
    activeTag: "all",
  },
};

const els = {
  generatedAt: document.querySelector("#generatedAt"),
  refreshButton: document.querySelector("#refreshButton"),
  refreshStatus: document.querySelector("#refreshStatus"),
  tabs: document.querySelectorAll(".tab-link"),
  semiconductorView: document.querySelector("#semiconductorView"),
  marketView: document.querySelector("#marketView"),
  totalCount: document.querySelector("#totalCount"),
  internationalCount: document.querySelector("#internationalCount"),
  taiwanCount: document.querySelector("#taiwanCount"),
  highCount: document.querySelector("#highCount"),
  marketSummary: document.querySelector("#marketSummary"),
  marketIndex: document.querySelector("#marketIndex"),
  stockGrid: document.querySelector("#stockGrid"),
  marketNews: document.querySelector("#marketNews"),
  searchInput: document.querySelector("#searchInput"),
  regionFilter: document.querySelector("#regionFilter"),
  topicTags: document.querySelector("#topicTags"),
  clearTagButton: document.querySelector("#clearTagButton"),
  timeline: document.querySelector("#timeline"),
  split: document.querySelector(".split"),
  singleRegionSection: document.querySelector("#singleRegionSection"),
  singleRegionTitle: document.querySelector("#singleRegionTitle"),
  singleRegionSubtitle: document.querySelector("#singleRegionSubtitle"),
  singleRegionList: document.querySelector("#singleRegionList"),
  internationalList: document.querySelector("#internationalList"),
  taiwanList: document.querySelector("#taiwanList"),
  template: document.querySelector("#newsCardTemplate"),
  stockTemplate: document.querySelector("#stockCardTemplate"),
  backToTop: document.querySelector("#backToTop"),
};

async function init() {
  state.activeView = location.hash === "#market" ? "market" : "semiconductor";
  const payload = await loadJson("data/news.json");
  const history = await loadHistory();
  applyPayload(payload);
  state.history = history.days || [];
  bindEvents();
  renderTimeline();
  renderMarket();
  renderNews();
  showView(state.activeView, false);
}

async function loadJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  return response.json();
}

async function loadHistory() {
  try {
    return await loadJson("data/history.json");
  } catch {
    return { days: [] };
  }
}

function applyPayload(payload) {
  state.items = payload.items || [];
  state.market = payload.market || {};
  state.activeDate = payload.date || "";
  els.generatedAt.textContent = formatDate(payload.generated_at);
  renderTopicTags();
}

function bindEvents() {
  els.tabs.forEach((tab) => {
    tab.addEventListener("click", (event) => {
      event.preventDefault();
      showView(tab.dataset.view, true);
    });
  });

  els.searchInput.addEventListener("input", (event) => {
    state.filters.search = event.target.value.trim().toLowerCase();
    renderNews();
  });
  els.regionFilter.addEventListener("change", (event) => {
    state.filters.region = event.target.value;
    renderNews();
  });
  els.clearTagButton.addEventListener("click", () => {
    state.filters.activeTag = "all";
    renderTopicTags();
    renderNews();
  });
  els.backToTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  els.refreshButton.addEventListener("click", refreshData);
  window.addEventListener("scroll", () => {
    els.backToTop.classList.toggle("visible", window.scrollY > 360);
  });
  window.addEventListener("hashchange", () => {
    showView(location.hash === "#market" ? "market" : "semiconductor", false);
  });
}

async function refreshData() {
  els.refreshButton.disabled = true;
  els.refreshStatus.textContent = "重新讀取已發布資料...";
  try {
    const previousGeneratedAt = els.generatedAt.textContent;
    const payload = await loadJson("data/news.json");
    const history = await loadHistory();
    applyPayload(payload);
    state.history = history.days || [];
    renderTimeline();
    renderMarket();
    renderNews();
    const currentGeneratedAt = els.generatedAt.textContent;
    els.refreshStatus.textContent =
      currentGeneratedAt === previousGeneratedAt
        ? "目前已是最新已發布資料；系統約每 30 分鐘自動更新"
        : "已載入最新發布資料";
  } catch (error) {
    els.refreshStatus.textContent = "重新載入失敗";
  } finally {
    els.refreshButton.disabled = false;
  }
}

function showView(view, updateHash) {
  state.activeView = view === "market" ? "market" : "semiconductor";
  els.semiconductorView.classList.toggle("active-view", state.activeView === "semiconductor");
  els.marketView.classList.toggle("active-view", state.activeView === "market");
  els.tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.view === state.activeView));
  if (updateHash) {
    history.pushState(null, "", state.activeView === "market" ? "#market" : "#semiconductor");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function renderTopicTags() {
  const preferredTags = [
    "台積電",
    "NVIDIA",
    "AMD",
    "Microsoft",
    "Google",
    "AWS",
    "HBM",
    "CoWoS",
    "PCB",
    "ASIC",
    "AI 伺服器",
    "先進封裝",
  ];
  const counts = new Map();
  state.items.forEach((item) => {
    getItemTags(item).forEach((tag) => counts.set(tag, (counts.get(tag) || 0) + 1));
  });
  const tags = [
    ...preferredTags.filter((tag) => counts.has(tag)),
    ...[...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([tag]) => tag)
      .filter((tag) => !preferredTags.includes(tag))
      .slice(0, 16),
  ];

  els.clearTagButton.classList.toggle("active", state.filters.activeTag === "all");
  els.topicTags.innerHTML = "";
  tags.forEach((tag) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "topic-tag";
    if (state.filters.activeTag === tag) button.classList.add("active");
    button.textContent = `#${tag}`;
    button.addEventListener("click", () => {
      state.filters.activeTag = state.filters.activeTag === tag ? "all" : tag;
      renderTopicTags();
      renderNews();
    });
    els.topicTags.appendChild(button);
  });
}

function renderTimeline() {
  els.timeline.innerHTML = "";
  if (!state.history.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "尚無歷史歸檔。";
    els.timeline.appendChild(empty);
    return;
  }

  state.history.forEach((day) => {
    const button = document.createElement("button");
    button.className = "timeline-item";
    if (day.date === state.activeDate) button.classList.add("active");
    button.type = "button";
    button.innerHTML = `
      <span>${day.date}</span>
      <strong>${day.summary?.total || 0}</strong>
      <small>國際 ${day.summary?.international || 0} / 台灣 ${day.summary?.taiwan || 0}</small>
    `;
    button.addEventListener("click", async () => {
      const payload = await loadJson(day.path);
      applyPayload(payload);
      renderTimeline();
      renderMarket();
      renderNews();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    els.timeline.appendChild(button);
  });
}

function renderMarket() {
  const market = state.market || {};
  const summary = market.summary || {};
  els.marketSummary.innerHTML = `
    <p class="market-label">半導體供應鏈追蹤</p>
    <strong>${summary.plain_read || "尚無股市資料。"}</strong>
    <span>追蹤 ${summary.tracked || 0} 檔，上漲 ${summary.gainers || 0} / 下跌 ${summary.losers || 0}</span>
  `;

  els.marketIndex.innerHTML = "";
  (market.indices || []).forEach((item) => els.marketIndex.appendChild(buildQuotePill(item)));

  els.stockGrid.innerHTML = "";
  (market.stocks || []).forEach((stock) => {
    const card = els.stockTemplate.content.cloneNode(true);
    card.querySelector(".stock-group").textContent = stock.group;
    card.querySelector("h3").textContent = stock.name;
    card.querySelector(".stock-symbol").textContent = stock.symbol;
    const price = card.querySelector(".stock-price");
    price.className = `stock-price ${trendClass(stock.change_percent)}`;
    price.textContent = `${formatNumber(stock.price)} / ${formatPercent(stock.change_percent)}`;
    card.querySelector(".stock-read").textContent = stock.plain_read || "";
    els.stockGrid.appendChild(card);
  });

  els.marketNews.innerHTML = "";
  (market.news || []).slice(0, 10).forEach((news) => {
    const link = document.createElement("a");
    link.href = news.url || "#";
    link.target = "_blank";
    link.rel = "noreferrer";
    link.className = "market-news-item";
    link.innerHTML = `
      <span>${news.source}</span>
      <strong>${news.title}</strong>
      <small>${formatDate(news.published)}</small>
    `;
    els.marketNews.appendChild(link);
  });

  if (!els.marketNews.children.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "尚無 Yahoo 股市新聞。";
    els.marketNews.appendChild(empty);
  }
}

function buildQuotePill(item) {
  const pill = document.createElement("div");
  pill.className = `quote-pill ${trendClass(item.change_percent)}`;
  pill.innerHTML = `
    <span>${item.name}</span>
    <strong>${formatNumber(item.price)}</strong>
    <small>${formatPercent(item.change_percent)}</small>
  `;
  return pill;
}

function renderNews() {
  const items = filteredItems();
  const international = items.filter((item) => item.region === "international");
  const taiwan = items.filter((item) => item.region === "taiwan");

  els.totalCount.textContent = state.items.length;
  els.internationalCount.textContent = state.items.filter((item) => item.region === "international").length;
  els.taiwanCount.textContent = state.items.filter((item) => item.region === "taiwan").length;
  els.highCount.textContent = state.items.filter((item) => Number(item.importance) >= 4).length;

  if (state.filters.region === "all") {
    els.split.style.display = "";
    els.singleRegionSection.style.display = "none";
    renderList(els.internationalList, international, "沒有符合條件的國際情勢消息。");
    renderList(els.taiwanList, taiwan, "沒有符合條件的台灣本土消息。");
    return;
  }

  const isTaiwan = state.filters.region === "taiwan";
  els.split.style.display = "none";
  els.singleRegionSection.style.display = "block";
  els.singleRegionTitle.textContent = isTaiwan ? "台灣本土情勢" : "國際情勢";
  els.singleRegionSubtitle.textContent = isTaiwan
    ? "台積電、封裝、伺服器 ODM 與零組件"
    : "CSP、晶片、記憶體、設備與政策";
  renderList(
    els.singleRegionList,
    isTaiwan ? taiwan : international,
    isTaiwan ? "沒有符合條件的台灣本土消息。" : "沒有符合條件的國際情勢消息。"
  );
}

function filteredItems() {
  return state.items
    .filter((item) => {
      const haystack = [
        item.title,
        item.title_zh,
        item.source,
        item.summary_zh,
        item.investment_takeaway,
        ...(item.segments || []),
        ...(item.companies || []),
      ]
        .join(" ")
        .toLowerCase();
      const matchesSearch = !state.filters.search || haystack.includes(state.filters.search);
      const matchesRegion = state.filters.region === "all" || item.region === state.filters.region;
      const matchesTag =
        state.filters.activeTag === "all" ||
        getItemTags(item).includes(state.filters.activeTag) ||
        haystack.includes(state.filters.activeTag.toLowerCase());
      return matchesSearch && matchesRegion && matchesTag;
    })
    .sort((a, b) => Number(b.importance) - Number(a.importance));
}

function getItemTags(item) {
  const tags = new Set();
  const text = [
    item.title,
    item.title_zh,
    item.summary_zh,
    item.investment_takeaway,
    ...(item.companies || []),
    ...(item.segments || []),
  ]
    .join(" ")
    .toLowerCase();

  const aliases = {
    台積電: ["tsmc", "台積電"],
    NVIDIA: ["nvidia", "輝達"],
    AMD: ["amd"],
    Microsoft: ["microsoft", "azure"],
    Google: ["google", "gcp", "tpu"],
    AWS: ["aws", "amazon"],
    HBM: ["hbm"],
    CoWoS: ["cowos"],
    PCB: ["pcb", "ccl", "載板"],
    ASIC: ["asic", "custom silicon"],
    "AI 伺服器": ["ai server", "server", "伺服器"],
    先進封裝: ["advanced packaging", "packaging", "先進封裝"],
  };

  Object.entries(aliases).forEach(([tag, words]) => {
    if (words.some((word) => text.includes(word.toLowerCase()))) tags.add(tag);
  });
  (item.companies || []).forEach((company) => tags.add(company));
  (item.segments || []).forEach((segment) => {
    const compact = segment.split("/")[0].trim();
    if (compact && compact.length <= 8) tags.add(compact);
  });
  return [...tags];
}

function renderList(container, items, emptyText) {
  container.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = emptyText;
    container.appendChild(empty);
    return;
  }

  items.forEach((item) => {
    const card = els.template.content.cloneNode(true);
    card.querySelector(".source").textContent = `${item.source} · ${formatDate(item.published)}`;
    card.querySelector("h3").textContent = item.title_zh || "繁中重點標題待產生";
    card.querySelector(".importance").textContent = `I-${item.importance}`;
    card.querySelector(".english-title").innerHTML = `<span>English original</span>${escapeHtml(item.title || "")}`;
    card.querySelector(".summary").textContent = item.summary_zh || "暫無摘要。";
    card.querySelector(".takeaway").textContent = item.investment_takeaway || "暫無投資觀察。";

    const tags = card.querySelector(".tags");
    [...(item.segments || []), ...(item.companies || [])].forEach((tag) => {
      const tagEl = document.createElement("span");
      tagEl.className = "tag";
      tagEl.textContent = tag;
      tags.appendChild(tagEl);
    });

    const link = card.querySelector(".read-link");
    link.href = item.url || "#";
    if (!item.url) link.remove();
    container.appendChild(card);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function trendClass(value) {
  if (value > 0) return "up";
  if (value < 0) return "down";
  return "flat";
}

function formatNumber(value) {
  if (value === null || value === undefined) return "--";
  return new Intl.NumberFormat("zh-TW", { maximumFractionDigits: 2 }).format(value);
}

function formatPercent(value) {
  if (value === null || value === undefined) return "--";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function formatDate(value) {
  if (!value) return "未知時間";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

init().catch((error) => {
  document.body.innerHTML = `<main><div class="empty">讀取資料失敗：${error.message}</div></main>`;
});
