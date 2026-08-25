from .base import BaseFetcher
from config import DATA_SOURCES
from datetime import datetime
from bs4 import BeautifulSoup


class WallstreetcnFetcher(BaseFetcher):
    def __init__(self):
        super().__init__("wallstreetcn", DATA_SOURCES["wallstreetcn"])

    def fetch(self):
        url = "https://api-one-wscn.awtmt.com/apiv1/content/lives"
        params = {
            "channel": "global-channel",
            "limit": "30",
        }
        data = self._request_json(url, params=params)
        if not data:
            return [self._error_item("无法连接华尔街见闻接口")]

        items = []
        items_data = data.get("data", {})
        if isinstance(items_data, dict):
            items_data = items_data.get("items", [])
        elif isinstance(items_data, list):
            pass
        else:
            return [self._error_item("未获取到华尔街见闻数据")]

        for entry in items_data[:30]:
            dt_str = ""
            published = entry.get("published_at") or entry.get("display_time", "")
            if published:
                try:
                    ts = int(published)
                    if ts > 1e12:
                        ts = ts / 1000
                    dt_str = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    dt_str = str(published)[:19]

            title = entry.get("title", "") or entry.get("title_text", "")
            content_raw = entry.get("content", "") or entry.get("content_short", "")
            content_text = content_raw
            if content_raw and "<" in content_raw:
                content_text = BeautifulSoup(content_raw, "lxml").get_text(strip=True)

            if not title and content_text:
                title = content_text[:40]
            if not title:
                continue

            uri = entry.get("uri", "")
            url_str = f"https://wallstreetcn.com/news/global/{uri}" if uri else "https://wallstreetcn.com/"

            important = entry.get("is_important", False)
            item = self._make_item(title, content_text, url_str, dt_str)
            item["important"] = important
            items.append(item)

        return items
