import os
import sys
import json
import threading
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_SOURCES, MAX_TOTAL_ITEMS
from heat_engine import HeatEngine
from fetchers.cls_fetcher import CLSFetcher
from fetchers.jin10_fetcher import Jin10Fetcher
from fetchers.wallstreetcn_fetcher import WallstreetcnFetcher
from fetchers.cninfo_fetcher import CninfoFetcher
from fetchers.exchange_fetcher import ExchangeFetcher
from fetchers.csrc_fetcher import CSRCFetcher
from fetchers.securities_fetcher import SecuritiesFetcher

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

heat_engine = HeatEngine()

fetcher_instances = {
    "cls":          CLSFetcher(),
    "jin10":        Jin10Fetcher(),
    "wallstreetcn": WallstreetcnFetcher(),
    "cninfo":       CninfoFetcher(),
    "sse":          ExchangeFetcher("sse"),
    "szse":         ExchangeFetcher("szse"),
    "csrc":         CSRCFetcher(),
    "cs":           SecuritiesFetcher("cs"),
    "cnstock":      SecuritiesFetcher("cnstock"),
    "stcn":         SecuritiesFetcher("stcn"),
}


def fetch_all_sources():
    all_items = []
    source_status = {}
    results = {}

    def fetch_source(source_id, fetcher):
        try:
            items = fetcher.fetch()
            source_status[source_id] = {
                "name": DATA_SOURCES[source_id]["name"],
                "status": "ok" if not any(i.get("error") for i in items) else "partial",
                "count": len([i for i in items if not i.get("error")]),
                "color": DATA_SOURCES[source_id]["color"],
                "icon": DATA_SOURCES[source_id]["icon"],
            }
            return items
        except Exception as e:
            source_status[source_id] = {
                "name": DATA_SOURCES[source_id]["name"],
                "status": "error",
                "count": 0,
                "color": DATA_SOURCES[source_id]["color"],
                "icon": DATA_SOURCES[source_id]["icon"],
                "error": str(e)[:100],
            }
            return []

    threads = []
    for source_id, fetcher in fetcher_instances.items():
        def run(s=source_id, f=fetcher):
            results[s] = fetch_source(s, f)
        t = threading.Thread(target=run)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=20)

    for source_id in fetcher_instances:
        for item in results.get(source_id, []):
            scored = heat_engine.calculate(item)
            all_items.append(scored)

    all_items.sort(key=lambda x: x.get("heat_score", 0), reverse=True)
    all_items = all_items[:MAX_TOTAL_ITEMS]

    keyword_stats = heat_engine.compute_keyword_stats(all_items)

    return all_items, source_status, keyword_stats


def generate_html(items, source_status, keyword_stats):
    heat_meta = heat_engine.heat_level_meta

    data_json = json.dumps({
        "items": items,
        "source_status": source_status,
        "keywords": keyword_stats,
        "heat_levels": heat_meta,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False, default=str)

    html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>金融市场信息聚合系统</title>
<style>
:root{--bg-primary:#0d1117;--bg-secondary:#161b22;--bg-tertiary:#1c2330;--bg-hover:#262d3a;--border:#30363d;--text-primary:#e6edf3;--text-secondary:#8b949e;--text-muted:#6e7681;--accent:#2f81f7;--success:#238636;--warning:#d29922;--danger:#da3633;--radius:8px;--sidebar-width:280px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg-primary);color:var(--text-primary);font-size:14px;line-height:1.6;overflow-x:hidden}
#app{display:flex;flex-direction:column;min-height:100vh}
.top-bar{height:56px;background:var(--bg-secondary);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 20px;position:sticky;top:0;z-index:100}
.top-left{display:flex;align-items:center;gap:16px}
.logo{display:flex;align-items:center;gap:8px}
.logo-icon{font-size:22px}
.logo-text{font-size:18px;font-weight:700;background:linear-gradient(135deg,#2f81f7,#a371f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.update-time{font-size:12px;color:var(--text-muted);padding:4px 10px;background:var(--bg-tertiary);border-radius:4px}
.top-right{display:flex;align-items:center;gap:12px}
.btn-refresh{padding:6px 16px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;transition:all .2s}
.btn-refresh:hover{background:#4493f8;transform:translateY(-1px)}
.status-bar{min-height:48px;background:var(--bg-secondary);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px;padding:0 20px;overflow-x:auto;white-space:nowrap;flex-wrap:wrap}
.source-chip{display:flex;align-items:center;gap:6px;padding:4px 12px;background:var(--bg-tertiary);border-radius:16px;font-size:12px;cursor:pointer;transition:all .2s;border:1px solid transparent;flex-shrink:0}
.source-chip:hover{border-color:var(--border);background:var(--bg-hover)}
.source-chip.active{border-color:var(--accent)}
.source-chip .dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.source-chip .dot.ok{background:var(--success)}.source-chip .dot.error{background:var(--danger)}.source-chip .dot.partial{background:var(--warning)}
.source-chip .count{background:var(--bg-hover);padding:1px 6px;border-radius:8px;font-size:11px;color:var(--text-secondary)}
.main-content{display:flex;flex:1;overflow:hidden}
.sidebar{width:var(--sidebar-width);background:var(--bg-secondary);border-right:1px solid var(--border);overflow-y:auto;padding:16px;flex-shrink:0}
.panel{margin-bottom:20px;background:var(--bg-tertiary);border-radius:var(--radius);padding:14px}
.panel-title{font-size:13px;font-weight:700;color:var(--text-secondary);margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px}
.heat-legend{display:flex;flex-direction:column;gap:8px}
.heat-legend-item{display:flex;align-items:center;gap:8px;font-size:12px;cursor:pointer;padding:4px 8px;border-radius:6px;transition:background .2s}
.heat-legend-item:hover,.heat-legend-item.active{background:var(--bg-hover)}
.heat-badge{width:24px;height:24px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;flex-shrink:0}
.source-filters{display:flex;flex-direction:column;gap:4px}
.source-filter-item{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;cursor:pointer;transition:background .2s;font-size:13px}
.source-filter-item:hover,.source-filter-item.active{background:var(--bg-hover)}
.source-filter-item .color-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.search-box input{width:100%;padding:8px 12px;background:var(--bg-primary);border:1px solid var(--border);border-radius:6px;color:var(--text-primary);font-size:13px;outline:none;transition:border-color .2s}
.search-box input:focus{border-color:var(--accent)}
.keyword-cloud{display:flex;flex-wrap:wrap;gap:6px}
.kw-empty{color:var(--text-muted);font-size:12px}
.kw-tag{padding:3px 10px;background:var(--bg-primary);border-radius:12px;font-size:12px;cursor:pointer;transition:all .2s;color:var(--text-secondary)}
.kw-tag:hover{background:var(--accent);color:#fff}
.kw-tag.hot{color:var(--danger);font-weight:600}
.stats{display:flex;flex-direction:column;gap:10px}
.stat-item{display:flex;justify-content:space-between;align-items:center}
.stat-label{font-size:12px;color:var(--text-secondary)}
.stat-value{font-size:18px;font-weight:700;color:var(--text-primary)}
.news-feed{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px}
.content-right{flex:1;display:flex;flex-direction:column;overflow:hidden}
.tab-bar{display:flex;gap:0;background:var(--bg-secondary);border-bottom:1px solid var(--border);padding:0 16px;flex-shrink:0}
.tab{padding:10px 20px;cursor:pointer;font-size:14px;font-weight:600;color:var(--text-secondary);border-bottom:2px solid transparent;transition:all .2s;display:flex;align-items:center;gap:6px;user-select:none}
.tab:hover{color:var(--text-primary);background:var(--bg-hover)}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab-icon{font-size:16px}
.news-card{background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius);padding:16px;transition:all .2s;cursor:pointer;display:flex;gap:14px;animation:fadeIn .3s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.news-card:hover{border-color:var(--text-muted);background:var(--bg-tertiary)}
.news-card.scorching{border-left:3px solid #ff1744}
.news-card.hot{border-left:3px solid #ff5722}
.news-card.warm{border-left:3px solid #ff9800}
.news-card.cool{border-left:3px solid #4caf50}
.news-card.cold{border-left:3px solid #90a4ae}
.news-card.error-card{opacity:.6;border-left:3px solid var(--danger)}
.news-card.error-card .title{color:var(--danger)}
.news-card .heat-section{display:flex;flex-direction:column;align-items:center;gap:6px;min-width:56px}
.news-card .heat-badge-large{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:#fff}
.news-card .heat-score{font-size:11px;color:var(--text-muted);font-weight:600}
.news-card .content-section{flex:1;min-width:0}
.news-card .card-header{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.news-card .source-badge{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;color:#fff}
.news-card .type-tag{padding:1px 6px;border-radius:4px;font-size:11px;background:var(--bg-tertiary);color:var(--text-secondary)}
.news-card .time-tag{font-size:12px;color:var(--text-muted)}
.news-card .title{font-size:15px;font-weight:600;line-height:1.5;margin-bottom:6px;color:var(--text-primary);word-break:break-word}
.news-card .content{font-size:13px;color:var(--text-secondary);line-height:1.6;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;word-break:break-word}
.news-card .card-footer{display:flex;align-items:center;gap:6px;margin-top:10px;flex-wrap:wrap}
.news-card .kw-tag-small{padding:2px 8px;background:var(--bg-tertiary);border-radius:10px;font-size:11px;color:var(--text-secondary)}
.empty-state{text-align:center;padding:60px 20px;color:var(--text-muted)}
.empty-state .icon{font-size:48px;margin-bottom:12px}
.footer{height:36px;background:var(--bg-secondary);border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 20px;font-size:11px;color:var(--text-muted)}
@media(max-width:768px){.sidebar{display:none}.top-bar{flex-wrap:wrap;height:auto;padding:10px}.logo-text{font-size:14px}}
</style>
</head>
<body>
<div id="app">
    <header class="top-bar">
        <div class="top-left">
            <div class="logo"><span class="logo-icon">📊</span><span class="logo-text">金融市场信息聚合系统</span></div>
            <span class="update-time" id="updateTime">加载中...</span>
        </div>
        <div class="top-right">
            <button class="btn-refresh" onclick="location.reload()">刷新数据</button>
        </div>
    </header>
    <div class="status-bar" id="statusBar"></div>
    <div class="main-content">
        <aside class="sidebar">
            <div class="panel"><h3 class="panel-title">热度等级</h3><div class="heat-legend" id="heatLegend"></div></div>
            <div class="panel"><h3 class="panel-title">数据源筛选</h3><div class="source-filters" id="sourceFilters"></div></div>
            <div class="panel"><h3 class="panel-title">搜索</h3><div class="search-box"><input type="text" id="searchInput" placeholder="输入关键词搜索..." oninput="handleSearch()"></div></div>
            <div class="panel"><h3 class="panel-title">热门关键词</h3><div class="keyword-cloud" id="keywordCloud"><span class="kw-empty">暂无数据</span></div></div>
            <div class="panel"><h3 class="panel-title">统计</h3><div class="stats"><div class="stat-item"><span class="stat-label">总条数</span><span class="stat-value" id="statTotal">0</span></div><div class="stat-item"><span class="stat-label">正常源</span><span class="stat-value" id="statSources">0/0</span></div><div class="stat-item"><span class="stat-label">爆热</span><span class="stat-value" id="statScorching">0</span></div></div></div>
        </aside>
        <div class="content-right">
            <div class="tab-bar">
                <div class="tab active" id="tabHeat" onclick="switchTab('heat')"><span class="tab-icon">🔥</span> 热度排序</div>
                <div class="tab" id="tabTime" onclick="switchTab('time')"><span class="tab-icon">🕐</span> 时间排序</div>
                <div class="tab" id="tabCninfo" onclick="switchTab('cninfo')"><span class="tab-icon">📋</span> 巨潮公告</div>
            </div>
            <main class="news-feed" id="newsFeed"><div class="empty-state"><div class="icon">⏳</div><p>加载中...</p></div></main>
        </div>
    </div>
    <footer class="footer"><span>金融市场信息聚合系统 | 数据源: 财联社 · 金十数据 · 华尔街见闻 · 巨潮资讯网 · 交易所 · 证监会 · 三大证券报</span><span id="genTime"></span></footer>
</div>
<script>
const DATA = ''' + data_json + ''';
let currentSource="",currentLevel="",currentSort="heat",searchQuery="";
const HEAT_ORDER=["scorching","hot","warm","cool","cold"];

function init(){
    document.getElementById("updateTime").textContent="数据时间: "+DATA.generated_at;
    document.getElementById("genTime").textContent="生成于: "+DATA.generated_at;
    renderHeatLegend();
    renderStatusBar();
    renderSourceFilters();
    renderKeywords();
    renderStats();
    renderNews();
}

function renderHeatLegend(){
    const c=document.getElementById("heatLegend");
    c.innerHTML="";
    for(const lv of HEAT_ORDER){
        const m=DATA.heat_levels[lv];if(!m)continue;
        const d=document.createElement("div");
        d.className="heat-legend-item"+(currentLevel===lv?" active":"");
        d.onclick=()=>toggleLevel(lv);
        d.innerHTML='<div class="heat-badge" style="background:'+m.color+'">'+m.label+'</div><span>'+getLevelName(lv)+'</span>';
        c.appendChild(d);
    }
}
function getLevelName(l){const n={scorching:"爆热(≥80)",hot:"热门(≥50)",warm:"温热(≥30)",cool:"一般(≥15)",cold:"冷门(<15)"};return n[l]||l;}
function toggleLevel(l){currentLevel=currentLevel===l?"":l;renderHeatLegend();renderNews();}
function switchTab(s){currentSort=s;document.getElementById("tabHeat").classList.toggle("active",s==="heat");document.getElementById("tabTime").classList.toggle("active",s==="time");document.getElementById("tabCninfo").classList.toggle("active",s==="cninfo");renderNews();}

function renderStatusBar(){
    const b=document.getElementById("statusBar");b.innerHTML="";
    for(const[id,info]of Object.entries(DATA.source_status)){
        const c=document.createElement("div");
        c.className="source-chip"+(currentSource===id?" active":"");
        c.onclick=()=>toggleSource(id);
        c.innerHTML='<div class="dot '+info.status+'"></div><span>'+info.name+'</span>'+(info.count>0?'<span class="count">'+info.count+'</span>':"");
        b.appendChild(c);
    }
}
function renderSourceFilters(){
    const c=document.getElementById("sourceFilters");c.innerHTML="";
    const all=document.createElement("div");
    all.className="source-filter-item"+(currentSource===""?" active":"");
    all.onclick=()=>toggleSource("");
    all.innerHTML='<div class="color-dot" style="background:var(--accent)"></div><span>全部数据源</span>';
    c.appendChild(all);
    for(const[id,info]of Object.entries(DATA.source_status)){
        const d=document.createElement("div");
        d.className="source-filter-item"+(currentSource===id?" active":"");
        d.onclick=()=>toggleSource(id);
        d.innerHTML='<div class="color-dot" style="background:'+info.color+'"></div><span>'+info.name+'</span><span style="margin-left:auto;font-size:11px;color:var(--text-muted)">'+info.count+'</span>';
        c.appendChild(d);
    }
}
function renderStats(){
    document.getElementById("statTotal").textContent=DATA.items.length;
    const ok=Object.values(DATA.source_status).filter(s=>s.status==="ok").length;
    const tot=Object.keys(DATA.source_status).length;
    document.getElementById("statSources").textContent=ok+"/"+tot;
    document.getElementById("statScorching").textContent=DATA.items.filter(i=>i.heat_level==="scorching").length;
}
function toggleSource(id){currentSource=currentSource===id?"":id;renderSourceFilters();renderStatusBar();renderNews();}

function handleSearch(){
    const i=document.getElementById("searchInput");
    searchQuery=i.value.trim().toLowerCase();
    clearTimeout(window.st);
    window.st=setTimeout(renderNews,300);
}

function renderNews(){
    const feed=document.getElementById("newsFeed");
    let items=DATA.items.slice();
    if(currentSource)items=items.filter(i=>i.source_id===currentSource);
    if(currentLevel)items=items.filter(i=>i.heat_level===currentLevel);
    if(searchQuery)items=items.filter(i=>i.title.toLowerCase().includes(searchQuery)||(i.content||"").toLowerCase().includes(searchQuery));
    if(currentSort==="cninfo"){items=items.filter(i=>i.source_id==="cninfo");items.sort((a,b)=>{const ta=(a.published||"").replace(/[^0-9]/g,"");const tb=(b.published||"").replace(/[^0-9]/g,"");if(!ta&&!tb)return 0;if(!ta)return 1;if(!tb)return -1;return tb.localeCompare(ta);});}else if(currentSort==="time"){items=items.filter(i=>i.source_id!=="cninfo");items.sort((a,b)=>{const ta=(a.published||"").replace(/[^0-9]/g,"");const tb=(b.published||"").replace(/[^0-9]/g,"");if(!ta&&!tb)return 0;if(!ta)return 1;if(!tb)return -1;return tb.localeCompare(ta);});}else{items.sort((a,b)=>(b.heat_score||0)-(a.heat_score||0));}
    if(items.length===0){feed.innerHTML='<div class="empty-state"><div class="icon">📭</div><p>暂无符合条件的新闻</p></div>';return;}
    feed.innerHTML="";
    for(const item of items){
        const card=document.createElement("div");
        card.className="news-card "+(item.heat_level||"cold")+(item.error?" error-card":"");
        const lm=DATA.heat_levels[item.heat_level]||DATA.heat_levels.cold;
        const hc=lm?lm.color:"#90a4ae";const hl=lm?lm.label:"冷";
        let h='<div class="card-header"><span class="source-badge" style="background:'+item.source_color+'">'+(item.source_icon||item.source_name)+'</span><span>'+item.source_name+'</span>';
        if(item.type_label)h+='<span class="type-tag">'+item.type_label+'</span>';
        if(item.important)h+='<span class="type-tag" style="color:#ff5722;font-weight:700">重要</span>';
        h+='</div>';
        let f='<div class="card-footer">';
        if(item.published)f+='<span class="time-tag">🕒 '+item.published+'</span>';
        if(item.heat_keywords)for(const kw of item.heat_keywords.slice(0,5))f+='<span class="kw-tag-small">'+kw+'</span>';
        f+='</div>';
        const titleHtml=item.url?'<a href="'+item.url+'" target="_blank" rel="noopener" style="color:inherit;text-decoration:none">'+escapeHtml(item.title)+'</a>':escapeHtml(item.title);
        card.innerHTML='<div class="heat-section"><div class="heat-badge-large" style="background:'+hc+'">'+hl+'</div><div class="heat-score">'+(item.heat_score||0)+'分</div></div><div class="content-section">'+h+'<div class="title">'+titleHtml+'</div>'+(item.content?'<div class="content">'+escapeHtml(item.content)+'</div>':"")+f+'</div>';
        feed.appendChild(card);
    }
}

function escapeHtml(t){if(!t)return"";const d=document.createElement("div");d.textContent=t;return d.innerHTML;}

function renderKeywords(){
    const c=document.getElementById("keywordCloud");
    const entries=Object.entries(DATA.keywords||{});
    if(entries.length===0){c.innerHTML='<span class="kw-empty">暂无数据</span>';return;}
    c.innerHTML="";
    const max=entries[0][1];
    for(const[kw,count]of entries){
        const t=document.createElement("span");
        t.className="kw-tag"+(count>=max*0.6?" hot":"");
        t.style.fontSize=Math.max(11,Math.min(16,11+(count/max)*5))+"px";
        t.textContent=kw+" ("+count+")";
        t.onclick=()=>{document.getElementById("searchInput").value=kw;searchQuery=kw.toLowerCase();renderNews();};
        c.appendChild(t);
    }
}

init();
</script>
</body>
</html>'''

    output_path = os.path.join(BASE_DIR, "dashboard.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)

    return output_path


if __name__ == "__main__":
    print("=" * 60)
    print("  金融市场信息聚合系统 - 报告生成器")
    print("=" * 60)
    print("\n  正在从各数据源获取最新信息...")
    print("  数据源:", ", ".join(DATA_SOURCES[s]["name"] for s in DATA_SOURCES))

    items, source_status, keyword_stats = fetch_all_sources()

    ok_count = sum(1 for v in source_status.values() if v["status"] == "ok")
    print(f"\n  获取完成: {len(items)} 条信息, {ok_count}/{len(fetcher_instances)} 源正常")
    print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    output_path = generate_html(items, source_status, keyword_stats)

    print(f"\n  >>> 报告已生成: {output_path}")
    print(f"  >>> 请在浏览器中打开此文件查看 <<<\n")
