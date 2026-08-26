import os
import sys
import threading
import time
from datetime import datetime
from collections import defaultdict

from flask import Flask, render_template, jsonify, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_SOURCES, REFRESH_INTERVAL, MAX_TOTAL_ITEMS
from heat_engine import HeatEngine
from fetchers.cls_fetcher import CLSFetcher
from fetchers.jin10_fetcher import Jin10Fetcher
from fetchers.wallstreetcn_fetcher import WallstreetcnFetcher
from fetchers.cninfo_fetcher import CninfoFetcher
from fetchers.exchange_fetcher import ExchangeFetcher
from fetchers.csrc_fetcher import CSRCFetcher
from fetchers.securities_fetcher import SecuritiesFetcher

app = Flask(__name__, static_folder="static", template_folder="templates")

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

cache_lock = threading.Lock()
cache = {
    "items": [],
    "source_status": {},
    "keyword_stats": {},
    "last_update": "",
    "total_count": 0,
    "source_counts": {},
}

prev_heat_scores = {}


def fetch_all_sources():
    all_items = []
    source_status = {}
    source_counts = {}

    def fetch_source(source_id, fetcher):
        try:
            items = fetcher.fetch()
            source_status[source_id] = {
                "name": DATA_SOURCES[source_id]["name"],
                "status": "ok" if not any(i.get("error") for i in items) else "partial",
                "count": len([i for i in items if not i.get("error")]),
                "color": DATA_SOURCES[source_id]["color"],
                "icon": DATA_SOURCES[source_id]["icon"],
                "last_attempt": datetime.now().strftime("%H:%M:%S"),
            }
            source_counts[source_id] = len([i for i in items if not i.get("error")])
            return items
        except Exception as e:
            source_status[source_id] = {
                "name": DATA_SOURCES[source_id]["name"],
                "status": "error",
                "count": 0,
                "color": DATA_SOURCES[source_id]["color"],
                "icon": DATA_SOURCES[source_id]["icon"],
                "last_attempt": datetime.now().strftime("%H:%M:%S"),
                "error": str(e)[:100],
            }
            source_counts[source_id] = 0
            return []

    threads = []
    results = {}

    for source_id, fetcher in fetcher_instances.items():
        def run(s=source_id, f=fetcher):
            results[s] = fetch_source(s, f)
        t = threading.Thread(target=run)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=20)

    for source_id in fetcher_instances:
        items = results.get(source_id, [])
        for item in items:
            scored = heat_engine.calculate(item)
            all_items.append(scored)

    all_items.sort(key=lambda x: x.get("heat_score", 0), reverse=True)
    all_items = all_items[:MAX_TOTAL_ITEMS]

    global prev_heat_scores
    new_heat_scores = {}
    for item in all_items:
        key = item.get("source_id", "") + "|" + item.get("title", "")[:80]
        cur_score = item.get("heat_score", 0)
        if key in prev_heat_scores:
            prev = prev_heat_scores[key]
            if cur_score > prev:
                item["heat_trend"] = "up"
                item["heat_delta"] = round(cur_score - prev, 1)
            elif cur_score < prev:
                item["heat_trend"] = "down"
                item["heat_delta"] = round(prev - cur_score, 1)
            else:
                item["heat_trend"] = "same"
                item["heat_delta"] = 0
        else:
            item["heat_trend"] = "new"
            item["heat_delta"] = 0
        new_heat_scores[key] = cur_score
    prev_heat_scores = new_heat_scores

    keyword_stats = heat_engine.compute_keyword_stats(all_items)

    with cache_lock:
        cache["items"] = all_items
        cache["source_status"] = source_status
        cache["keyword_stats"] = keyword_stats
        cache["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cache["total_count"] = len(all_items)
        cache["source_counts"] = source_counts

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 数据更新完成: {len(all_items)} 条, "
          f"{sum(1 for v in source_status.values() if v['status'] == 'ok')}/{len(fetcher_instances)} 源正常")


def background_updater():
    while True:
        fetch_all_sources()
        time.sleep(REFRESH_INTERVAL)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/news")
def api_news():
    source = request.args.get("source", "")
    min_heat = request.args.get("min_heat", 0, type=float)
    search = request.args.get("search", "").lower()
    heat_level = request.args.get("level", "")

    with cache_lock:
        items = list(cache["items"])

    if source:
        items = [i for i in items if i.get("source_id") == source]

    if min_heat > 0:
        items = [i for i in items if i.get("heat_score", 0) >= min_heat]

    if heat_level:
        items = [i for i in items if i.get("heat_level") == heat_level]

    if search:
        items = [i for i in items
                 if search in i.get("title", "").lower()
                 or search in i.get("content", "").lower()]

    return jsonify({
        "items": items,
        "total": len(items),
        "last_update": cache["last_update"],
    })


@app.route("/api/status")
def api_status():
    with cache_lock:
        return jsonify({
            "source_status": cache["source_status"],
            "total_count": cache["total_count"],
            "last_update": cache["last_update"],
            "source_counts": cache["source_counts"],
        })


@app.route("/api/keywords")
def api_keywords():
    with cache_lock:
        return jsonify({
            "keywords": cache["keyword_stats"],
            "last_update": cache["last_update"],
        })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    thread = threading.Thread(target=fetch_all_sources)
    thread.start()
    return jsonify({"message": "刷新已触发", "time": datetime.now().strftime("%H:%M:%S")})


@app.route("/api/heat_levels")
def api_heat_levels():
    return jsonify(heat_engine.heat_level_meta)


if __name__ == "__main__":
    print("=" * 60)
    print("  金融市场信息聚合系统 启动中...")
    print("  数据源:", ", ".join(DATA_SOURCES[s]["name"] for s in DATA_SOURCES))
    print("  刷新间隔:", REFRESH_INTERVAL, "秒")
    print("=" * 60)

    print("  正在首次获取数据...")
    fetch_all_sources()
    print("  首次数据获取完成!")

    updater = threading.Thread(target=background_updater, daemon=True)
    updater.start()

    print("\n  >>> 请在浏览器打开: http://127.0.0.1:5000 <<<\n")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
