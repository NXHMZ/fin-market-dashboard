from .base import BaseFetcher
from config import DATA_SOURCES
from datetime import datetime
import re
import json


class Jin10Fetcher(BaseFetcher):
    def __init__(self):
        super().__init__("jin10", DATA_SOURCES["jin10"])

    def fetch(self):
        url = "https://www.jin10.com/flash_newest.js"
        headers = {
            "Referer": "https://www.jin10.com/",
        }
        try:
            import requests
            import urllib3
            urllib3.disable_warnings()
            resp = requests.get(url, headers={**self.headers, **headers},
                                timeout=self.timeout, verify=False)
            if resp.status_code != 200:
                return [self._error_item("金十数据JS文件获取失败")]
            match = re.search(r'var newest = (\[.*?\]);', resp.text, re.DOTALL)
            if not match:
                return [self._error_item("金十数据JS解析失败")]
            data = json.loads(match.group(1))
        except Exception:
            return [self._error_item("金十数据获取异常")]

        items = []
        for entry in data[:30]:
            dt_str = entry.get("time", "")
            d = entry.get("data", {})
            title = d.get("title", "")
            content = d.get("content", "")

            if not title and content:
                content_clean = re.sub(r'<[^>]+>', '', content).strip()
                title = content_clean[:40]
            if not title:
                continue

            content_text = re.sub(r'<[^>]+>', '', content).strip() if content else ""

            url_str = f"https://www.jin10.com/item/flash/{entry.get('id', '')}"

            item = self._make_item(title, content_text, url_str, dt_str)
            item["important"] = entry.get("type", 0) == 1
            items.append(item)

        if not items:
            return [self._error_item("金十数据未解析到新闻")]
        return items
