import os
import sys
import threading
import time
import json
import queue
from datetime import datetime
from collections import defaultdict

from flask import Flask, render_template, jsonify, request, Response

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_SOURCES, SOURCE_TIERS, MAX_TOTAL_ITEMS, DEDUP_TITLE_THRESHOLD
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
    "breaking_news": [],
    "tier_status": {},
}

prev_heat_scores = {}

sse_clients = []
sse_lock = threading.Lock()


def notify_sse(event_type, data):
    msg = json.dumps({"type": event_type, "data": data, "timestamp": datetime.now().strftime("%H:%M:%S")}, ensure_ascii=False)
    with sse_lock:
        dead = []
        for i, q in enumerate(sse_clients):
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(i)
        for i in reversed(dead):
            sse_clients.pop(i)


def fetch_source(source_id, fetcher):
    try:
        items = fetcher.fetch()
        status = {
            "name": DATA_SOURCES[source_id]["name"],
            "status": "ok" if not any(i.get("error") for i in items) else "partial",
            "count": len([i for i in items if not i.get("error")]),
            "color": DATA_SOURCES[source_id]["color"],
            "icon": DATA_SOURCES[source_id]["icon"],
            "last_attempt": datetime.now().strftime("%H:%M:%S"),
        }
        return items, status
    except Exception as e:
        status = {
            "name": DATA_SOURCES[source_id]["name"],
            "status": "error",
            "count": 0,
            "color": DATA_SOURCES[source_id]["color"],
            "icon": DATA_SOURCES[source_id]["icon"],
            "last_attempt": datetime.now().strftime("%H:%M:%S"),
            "error": str(e)[:100],
        }
        return [], status


def fetch_tier(tier_name, tier_config):
    source_ids = tier_config["sources"]
    threads = []
    results = {}
    statuses = {}

    for sid in source_ids:
        fetcher = fetcher_instances.get(sid)
        if not fetcher:
            continue

        def run(s=sid, f=fetcher):
            items, status = fetch_source(s, f)
            results[s] = items
            statuses[s] = status

        t = threading.Thread(target=run)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=20)

    return results, statuses


def merge_and_score(new_results, tier_name):
    with cache_lock:
        existing_items = list(cache["items"])
        existing_titles = {item.get("title", "")[:80] for item in existing_items}
        existing_keys = {item.get("source_id", "") + "|" + item.get("title", "")[:80] for item in existing_items}

    all_new_items = []
    breaking_items = []
    source_counts_update = {}

    for source_id, raw_items in new_results.items():
        valid_items = [i for i in raw_items if not i.get("error")]
        source_counts_update[source_id] = len(valid_items)

        for item in raw_items:
            if item.get("error"):
                continue

            title = item.get("title", "")[:80]
            dedup_key = source_id + "|" + title
            if dedup_key in existing_keys:
                continue

            if heat_engine.is_duplicate(title, existing_items + all_new_items, DEDUP_TITLE_THRESHOLD):
                continue

            scored = heat_engine.calculate(item)
            all_new_items.append(scored)

            if scored.get("is_breaking"):
                breaking_items.append(scored)

    if all_new_items:
        merged = existing_items + all_new_items
        merged.sort(key=lambda x: x.get("heat_score", 0), reverse=True)
        merged = merged[:MAX_TOTAL_ITEMS]

        global prev_heat_scores
        new_heat_scores = {}
        for item in merged:
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

        keyword_stats = heat_engine.compute_keyword_stats(merged)

        with cache_lock:
            cache["items"] = merged
            cache["keyword_stats"] = keyword_stats
            cache["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cache["total_count"] = len(merged)
            for sid, cnt in source_counts_update.items():
                cache["source_counts"][sid] = cnt
            cache["tier_status"][tier_name] = {
                "last_run": datetime.now().strftime("%H:%M:%S"),
                "new_items": len(all_new_items),
                "breaking": len(breaking_items),
            }
            if breaking_items:
                cache["breaking_news"] = (cache.get("breaking_news", []) + breaking_items)[-50:]

        if breaking_items:
            for b in breaking_items:
                notify_sse("breaking", {
                    "title": b.get("title", ""),
                    "source": b.get("source_name", ""),
                    "score": b.get("heat_score", 0),
                    "url": b.get("url", ""),
                    "hits": b.get("breaking_hits", []),
                })
                print(f"  [突发] {b.get('source_name','')} | {b.get('title','')[:50]}")

        notify_sse("update", {
            "tier": tier_name,
            "new_count": len(all_new_items),
            "breaking_count": len(breaking_items),
            "total": len(merged),
        })

        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{tier_name}] 新增 {len(all_new_items)} 条, "
              f"突发 {len(breaking_items)} 条, 总计 {len(merged)} 条")


def update_source_status(tier_name, statuses):
    with cache_lock:
        for sid, status in statuses.items():
            cache["source_status"][sid] = status


def tier_worker(tier_name, tier_config):
    interval = tier_config["interval"]
    sources_label = tier_config["label"]
    print(f"  [{tier_name}] 轮询线程启动 ({sources_label}, 每 {interval}s)")

    while True:
        try:
            results, statuses = fetch_tier(tier_name, tier_config)
            update_source_status(tier_name, statuses)
            merge_and_score(results, tier_name)
        except Exception as e:
            print(f"  [{tier_name}] 轮询异常: {e}")

        time.sleep(interval)


def initial_fetch_all():
    print("  正在首次获取数据...")
    all_results = {}
    all_statuses = {}

    for tier_name, tier_config in SOURCE_TIERS.items():
        results, statuses = fetch_tier(tier_name, tier_config)
        all_results.update(results)
        all_statuses.update(statuses)
        update_source_status(tier_name, statuses)

    with cache_lock:
        existing_items = []
        existing_keys = set()

    all_items = []
    for source_id, raw_items in all_results.items():
        for item in raw_items:
            if item.get("error"):
                continue
            scored = heat_engine.calculate(item)
            all_items.append(scored)

    all_items.sort(key=lambda x: x.get("heat_score", 0), reverse=True)
    all_items = all_items[:MAX_TOTAL_ITEMS]

    global prev_heat_scores
    for item in all_items:
        key = item.get("source_id", "") + "|" + item.get("title", "")[:80]
        item["heat_trend"] = "new"
        item["heat_delta"] = 0
        prev_heat_scores[key] = item.get("heat_score", 0)

    breaking_items = [item for item in all_items if item.get("is_breaking")]

    keyword_stats = heat_engine.compute_keyword_stats(all_items)

    with cache_lock:
        cache["items"] = all_items
        cache["keyword_stats"] = keyword_stats
        cache["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cache["total_count"] = len(all_items)
        cache["source_counts"] = {sid: len([i for i in items if not i.get("error")]) for sid, items in all_results.items()}
        if breaking_items:
            cache["breaking_news"] = breaking_items[:50]

    print(f"  首次获取完成: {len(all_items)} 条, 突发 {len(breaking_items)} 条")


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
            "tier_status": cache.get("tier_status", {}),
            "breaking_count": len(cache.get("breaking_news", [])),
        })


@app.route("/api/keywords")
def api_keywords():
    with cache_lock:
        return jsonify({
            "keywords": cache["keyword_stats"],
            "last_update": cache["last_update"],
        })


@app.route("/api/breaking")
def api_breaking():
    with cache_lock:
        items = list(cache.get("breaking_news", []))
    return jsonify({
        "items": items,
        "total": len(items),
        "last_update": cache["last_update"],
    })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    tier_name = request.args.get("tier", "")
    if tier_name and tier_name in SOURCE_TIERS:
        thread = threading.Thread(target=fetch_tier_and_merge, args=(tier_name,))
        thread.start()
        return jsonify({"message": f"已触发 {tier_name} 刷新", "time": datetime.now().strftime("%H:%M:%S")})

    thread = threading.Thread(target=initial_fetch_all)
    thread.start()
    return jsonify({"message": "已触发全量刷新", "time": datetime.now().strftime("%H:%M:%S")})


def fetch_tier_and_merge(tier_name):
    tier_config = SOURCE_TIERS[tier_name]
    results, statuses = fetch_tier(tier_name, tier_config)
    update_source_status(tier_name, statuses)
    merge_and_score(results, tier_name)


@app.route("/api/heat_levels")
def api_heat_levels():
    return jsonify(heat_engine.heat_level_meta)


@app.route("/api/stream")
def api_stream():
    def event_stream():
        q = queue.Queue(maxsize=100)
        with sse_lock:
            sse_clients.append(q)

        try:
            yield "event: connected\ndata: {\"type\":\"connected\"}\n\n"
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield f"data: {msg}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        finally:
            with sse_lock:
                if q in sse_clients:
                    sse_clients.remove(q)

    return Response(event_stream(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  金融市场信息聚合系统 启动中...")
    print("  数据源:", ", ".join(DATA_SOURCES[s]["name"] for s in DATA_SOURCES))
    print("  分级轮询:")
    for tier_name, tier_config in SOURCE_TIERS.items():
        sources = ", ".join(DATA_SOURCES[s]["name"] for s in tier_config["sources"])
        print(f"    [{tier_name}] {sources} (每 {tier_config['interval']}s)")
    print("=" * 60)

    initial_fetch_all()
    print("  首次数据获取完成!")

    for tier_name, tier_config in SOURCE_TIERS.items():
        worker = threading.Thread(target=tier_worker, args=(tier_name, tier_config), daemon=True)
        worker.start()

    print("\n  >>> 请在浏览器打开: http://127.0.0.1:5000 <<<\n")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=True)
