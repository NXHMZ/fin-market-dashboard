let currentSource = "";
let currentLevel = "";
let currentSort = "heat";
let searchQuery = "";
let heatLevels = {};
let refreshTimer = null;

const HEAT_LEVEL_ORDER = ["scorching", "hot", "warm", "cool", "cold"];

async function init() {
    await loadHeatLevels();
    renderHeatLegend();
    await loadStatus();
    await loadNews();
    await loadKeywords();
    startAutoRefresh();
}

async function loadHeatLevels() {
    try {
        const res = await fetch("/api/heat_levels");
        heatLevels = await res.json();
    } catch (e) {
        console.error("Failed to load heat levels:", e);
    }
}

function renderHeatLegend() {
    const container = document.getElementById("heatLegend");
    container.innerHTML = "";
    for (const level of HEAT_LEVEL_ORDER) {
        const meta = heatLevels[level];
        if (!meta) continue;
        const item = document.createElement("div");
        item.className = "heat-legend-item" + (currentLevel === level ? " active" : "");
        item.onclick = () => toggleLevel(level);
        item.innerHTML = `
            <div class="heat-badge" style="background:${meta.color}">${meta.label}</div>
            <span>${getLevelName(level)}</span>
        `;
        container.appendChild(item);
    }
}

function getLevelName(level) {
    const names = {
        scorching: "爆热 (≥80分)",
        hot: "热门 (≥50分)",
        warm: "温热 (≥30分)",
        cool: "一般 (≥15分)",
        cold: "冷门 (<15分)",
    };
    return names[level] || level;
}

function toggleLevel(level) {
    currentLevel = currentLevel === level ? "" : level;
    renderHeatLegend();
    loadNews();
}

function switchTab(sortBy) {
    currentSort = sortBy;
    document.getElementById("tabHeat").classList.toggle("active", sortBy === "heat");
    document.getElementById("tabTime").classList.toggle("active", sortBy === "time");
    document.getElementById("tabCninfo").classList.toggle("active", sortBy === "cninfo");
    loadNews();
}

async function loadStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        renderStatusBar(data);
        renderSourceFilters(data);
        renderStats(data);
    } catch (e) {
        console.error("Failed to load status:", e);
    }
}

function renderStatusBar(data) {
    const bar = document.getElementById("statusBar");
    bar.innerHTML = "";

    for (const [sourceId, info] of Object.entries(data.source_status || {})) {
        const chip = document.createElement("div");
        chip.className = "source-chip" + (currentSource === sourceId ? " active" : "");
        chip.onclick = () => toggleSource(sourceId);
        chip.innerHTML = `
            <div class="dot ${info.status}"></div>
            <span>${info.name}</span>
            ${info.count > 0 ? `<span class="count">${info.count}</span>` : ""}
        `;
        bar.appendChild(chip);
    }

    const updateTime = document.getElementById("updateTime");
    if (data.last_update) {
        updateTime.textContent = `最后更新: ${data.last_update}`;
    }
}

function renderSourceFilters(data) {
    const container = document.getElementById("sourceFilters");
    container.innerHTML = "";

    const allItem = document.createElement("div");
    allItem.className = "source-filter-item" + (currentSource === "" ? " active" : "");
    allItem.onclick = () => toggleSource("");
    allItem.innerHTML = `
        <div class="color-dot" style="background:var(--accent)"></div>
        <span>全部数据源</span>
    `;
    container.appendChild(allItem);

    for (const [sourceId, info] of Object.entries(data.source_status || {})) {
        const item = document.createElement("div");
        item.className = "source-filter-item" + (currentSource === sourceId ? " active" : "");
        item.onclick = () => toggleSource(sourceId);
        item.innerHTML = `
            <div class="color-dot" style="background:${info.color}"></div>
            <span>${info.name}</span>
            <span style="margin-left:auto;font-size:11px;color:var(--text-muted)">${info.count}</span>
        `;
        container.appendChild(item);
    }
}

function renderStats(data) {
    document.getElementById("statTotal").textContent = data.total_count || 0;
    const okCount = Object.values(data.source_status || {}).filter(s => s.status === "ok").length;
    const totalCount = Object.keys(data.source_status || {}).length;
    document.getElementById("statSources").textContent = `${okCount}/${totalCount}`;
}

function toggleSource(sourceId) {
    currentSource = currentSource === sourceId ? "" : sourceId;
    loadNews();
    loadStatus();
}

function handleSearch() {
    const input = document.getElementById("searchInput");
    searchQuery = input.value.trim().toLowerCase();
    clearTimeout(window.searchTimer);
    window.searchTimer = setTimeout(loadNews, 300);
}

async function loadNews() {
    try {
        const params = new URLSearchParams();
        if (currentSource) params.append("source", currentSource);
        if (currentLevel) params.append("level", currentLevel);
        if (searchQuery) params.append("search", searchQuery);

        const res = await fetch("/api/news?" + params.toString());
        const data = await res.json();
        renderNews(data);
    } catch (e) {
        console.error("Failed to load news:", e);
        document.getElementById("newsFeed").innerHTML = `
            <div class="empty-state">
                <div class="icon">⚠️</div>
                <p>加载失败，请检查网络连接</p>
            </div>
        `;
    }
}

function renderNews(data) {
    const feed = document.getElementById("newsFeed");
    let items = (data.items || []).slice();

    if (items.length === 0) {
        feed.innerHTML = `
            <div class="empty-state">
                <div class="icon">📭</div>
                <p>暂无符合条件的新闻</p>
            </div>
        `;
        return;
    }

    if (currentSort === "cninfo") {
        items = items.filter(i => i.source_id === "cninfo");
        items.sort((a, b) => {
            const ta = (a.published || "").replace(/[^0-9]/g, "");
            const tb = (b.published || "").replace(/[^0-9]/g, "");
            if (!ta && !tb) return 0;
            if (!ta) return 1;
            if (!tb) return -1;
            return tb.localeCompare(ta);
        });
    } else if (currentSort === "time") {
        items = items.filter(i => i.source_id !== "cninfo");
        items.sort((a, b) => {
            const ta = (a.published || "").replace(/[^0-9]/g, "");
            const tb = (b.published || "").replace(/[^0-9]/g, "");
            if (!ta && !tb) return 0;
            if (!ta) return 1;
            if (!tb) return -1;
            return tb.localeCompare(ta);
        });
    } else {
        items.sort((a, b) => (b.heat_score || 0) - (a.heat_score || 0));
    }

    feed.innerHTML = "";
    for (const item of items) {
        const card = createNewsCard(item);
        feed.appendChild(card);
    }
}

function createNewsCard(item) {
    const card = document.createElement("div");
    card.className = `news-card ${item.heat_level || "cold"}` + (item.error ? " error-card" : "");

    const levelMeta = heatLevels[item.heat_level] || heatLevels["cold"];
    const heatColor = levelMeta ? levelMeta.color : "#90a4ae";
    const heatLabel = levelMeta ? levelMeta.label : "冷";

    let headerHtml = `
        <div class="card-header">
            <span class="source-badge" style="background:${item.source_color}">
                ${item.source_icon || item.source_name}
            </span>
            <span class="source-name">${item.source_name}</span>
    `;

    if (item.type_label) {
        headerHtml += `<span class="type-tag">${item.type_label}</span>`;
    }
    if (item.important) {
        headerHtml += `<span class="type-tag" style="color:#ff5722;font-weight:700">重要</span>`;
    }

    headerHtml += `</div>`;

    let footerHtml = `<div class="card-footer">`;
    if (item.published) {
        footerHtml += `<span class="time-tag">🕒 ${item.published}</span>`;
    }
    if (item.heat_keywords && item.heat_keywords.length > 0) {
        for (const kw of item.heat_keywords.slice(0, 5)) {
            footerHtml += `<span class="kw-tag-small">${kw}</span>`;
        }
    }
    footerHtml += `</div>`;

    const titleHtml = item.url
        ? `<a href="${item.url}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer"
             style="color:inherit;text-decoration:none">${escapeHtml(item.title)}</a>`
        : escapeHtml(item.title);

    card.innerHTML = `
        <div class="heat-section">
            <div class="heat-badge-large" style="background:${heatColor}">${heatLabel}</div>
            <div class="heat-score">${item.heat_score || 0}分</div>
        </div>
        <div class="content-section">
            ${headerHtml}
            <div class="title">${titleHtml}</div>
            ${item.content ? `<div class="content">${escapeHtml(item.content)}</div>` : ""}
            ${footerHtml}
        </div>
    `;

    return card;
}

function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

async function loadKeywords() {
    try {
        const res = await fetch("/api/keywords");
        const data = await res.json();
        renderKeywords(data.keywords || {});
    } catch (e) {
        console.error("Failed to load keywords:", e);
    }
}

function renderKeywords(keywords) {
    const container = document.getElementById("keywordCloud");
    const entries = Object.entries(keywords);
    if (entries.length === 0) {
        container.innerHTML = '<span class="kw-empty">暂无数据</span>';
        return;
    }

    container.innerHTML = "";
    const maxCount = entries[0][1];
    for (const [kw, count] of entries) {
        const tag = document.createElement("span");
        tag.className = "kw-tag" + (count >= maxCount * 0.6 ? " hot" : "");
        const fontSize = Math.max(11, Math.min(16, 11 + (count / maxCount) * 5));
        tag.style.fontSize = fontSize + "px";
        tag.textContent = `${kw} (${count})`;
        tag.onclick = () => {
            document.getElementById("searchInput").value = kw;
            searchQuery = kw.toLowerCase();
            loadNews();
        };
        container.appendChild(tag);
    }
}

async function manualRefresh() {
    const btn = document.querySelector(".btn-refresh");
    btn.disabled = true;
    btn.textContent = "刷新中...";
    try {
        await fetch("/api/refresh", { method: "POST" });
        setTimeout(async () => {
            await loadStatus();
            await loadNews();
            await loadKeywords();
            btn.disabled = false;
            btn.textContent = "手动刷新";
        }, 3000);
    } catch (e) {
        btn.disabled = false;
        btn.textContent = "手动刷新";
    }
}

function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(async () => {
        await loadStatus();
        await loadNews();
        await loadKeywords();
    }, 30000);
}

init();
