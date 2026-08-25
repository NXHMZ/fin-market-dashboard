import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
import traceback

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BaseFetcher:
    def __init__(self, source_id, config):
        self.source_id = source_id
        self.source_name = config["name"]
        self.source_color = config["color"]
        self.source_icon = config["icon"]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.timeout = 10

    def fetch(self):
        raise NotImplementedError

    def _request_json(self, url, params=None, headers=None):
        try:
            h = {**self.headers, **(headers or {})}
            resp = requests.get(url, params=params, headers=h, timeout=self.timeout, verify=False)
            resp.encoding = resp.apparent_encoding
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None

    def _request_html(self, url, params=None, headers=None):
        try:
            h = {**self.headers, **(headers or {})}
            resp = requests.get(url, params=params, headers=h, timeout=self.timeout, verify=False)
            resp.encoding = resp.apparent_encoding
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "lxml")
            return None
        except Exception:
            return None

    def _make_item(self, title, content, url, published, extra=None):
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_color": self.source_color,
            "source_icon": self.source_icon,
            "title": title,
            "content": content or "",
            "url": url or "",
            "published": published or "",
            "published_dt": self._parse_date(published),
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **(extra or {}),
        }

    def _parse_date(self, date_str):
        if not date_str:
            return None
        for fmt in [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y年%m月%d日 %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
        ]:
            try:
                return datetime.strptime(date_str[:19], fmt)
            except ValueError:
                continue
        return None

    def _extract_date_from_url(self, url):
        import re
        m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
        if m:
            y, mo, d = m.group(1), m.group(2), m.group(3)
            if 2020 <= int(y) <= 2030 and 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
                return f"{y}-{mo}-{d} 00:00"
        for pat in [r"detail_(\d{4})(\d{2})(\d{2})", r"_(\d{4})(\d{2})(\d{2})_", r"\D(\d{4})(\d{2})(\d{2})\D"]:
            m = re.search(pat, url)
            if m:
                y, mo, d = m.group(1), m.group(2), m.group(3)
                if 2020 <= int(y) <= 2030 and 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
                    return f"{y}-{mo}-{d} 00:00"
        return None

    def _extract_time_from_text(self, text):
        import re
        m = re.search(r"(\d{2}):(\d{2})(?::(\d{2}))?", text)
        if m:
            h, mi = m.group(1), m.group(2)
            s = m.group(3) or "00"
            return f"{h}:{mi}:{s}"
        return None

    def _today_str(self):
        return datetime.now().strftime("%Y-%m-%d")

    def _error_item(self, error_msg):
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_color": self.source_color,
            "source_icon": self.source_icon,
            "title": f"[{self.source_name} 数据获取失败]",
            "content": error_msg,
            "url": "",
            "published": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "published_dt": datetime.now(),
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": True,
        }
