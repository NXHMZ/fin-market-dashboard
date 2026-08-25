from .base import BaseFetcher
from config import DATA_SOURCES
from datetime import datetime
from bs4 import BeautifulSoup
import re
import requests


class CSRCFetcher(BaseFetcher):
    def __init__(self):
        super().__init__("csrc", DATA_SOURCES["csrc"])

    def fetch(self):
        url = "https://www.csrc.gov.cn/pub/newsite/zjxw/"
        soup = self._request_html(url)
        if not soup:
            return [self._error_item("无法连接证监会网站")]

        items = []
        for li in soup.select("ul.list_con li, .list-item li, .news-list li, ul li")[:30]:
            a_tag = li.select_one("a")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 4:
                continue
            href = a_tag.get("href", "")
            if href and not href.startswith("http"):
                if href.startswith("/"):
                    href = f"https://www.csrc.gov.cn{href}"
                else:
                    href = f"https://www.csrc.gov.cn/{href}"

            time_tag = li.select_one("span.date, span.time, .date, time")
            dt_str = time_tag.get_text(strip=True) if time_tag else ""

            if dt_str:
                m = re.match(r"^(\d{2})-(\d{2})$", dt_str.strip())
                if m:
                    dt_str = f"{datetime.now().year}-{dt_str.strip()} 00:00"
                elif re.match(r"^\d{4}-\d{2}-\d{2}$", dt_str.strip()):
                    dt_str = f"{dt_str.strip()} 00:00"
            else:
                dt_str = f"{self._today_str()} 00:00"

            item = self._make_item(title, "", href, dt_str)
            items.append(item)

        if not items:
            return [self._error_item("证监会未获取到数据")]

        return items
