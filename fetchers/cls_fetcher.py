from .base import BaseFetcher
from config import DATA_SOURCES
from datetime import datetime
from bs4 import BeautifulSoup


class CLSFetcher(BaseFetcher):
    def __init__(self):
        super().__init__("cls", DATA_SOURCES["cls"])

    def fetch(self):
        soup = self._request_html("https://www.cls.cn/")
        if not soup:
            return [self._error_item("无法连接财联社网站")]

        items = []
        seen = set()
        for a_tag in soup.select("a[href]"):
            href = a_tag.get("href", "")
            if "/detail/" not in href:
                continue
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 6 or title in seen:
                continue
            seen.add(title)
            if not href.startswith("http"):
                href = f"https://www.cls.cn{href}"
            time_part = self._extract_time_from_text(title)
            if time_part:
                pub = f"{self._today_str()} {time_part}"
            else:
                pub = f"{self._today_str()} 00:00"
            item = self._make_item(title, "", href, pub)
            items.append(item)
            if len(items) >= 30:
                break

        if not items:
            return [self._error_item("财联社页面未提取到新闻")]
        return items
